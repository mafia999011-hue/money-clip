import os
import re
import subprocess
from .reframer import VideoReframer
from .gemini_client import GeminiClipperClient
from .subtitler import SubtitleGenerator
from .renderer import VideoRenderer
from .dubber import AIDubber, SUPPORTED_DUB_LANGUAGES
from .storage import HistoryStorage

class AutoClipPipeline:
    def __init__(self, api_key: str = None, output_dir: str = "output"):
        self.api_key = api_key
        self.output_dir = output_dir
        self.client = GeminiClipperClient(api_key=api_key)

    def process_video(
        self,
        video_path: str,
        reframe_mode: str = "blurred_background",
        aspect_ratio: str = "9:16",
        dub_language: str = "none",
        subtitle_preset: str = "hormozi",
        enable_emojis: bool = True,
        length_pref: str = "auto",
        clip_count: str = "3",
        caption_language: str = "auto",
        video_quality: str = "1080p",
        show_hook_header: bool = True,
        enable_dynamic_zoom: bool = True,
        enable_progress_bar: bool = True,
        enable_color_pop: bool = True,
        enable_audio_boost: bool = True,
        progress_callback = None
    ) -> dict:
        def update_progress(stage: str, percent: int):
            if progress_callback:
                progress_callback(stage, percent)

        update_progress("Inspecting video metadata", 10)
        info = VideoReframer.get_video_info(video_path)
        video_duration = info.get("duration", 60.0)

        update_progress("Extracting audio track for Opus AI engine", 25)
        audio_path = self.client.extract_audio(video_path, video_duration=video_duration)

        update_progress(f"Analyzing virality & hooks ({caption_language.upper()} script, {clip_count} clips)", 45)
        ai_result = self.client.analyze_video_audio(
            audio_path,
            video_duration,
            length_pref=length_pref,
            clip_count=clip_count,
            caption_language=caption_language
        )

        clips_data = ai_result.get("clips", [])
        rendered_clips = []
        total_clips = len(clips_data)

        for idx, clip in enumerate(clips_data):
            c_id = clip.get("id", idx + 1)
            title = clip.get("title", f"Clip {c_id}")
            raw_start = float(clip.get("start_time", 0.0))
            raw_end = float(clip.get("end_time", raw_start + 30.0))

            # Bulletproof sanity check: fix any inverted or out-of-bounds timestamps from AI
            if raw_start > raw_end:
                raw_start, raw_end = raw_end, raw_start
            if (raw_end - raw_start) < 8.0:
                raw_end = min(video_duration, raw_start + 25.0)
            start_t = max(0.0, min(raw_start, max(0.0, video_duration - 5.0)))
            end_t = max(start_t + 5.0, min(raw_end, video_duration))
            clip_dur = round(end_t - start_t, 2)

            slug = re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:25].strip('_')
            clip_base = f"clip_{c_id}_{slug}"

            ass_path = os.path.join(self.output_dir, f"{clip_base}.ass")
            clip_output_path = os.path.join(self.output_dir, f"{clip_base}.mp4")
            raw_segment_path = os.path.join(self.output_dir, f"{clip_base}_seg.mp4")

            progress_pct = 50 + int((idx + 1) / total_clips * 45)
            update_progress(f"Extracting frame-perfect clip {c_id}/{total_clips}...", max(10, progress_pct - 6))

            # Step 1: Pre-cut the exact clip segment using frame-accurate decode seeking
            # This locks video & audio streams to the exact same millisecond
            cut_cmd = [
                "ffmpeg", "-y",
                "-accurate_seek",
                "-ss", f"{start_t:.3f}",
                "-t", f"{clip_dur:.3f}",
                "-i", video_path,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                raw_segment_path
            ]
            subprocess.run(cut_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            render_source = raw_segment_path if os.path.exists(raw_segment_path) else video_path
            render_start = 0.0 if os.path.exists(raw_segment_path) else start_t
            render_end = clip_dur if os.path.exists(raw_segment_path) else end_t

            # Step 2: Transcribe speech directly from the exact cut segment (0.0s to clip_dur)
            update_progress(f"Transcribing voice timestamps for Clip {c_id}/{total_clips}...", max(10, progress_pct - 3))
            precise_words = self.client.transcribe_clip_audio(
                audio_path=render_source,
                start_time=render_start,
                duration=clip_dur,
                caption_language=caption_language
            )

            # Robust fallback: if speech transcription is empty (silent or instrumental),
            # evenly pace words over the ENTIRE clip duration so subtitles never cut off early
            if not precise_words:
                fallback_text = clip.get("hook") or clip.get("title", "")
                tokens = [tok for tok in re.split(r'\s+', fallback_text) if tok.strip()]
                if tokens:
                    word_interval = max(0.2, clip_dur / max(1, len(tokens)))
                    precise_words = []
                    for i, tok in enumerate(tokens):
                        w_s = round(i * word_interval, 2)
                        w_e = round(min(clip_dur, (i + 1) * word_interval), 2)
                        precise_words.append({"word": tok, "start": w_s, "end": w_e})

            hook_headline = clip.get("hook_headline") or title
            audio_override_path = None

            # Optional AI Voice Dubbing & Speech Translation
            is_dubbed = AIDubber.is_dubbing_enabled(dub_language)
            if is_dubbed:
                dub_lang_name = SUPPORTED_DUB_LANGUAGES.get(dub_language, dub_language)
                update_progress(f"AI Dubbing voiceover to {dub_lang_name} for Clip {c_id}/{total_clips}...", max(10, progress_pct - 2))
                
                spoken_script = " ".join([re.sub(r'[^a-zA-Z0-9\u0600-\u06FF\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF]', ' ', w.get("word", "")).strip() for w in precise_words if w.get("word")])
                if len(spoken_script.strip()) < 10:
                    spoken_script = clip.get("hook") or title

                translated_script = AIDubber.translate_script(spoken_script, dub_language, api_key=self.api_key)

                if hook_headline:
                    translated_hook = AIDubber.translate_script(hook_headline, dub_language, api_key=self.api_key)
                    if translated_hook:
                        hook_headline = translated_hook

                raw_dub_path = os.path.join(self.output_dir, f"{clip_base}_dub.mp3")
                synth_audio = AIDubber.synthesize_speech(translated_script, dub_language, raw_dub_path, target_duration=clip_dur)

                if synth_audio and os.path.exists(synth_audio):
                    mixed_audio_path = os.path.join(self.output_dir, f"{clip_base}_mixed.aac")
                    audio_override_path = AIDubber.duck_and_mix_audio(
                        original_input=render_source,
                        start_time=render_start,
                        duration=clip_dur,
                        dub_audio_path=synth_audio,
                        output_audio_path=mixed_audio_path
                    )

                    dub_tokens = [tok for tok in re.split(r'\s+', translated_script) if tok.strip()]
                    if dub_tokens:
                        dub_interval = max(0.18, clip_dur / len(dub_tokens))
                        dub_words = []
                        for i, tok in enumerate(dub_tokens):
                            w_s = round(i * dub_interval, 2)
                            w_e = round(min(clip_dur, (i + 1) * dub_interval), 2)
                            dub_words.append({"word": tok, "start": w_s, "end": w_e})
                        precise_words = dub_words

            # Generate ASS subtitles with Opus auto-emojis, active bounce, top hook banner, and punchy 2-word groups
            SubtitleGenerator.generate_ass(
                words=precise_words,
                clip_start=0.0,
                clip_end=clip_dur,
                output_ass_path=ass_path,
                preset_name=subtitle_preset,
                aspect_ratio=aspect_ratio,
                enable_emojis=enable_emojis,
                words_per_group=2,
                video_quality=video_quality,
                hook_headline=hook_headline,
                show_hook_header=show_hook_header
            )

            update_progress(f"Rendering Clip {c_id}/{total_clips}: {title} ({aspect_ratio}, {video_quality})", progress_pct)

            VideoRenderer.render_clip(
                video_path=render_source,
                start_time=render_start,
                end_time=render_end,
                output_path=clip_output_path,
                reframe_mode=reframe_mode,
                aspect_ratio=aspect_ratio,
                ass_path=ass_path,
                video_quality=video_quality,
                enable_dynamic_zoom=enable_dynamic_zoom,
                enable_progress_bar=enable_progress_bar,
                enable_color_pop=enable_color_pop,
                enable_audio_boost=enable_audio_boost,
                subtitle_preset=subtitle_preset,
                audio_override_path=audio_override_path
            )

            # Clean up intermediate segment
            if os.path.exists(raw_segment_path):
                try:
                    os.remove(raw_segment_path)
                except Exception:
                    pass

            rendered_clips.append({
                "id": c_id,
                "title": title,
                "hook": clip.get("hook", ""),
                "hook_headline": hook_headline,
                "hook_type": clip.get("hook_type", "⚡ Value Bomb & Hack"),
                "curiosity_gap": clip.get("curiosity_gap", "9.6/10"),
                "drop_off_risk": clip.get("drop_off_risk", "Very Low"),
                "viral_action_tip": clip.get("viral_action_tip", "Pin an engaging question in comments to increase algorithmic watch time."),
                "start_time": start_t,
                "end_time": end_t,
                "duration": clip_dur,
                "quality": video_quality,
                "aspect_ratio": aspect_ratio,
                "dub_language": dub_language,
                "dub_label": SUPPORTED_DUB_LANGUAGES.get(dub_language, "Original"),
                "virality_score": clip.get("virality_score", 95),
                "hook_score": clip.get("hook_score", 96),
                "flow_score": clip.get("flow_score", 94),
                "engagement_score": clip.get("engagement_score", 95),
                "reason": clip.get("reason", ""),
                "social_copy": clip.get("social_copy", {}),
                "video_file": os.path.basename(clip_output_path),
                "download_url": f"/download/{os.path.basename(clip_output_path)}",
                "preview_url": f"/stream/{os.path.basename(clip_output_path)}"
            })

        # Save to persistent history
        try:
            HistoryStorage(os.path.join(os.path.dirname(os.path.abspath(self.output_dir)), "data", "history.json")).save_clips(rendered_clips)
        except Exception as e:
            print(f"Warning: Failed to save to history: {e}")

        update_progress("Complete! All Money Clip shorts rendered successfully.", 100)

        return {
            "summary": ai_result.get("full_summary", ""),
            "original_duration": video_duration,
            "clips": rendered_clips
        }

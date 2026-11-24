import os
import subprocess
from .reframer import VideoReframer

QUALITY_PROFILES = {
    "720p": {
        "crf": "23",
        "preset": "ultrafast",
        "audio_bitrate": "128k"
    },
    "1080p": {
        "crf": "20",
        "preset": "veryfast",
        "audio_bitrate": "192k"
    },
    "1440p": {
        "crf": "18",
        "preset": "veryfast",
        "audio_bitrate": "256k"
    }
}

ASPECT_DIMENSIONS = {
    "9:16": {
        "720p": (720, 1280),
        "1080p": (1080, 1920),
        "1440p": (1440, 2560)
    },
    "1:1": {
        "720p": (720, 720),
        "1080p": (1080, 1080),
        "1440p": (1440, 1440)
    },
    "16:9": {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440)
    },
    "4:5": {
        "720p": (720, 900),
        "1080p": (1080, 1350),
        "1440p": (1440, 1800)
    }
}

PROGRESS_BAR_COLORS = {
    "hormozi": "0x00E6FF",        # Vibrant Yellow
    "mrbeast": "0x00FF66",        # Neon Green
    "cyberpunk": "0xFFFF00",      # Cyan
    "sunset": "0xFF00C8",         # Magenta / Pink
    "devin": "0x00A2FF",          # Gold / Red
    "minimal_clean": "0xFFA600",   # Electric Blue
    "ali_abdaal": "0x66F0FF",     # Pastel Butter Yellow
    "iman_gadzhi": "0x78C3E5",    # Champagne Gold
    "gaming_rgb": "0x00FF33",     # Hyper RGB Green
    "vhs_retro": "0x008CFF",      # Amber Synthwave Orange
    "crimson_urgent": "0x271EFF"  # Crimson Red
}

class VideoRenderer:
    @staticmethod
    def get_or_create_hook_sfx() -> str:
        """Ensures the cinematic sub-bass whoosh impact SFX asset exists."""
        sfx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "assets", "hook_whoosh.wav")
        if os.path.exists(sfx_path) and os.path.getsize(sfx_path) > 1000:
            return sfx_path
        os.makedirs(os.path.dirname(sfx_path), exist_ok=True)
        try:
            import wave
            import struct
            import math
            sample_rate = 44100
            duration = 0.45
            n_samples = int(sample_rate * duration)
            with wave.open(sfx_path, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                frames = bytearray()
                for i in range(n_samples):
                    t = i / sample_rate
                    progress = t / duration
                    freq = 320.0 * (1.0 - progress)**1.8 + 45.0
                    if t < 0.04:
                        env = t / 0.04
                    else:
                        env = math.exp(-6.0 * (t - 0.04))
                    val = 0.85 * math.sin(2.0 * math.pi * freq * t) + 0.15 * math.sin(4.0 * math.pi * freq * t)
                    sample = int(val * env * 24000.0)
                    sample = max(-32767, min(32767, sample))
                    frames.extend(struct.pack('<h', sample))
                wav.writeframes(frames)
            return sfx_path
        except Exception:
            return None

    @staticmethod
    def check_audio_stream(video_path: str) -> bool:
        """Checks if input file contains an active audio stream."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "audio" in res.stdout.decode()

    @classmethod
    def render_clip(
        cls,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        reframe_mode: str = "blurred_background",
        aspect_ratio: str = "9:16",
        ass_path: str = None,
        video_quality: str = "1080p",
        enable_dynamic_zoom: bool = True,
        enable_progress_bar: bool = True,
        enable_color_pop: bool = True,
        enable_audio_boost: bool = True,
        subtitle_preset: str = "hormozi",
        audio_override_path: str = None,
        enable_hook_sfx: bool = True,
        enable_seamless_loop: bool = True
    ) -> str:
        """
        Extracts, reframes (to 9:16 vertical, 1:1 square, 16:9 landscape, or 4:5 portrait),
        sharpens foreground, smooths audio transitions / mixes AI voice dubs,
        and renders video at requested quality (720p, 1080p, or 1440p) with viral editing features.
        """
        duration = max(0.5, end_time - start_time)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        has_audio = cls.check_audio_stream(video_path)

        profile = QUALITY_PROFILES.get(video_quality, QUALITY_PROFILES["1080p"])
        crf = profile["crf"]
        preset = profile["preset"]
        audio_br = profile["audio_bitrate"]

        ar_dict = ASPECT_DIMENSIONS.get(aspect_ratio, ASPECT_DIMENSIONS["9:16"])
        w, h = ar_dict.get(video_quality, ar_dict["1080p"])

        color_filter = ",eq=saturation=1.16:contrast=1.08:brightness=-0.02" if enable_color_pop else ""

        filters = []
        half_h = h // 2
        half_w = w // 2

        if reframe_mode == "split_gaming":
            # Gaming Streamer Split:
            # - Facecam cropped from stream top, gameplay screen cropped from action zone
            if w < h:
                # Vertical stacking for portrait/phone formats (9:16, 4:5)
                filters.append(
                    f"[0:v]crop=iw:ih*0.5:0:0,scale={w}:{half_h},unsharp=5:5:0.6:5:5:0.0{color_filter}[cam];"
                    f"[0:v]crop=iw:ih*0.7:0:ih*0.3,scale={w}:{half_h},unsharp=5:5:0.6:5:5:0.0{color_filter}[game];"
                    f"[cam][game]vstack[v_base]"
                )
            else:
                # Horizontal side-by-side for landscape/square (16:9, 1:1)
                filters.append(
                    f"[0:v]crop=iw*0.5:ih:0:0,scale={half_w}:{h},unsharp=5:5:0.6:5:5:0.0{color_filter}[cam];"
                    f"[0:v]crop=iw*0.7:ih:iw*0.3:0,scale={half_w}:{h},unsharp=5:5:0.6:5:5:0.0{color_filter}[game];"
                    f"[cam][game]hstack[v_base]"
                )
        elif reframe_mode == "split_reaction":
            # Equal 50/50 Dual Cam Reaction / Podcast Split
            if w < h:
                filters.append(
                    f"[0:v]scale={w}:{half_h}:force_original_aspect_ratio=increase,crop={w}:{half_h},unsharp=5:5:0.5:5:5:0.0{color_filter}[top_v];"
                    f"[0:v]scale={w}:{half_h}:force_original_aspect_ratio=increase,crop={w}:{half_h},unsharp=5:5:0.5:5:5:0.0{color_filter}[bot_v];"
                    f"[top_v][bot_v]vstack[v_base]"
                )
            else:
                filters.append(
                    f"[0:v]scale={half_w}:{h}:force_original_aspect_ratio=increase,crop={half_w}:{h},unsharp=5:5:0.5:5:5:0.0{color_filter}[left_v];"
                    f"[0:v]scale={half_w}:{h}:force_original_aspect_ratio=increase,crop={half_w}:{h},unsharp=5:5:0.5:5:5:0.0{color_filter}[right_v];"
                    f"[left_v][right_v]hstack[v_base]"
                )
        elif reframe_mode == "cinema_letterbox":
            # Cinematic Letterbox with darkened ambient glow:
            filters.append(
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=40:5,eq=brightness=-0.35:contrast=1.3[bg];"
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,unsharp=5:5:0.7:5:5:0.0{color_filter}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v_base]"
            )
        elif reframe_mode == "center_crop":
            # Universal Dynamic punch-in zoom for center crop (scales and crops center region to target AR)
            if enable_dynamic_zoom:
                crop_expr = f"crop='w=min(iw,ih*({w}/{h}))*if(lt(mod(t,3.6),2.1),1,0.93)':'h=min(ih,iw*({h}/{w}))*if(lt(mod(t,3.6),2.1),1,0.93)':x=(iw-ow)/2:y=(ih-oh)/2"
            else:
                crop_expr = f"crop='w=min(iw,ih*({w}/{h}))':'h=min(ih,iw*({h}/{w}))':x=(iw-ow)/2:y=(ih-oh)/2"
            filters.append(
                f"[0:v]{crop_expr},"
                f"scale={w}:{h}:flags=bicubic,"
                f"unsharp=5:5:0.6:5:5:0.0{color_filter}[v_base]"
            )
        else:
            # Cinematic Blurred Background (Universal default for ANY aspect ratio)
            if enable_dynamic_zoom:
                fg_crop = "crop='w=if(lt(mod(t,3.6),2.1), iw, iw*0.93)':h='if(lt(mod(t,3.6),2.1), ih, ih*0.93)':x=(iw-ow)/2:y=(ih-oh)/2,"
            else:
                fg_crop = ""
            filters.append(
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},boxblur=30:5,eq=brightness=-0.18:contrast=1.15[bg];"
                f"[0:v]{fg_crop}scale={w}:{h}:force_original_aspect_ratio=decrease,unsharp=5:5:0.6:5:5:0.0{color_filter}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v_base]"
            )

        last_v_stream = "[v_base]"

        # Animated bottom retention progress bar (draws underneath subtitles)
        if enable_progress_bar:
            bar_color = PROGRESS_BAR_COLORS.get(subtitle_preset, "0x00E6FF")
            bar_h = max(8, int(12 * (h / 1920)))
            filters.append(
                f"{last_v_stream}drawbox=x=0:y={h}-{bar_h}:w={w}:h={bar_h}:color=black@0.45:t=fill,"
                f"drawbox=x=0:y={h}-{bar_h}:w='min({w},{w}*t/{duration:.2f})':h={bar_h}:color={bar_color}:t=fill[v_prog]"
            )
            last_v_stream = "[v_prog]"

        if ass_path and os.path.exists(ass_path):
            escaped_ass = ass_path.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
            filters.append(f"{last_v_stream}ass='{escaped_ass}'[v_out]")
            last_v_stream = "[v_out]"
        else:
            filters.append(f"{last_v_stream}null[v_out]")
            last_v_stream = "[v_out]"

        # Audio handling: check for voiceover override, sound effects, and seamless loop fades
        fade_in_dur = 0.04  # Ultra-fast 40ms de-click fade-in
        loop_fade = 0.05 if enable_seamless_loop else 0.15
        fade_out_dur = min(loop_fade, duration / 5.0)
        out_start = max(0.0, duration - fade_out_dur)

        has_override_audio = bool(audio_override_path and os.path.exists(audio_override_path))
        
        # Determine extra audio inputs (dubbed voice and/or hook whoosh SFX)
        extra_inputs = []
        voice_stream = None
        sfx_stream = None
        current_input_idx = 1

        if has_override_audio:
            extra_inputs.extend(["-i", audio_override_path])
            voice_stream = f"[{current_input_idx}:a]"
            current_input_idx += 1
        elif has_audio:
            voice_stream = "[0:a]"

        sfx_path = cls.get_or_create_hook_sfx() if enable_hook_sfx else None
        if enable_hook_sfx and sfx_path and os.path.exists(sfx_path):
            extra_inputs.extend(["-i", sfx_path])
            sfx_stream = f"[{current_input_idx}:a]"
            current_input_idx += 1

        if voice_stream:
            if has_override_audio:
                filters.append(
                    f"{voice_stream}afade=t=in:ss=0:d={fade_in_dur:.2f},afade=t=out:st={out_start:.2f}:d={fade_out_dur:.2f}[a_voice]"
                )
            elif enable_audio_boost:
                filters.append(
                    f"{voice_stream}afade=t=in:ss=0:d={fade_in_dur:.2f},afade=t=out:st={out_start:.2f}:d={fade_out_dur:.2f},"
                    f"acompressor=threshold=-18dB:ratio=3:attack=5:release=50,volume=1.2[a_voice]"
                )
            else:
                filters.append(
                    f"{voice_stream}afade=t=in:ss=0:d={fade_in_dur:.2f},afade=t=out:st={out_start:.2f}:d={fade_out_dur:.2f}[a_voice]"
                )

            if sfx_stream:
                # Mix voice dialogue with punchy opening whoosh impact (attenuated -12dB)
                filters.append(f"{sfx_stream}volume=0.8[a_sfx]")
                filters.append(f"[a_voice][a_sfx]amix=inputs=2:duration=first:dropout_transition=2[a_out]")
                last_a_stream = "[a_out]"
            else:
                last_a_stream = "[a_voice]"
        elif sfx_stream:
            filters.append(f"{sfx_stream}volume=0.8[a_out]")
            last_a_stream = "[a_out]"
        else:
            last_a_stream = None

        filter_str = ";".join(filters)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", video_path,
        ]
        cmd.extend(extra_inputs)

        cmd.extend([
            "-filter_complex", filter_str,
            "-map", last_v_stream,
        ])

        if last_a_stream:
            cmd.extend(["-map", last_a_stream, "-c:a", "aac", "-b:a", audio_br])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", crf,
            "-pix_fmt", "yuv420p",
            "-avoid_negative_ts", "make_zero",
            output_path
        ])

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg render error: {res.stderr.decode('utf-8', errors='ignore')}")

        return output_path

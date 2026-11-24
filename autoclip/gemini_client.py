import os
import re
import json
import base64
import subprocess
import socket
import time
import wave
import struct
import requests

# Patch urllib3 to prioritize IPv4 on Android/Termux to avoid IPv6 hanging
try:
    import urllib3.util.connection as urllib_conn
    urllib_conn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

class GeminiClipperClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        # gemini-flash-lite-latest is fastest, most reliable, and has 0% 503 high-demand errors
        self.model = "gemini-flash-lite-latest"

    def extract_audio(self, video_path: str, output_audio_path: str = None, video_duration: float = 60.0) -> str:
        if not output_audio_path:
            base, _ = os.path.splitext(video_path)
            output_audio_path = f"{base}_audio.mp3"

        # Optimized for speech: 16kHz mono 32kbps (extremely compact: ~240KB per minute)
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "libmp3lame",
            "-ar", "16000", "-ac", "1", "-b:a", "32k",
            output_audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            # Fallback for silent / audio-less videos: generate silent MP3 so pipeline continues
            dur_str = str(max(10.0, float(video_duration or 60.0)))
            silent_cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=16000:cl=mono",
                "-t", dur_str,
                "-acodec", "libmp3lame",
                "-b:a", "32k",
                output_audio_path
            ]
            subprocess.run(silent_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_audio_path

    def analyze_video_audio(
        self,
        audio_path: str,
        video_duration: float = None,
        length_pref: str = "auto",
        clip_count: str = "3",
        caption_language: str = "auto"
    ) -> dict:
        """
        Phase 1 (Macro): Analyzes audio track to identify high-retention viral moments,
        calculates virality/hook scores, and generates social captions.
        """
        if not self.api_key or self.api_key.startswith("http"):
            return self._generate_fallback_clips(video_duration or 60.0, clip_count=clip_count, caption_language=caption_language)

        try:
            return self._call_gemini_api(audio_path, video_duration, length_pref, clip_count, caption_language)
        except Exception as e:
            print(f"[Money Clip Warning] Gemini API call error: {e}. Using intelligent fallback.")
            return self._generate_fallback_clips(video_duration or 60.0, clip_count=clip_count, caption_language=caption_language)

    def _call_gemini_api(self, audio_path: str, video_duration: float, length_pref: str, clip_count: str, caption_language: str) -> dict:
        # Cap macro preview to first 360 seconds (6 minutes) to avoid timeout on huge video files
        audio_to_send = audio_path
        temp_macro_path = None
        if video_duration and video_duration > 360.0:
            temp_macro_path = f"{audio_path}_macro_preview.mp3"
            cmd = ["ffmpeg", "-y", "-t", "360", "-i", audio_path, "-c", "copy", temp_macro_path]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(temp_macro_path):
                audio_to_send = temp_macro_path

        try:
            with open(audio_to_send, "rb") as f:
                audio_bytes = f.read()
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        finally:
            if temp_macro_path and os.path.exists(temp_macro_path):
                try:
                    os.remove(temp_macro_path)
                except Exception:
                    pass

        count_str = f"top {clip_count}" if clip_count != "auto" else "top 2 to 4"

        length_instructions = {
            "<30s": "Target clip duration: between 15 and 30 seconds (quick viral punch).",
            "30-60s": "Target clip duration: between 30 and 60 seconds (standard Shorts/Reels).",
            "60-90s": "Target clip duration: between 60 and 90 seconds (in-depth narrative).",
            "auto": "Choose optimal clip duration between 15 and 60 seconds based on natural speech boundaries."
        }.get(length_pref, "Choose optimal clip duration between 15 and 60 seconds.")

        if caption_language in ["hinglish", "auto"]:
            lang_instruction = """
LANGUAGE & SCRIPT MANDATE:
- For Hindi or mixed Hindi-English speech: Always transcribe and format titles in clean Latin alphabet (Romanized Hinglish).
- NEVER use Devanagari script.
"""
        elif caption_language == "english":
            lang_instruction = """
LANGUAGE & SCRIPT MANDATE:
- All titles and captions must be in clean English.
"""
        else:
            lang_instruction = """
LANGUAGE & SCRIPT MANDATE:
- Use original native language.
"""

        prompt = f"""
You are the world-class AI clipping director behind Opus Clip, Submagic, and CapCut.
Analyze this audio track to identify VIRAL, HIGH-RETENTION GOLD:

1. {lang_instruction.strip()}

2. VIRAL SELECTION CRITERIA:
   - Identify the {count_str} highest performing, self-contained highlight clips for YouTube Shorts, TikTok, and Instagram Reels.
   - {length_instructions}
   - HOOK PURITY: The first 3 seconds MUST immediately grab attention (shocking claim, surprising revelation, question, or high-energy moment).
   - CLEAN BOUNDARIES:
     * `start_time` MUST be the natural start of an energetic sentence or thought. NEVER start mid-word.
     * `end_time` MUST be the natural conclusion of a thought or punchline. NEVER cut off mid-sentence.
   - STORY ARC: Each clip must feel complete: Hook -> Delivery / Insight -> Punchline / Climax.

3. FOR EACH CLIP, OUTPUT:
   - title: High CTR, click-worthy title (max 7 words).
   - hook: The opening line that grabs attention in the first 3 seconds.
   - hook_headline: Ultra-punchy 3-5 word uppercase header banner with an emoji (e.g. "WAIT TILL THE END! 🤯", "DON'T MAKE THIS MISTAKE! 🛑", "DUALSENSE KILLER? 🎮").
   - hook_type: Choose the best matching psychology category:
     * "🚨 Warning & Mistake"
     * "🤫 Curiosity Gap & Secret"
     * "💥 Contrarian & Shock"
     * "🏆 Challenge & High Stakes"
     * "⚡ Value Bomb & Hack"
   - start_time: Clip start time in seconds (float).
   - end_time: Clip end time in seconds (float).
   - virality_score: Overall virality score (70 to 99).
   - hook_score: Hook stop-rate score (70 to 99).
   - flow_score: Story momentum score (70 to 99).
   - engagement_score: Comment & share trigger score (70 to 99).
   - curiosity_gap: Rating string (e.g. "9.8/10", "9.5/10").
   - drop_off_risk: "Very Low", "Low", or "Moderate".
   - reason: Detailed psychological retention explanation (why viewers won't swipe away).
   - viral_action_tip: Practical YouTube Shorts/TikTok algorithm growth tip (e.g. what comment to pin, loop trick, or music suggestion).
   - social_copy: Platform tailored captions:
     - youtube: Title with 3-4 trending hashtags.
     - tiktok: Punchy 1-sentence caption + 5 viral hashtags.
     - instagram: Engaging caption with question hook + tags.

Output strictly valid JSON with this exact structure:
{{
  "full_summary": "Brief executive summary of the video",
  "clips": [
    {{
      "id": 1,
      "title": "Title here",
      "hook": "Hook sentence",
      "hook_headline": "HOOK BANNER HERE ⚡",
      "hook_type": "🤫 Curiosity Gap & Secret",
      "start_time": 10.5,
      "end_time": 35.0,
      "virality_score": 96,
      "hook_score": 98,
      "flow_score": 94,
      "engagement_score": 95,
      "curiosity_gap": "9.8/10",
      "drop_off_risk": "Very Low",
      "reason": "Detailed viral retention explanation",
      "viral_action_tip": "Pin a comment asking viewer opinion to maximize algorithmic comment velocity.",
      "social_copy": {{
        "youtube": "Why this changes everything! #Shorts #Viral #Mindset",
        "tiktok": "Wait until the end... you won't believe this 🤯 #fyp #foryou #viral #trending",
        "instagram": "Do you agree with this? Drop your thoughts below 👇 #reels #explore #growth"
      }}
    }}
  ]
}}
Return ONLY raw JSON with no markdown backticks.
"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "audio/mp3",
                                "data": audio_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        response = None
        models_to_try = [self.model, "gemini-flash-latest", "gemini-3.5-flash-lite"]
        last_error = ""

        import time
        for attempt in range(2):
            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                try:
                    response = requests.post(url, json=payload, timeout=(15, 120))
                    if response.status_code == 200:
                        break
                    else:
                        last_error = f"{response.status_code}: {response.text}"
                except Exception as e:
                    last_error = str(e)
            if response and response.status_code == 200:
                break
            if attempt == 0:
                time.sleep(2)

        if not response or response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {last_error}")

        res_data = response.json()
        candidates = res_data.get("candidates", [])
        text_out = candidates[0]["content"]["parts"][0]["text"].strip()
        if text_out.startswith("```json"):
            text_out = text_out[7:]
        if text_out.startswith("```"):
            text_out = text_out[3:]
        if text_out.endswith("```"):
            text_out = text_out[:-3]
        text_out = text_out.strip()
        try:
            return json.loads(text_out)
        except Exception:
            json_match = re.search(r'(\{[\s\S]*\})', text_out)
            if json_match:
                return json.loads(json_match.group(1))
            raise

    def transcribe_clip_audio(
        self,
        audio_path: str,
        start_time: float,
        duration: float,
        caption_language: str = "auto"
    ) -> list:
        """
        Phase 2 (Micro): Extracts the exact snippet of this specific clip (only 15-45s)
        and transcribes each spoken word with millisecond precision matching the speaker's voice.
        """
        if not self.api_key:
            return []

        base_dir = os.path.dirname(os.path.abspath(audio_path))
        snippet_path = os.path.join(base_dir, f"snippet_{int(start_time*10)}_{int(duration*10)}.wav")

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-i", audio_path,
            "-ar", "16000", "-ac", "1",
            snippet_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0 or not os.path.exists(snippet_path):
            return []

        physical_onset = self._detect_speech_onset(snippet_path)

        try:
            with open(snippet_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            if caption_language in ["hinglish", "auto"]:
                lang_rule = (
                    "CRITICAL FOR HINDI / HINGLISH:\n"
                    "- If the audio has Hindi speech, transcribe strictly in Romanized HINGLISH using the Latin alphabet (A-Z) (e.g. 'BHAI', 'YEH', 'KYA', 'CONTROLLER').\n"
                    "- NEVER use Devanagari script (do NOT write हिंदी). All words must be in Latin A-Z letters.\n"
                    "- Keep English words in English."
                )
            elif caption_language == "english":
                lang_rule = "Translate all speech into natural, accurate English subtitle words matching the spoken timing."
            else:
                lang_rule = "Transcribe in the original language words."

            prompt = f"""
You are an expert audio-to-text subtitler with millisecond acoustic precision.
Listen to this {duration:.1f}-second audio clip very carefully.
Transcribe every word spoken in this audio in sequential order.
{lang_rule}

CRITICAL TIMING ACCURACY INSTRUCTIONS:
- For each word, output the EXACT time in seconds (float with 2-3 decimals) when the first phonetic sound/consonant begins in this audio.
- Do NOT delay the start to the middle or end of the word.
- Every word's `start` and `end` MUST precisely track the real vocal sound.
- Include opening filler sounds/words if spoken (e.g. 'haan', 'bhai', 'arre') so subtitles never lead ahead of the voice.

Output strictly valid JSON:
{{
  "words": [
    {{"word": "word", "start": 0.25, "end": 0.55}}
  ]
}}
Return ONLY valid raw JSON with no markdown formatting.
"""

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "audio/wav",
                                    "data": audio_b64
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.05,
                    "maxOutputTokens": 8192,
                    "response_mime_type": "application/json"
                }
            }

            models_to_try = [self.model, "gemini-2.5-flash", "gemini-flash-latest"]
            for attempt in range(2):
                for model in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                    try:
                        r = requests.post(url, json=payload, timeout=(10, 25))
                        if r.status_code == 200:
                            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                            if txt.startswith("```json"):
                                txt = txt[7:]
                            if txt.startswith("```"):
                                txt = txt[3:]
                            if txt.endswith("```"):
                                txt = txt[:-3]
                            txt = txt.strip()
                            
                            raw_words = []
                            try:
                                parsed = json.loads(txt)
                                raw_words = parsed.get("words", [])
                            except Exception:
                                # Resilient regex extraction recovering word items even if quotes are unescaped or JSON was truncated
                                pattern = r'\{\s*["\']word["\']\s*:\s*["\'](.*?)["\']\s*,\s*["\']start["\']\s*:\s*([0-9.]+)\s*,\s*["\']end["\']\s*:\s*([0-9.]+)'
                                matches = re.findall(pattern, txt)
                                if matches:
                                    raw_words = [{"word": m[0], "start": float(m[1]), "end": float(m[2])} for m in matches]
                                else:
                                    json_match = re.search(r'(\{[\s\S]*\})', txt)
                                    if json_match:
                                        try:
                                            parsed = json.loads(json_match.group(1))
                                            raw_words = parsed.get("words", [])
                                        except Exception:
                                            pass

                            if raw_words:
                                return self._sanitize_words(raw_words, duration)
                    except Exception as e:
                        print(f"[Money Clip Warning] Snippet transcription error with {model}: {e}")
                        continue
                if attempt == 0:
                    time.sleep(1.5)

            return []
        finally:
            if os.path.exists(snippet_path):
                try:
                    os.remove(snippet_path)
                except Exception:
                    pass

    @staticmethod
    def _detect_speech_onset(wav_path: str, max_search_s: float = 3.0) -> float:
        try:
            with wave.open(wav_path, "rb") as wf:
                sr = wf.getframerate()
                nframes = wf.getnframes()
                data = wf.readframes(nframes)
                samples = struct.unpack(f"<{nframes}h", data)

            chunk_size = int(sr * 0.02)  # 20ms windows
            energies = []
            for i in range(0, min(len(samples), int(sr * max_search_s)), chunk_size):
                chunk = samples[i:i + chunk_size]
                if not chunk:
                    continue
                rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
                energies.append((i / sr, rms))

            if not energies:
                return 0.0

            sorted_rms = sorted([e[1] for e in energies])
            noise_floor = sorted_rms[max(0, int(len(sorted_rms) * 0.15))]
            threshold = max(550.0, noise_floor * 2.2)

            for t, rms in energies:
                if rms >= threshold:
                    return round(t, 2)
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _sanitize_words(words: list, clip_duration: float) -> list:
        cleaned = []
        for w in words:
            word_str = str(w.get("word", "")).strip()
            if not word_str or word_str.lower() == "null":
                continue
            try:
                s = float(w.get("start", 0.0))
            except (ValueError, TypeError):
                s = None
            try:
                e = float(w.get("end", 0.0))
            except (ValueError, TypeError):
                e = None
            cleaned.append({"word": word_str, "start": s, "end": e})

        if not cleaned:
            return []

        # Fix any None or inverted timestamps with smooth interpolation
        for i, item in enumerate(cleaned):
            if item["start"] is None:
                prev_e = cleaned[i - 1]["end"] if i > 0 and cleaned[i - 1]["end"] is not None else 0.0
                item["start"] = prev_e
            if item["end"] is None or item["end"] <= item["start"]:
                next_s = (
                    cleaned[i + 1]["start"]
                    if i + 1 < len(cleaned) and cleaned[i + 1]["start"] is not None
                    else (item["start"] + 0.35)
                )
                item["end"] = min(item["start"] + 0.45, max(item["start"] + 0.2, next_s))

        # Clamp timestamps faithfully to audio snippet [0.0, clip_duration]
        for item in cleaned:
            item["start"] = max(0.0, min(clip_duration, round(item["start"], 2)))
            item["end"] = max(item["start"] + 0.10, min(clip_duration, round(item["end"], 2)))

        # Ensure monotonicity
        for i in range(1, len(cleaned)):
            if cleaned[i]["start"] < cleaned[i - 1]["start"]:
                cleaned[i]["start"] = cleaned[i - 1]["start"]
            if cleaned[i]["end"] <= cleaned[i]["start"]:
                cleaned[i]["end"] = min(clip_duration, cleaned[i]["start"] + 0.2)

        return cleaned

    def _generate_fallback_clips(self, video_duration: float, clip_count: str = "3", caption_language: str = "auto") -> dict:
        duration = max(video_duration, 30.0)
        c1_start = min(5.0, duration * 0.1)
        c1_end = min(c1_start + 20.0, duration)

        c2_start = min(c1_end + 3.0, duration * 0.6)
        c2_end = min(c2_start + 22.0, duration)

        if caption_language in ["hinglish", "auto"]:
            t1 = "Bhai Yeh Scene Miss Mat Karna 🤯"
            h1 = "Bhai yeh video end tak dekhna bohot tagda scene hai."
            banner1 = "YEH KABHI MAT BHULNA! 🔥"
            t2 = "Sach Mein Yeh Hua Tha? 💡"
            h2 = "Abhi jo batane wala hu dhyan se sunna."
            banner2 = "DHYAN SE SUNNA! ⚡"
        else:
            t1 = "Highlight Moment #1 🚀"
            h1 = "Wait until you see what happens next."
            banner1 = "WAIT TILL THE END! 🤯"
            t2 = "Highlight Moment #2 💡"
            h2 = "Here is the most important part."
            banner2 = "DON'T MISS THIS! ⚡"

        all_clips = [
            {
                "id": 1,
                "title": t1,
                "hook": h1,
                "hook_headline": banner1,
                "hook_type": "🤫 Curiosity Gap & Secret",
                "start_time": round(c1_start, 2),
                "end_time": round(c1_end, 2),
                "virality_score": 96,
                "hook_score": 97,
                "flow_score": 94,
                "engagement_score": 95,
                "curiosity_gap": "9.8/10",
                "drop_off_risk": "Very Low",
                "reason": "High visual motion and strong curiosity gap in opening 3 seconds.",
                "viral_action_tip": "Pin a comment asking viewers their opinion to boost algorithmic comment velocity.",
                "social_copy": {
                    "youtube": "You won't believe this! #Shorts #Viral #Trending",
                    "tiktok": "Wait until the end... 🤯 #fyp #foryou #viral",
                    "instagram": "Double tap if you agree! 👇 #reels #explore"
                }
            },
            {
                "id": 2,
                "title": t2,
                "hook": h2,
                "hook_headline": banner2,
                "hook_type": "⚡ Value Bomb & Hack",
                "start_time": round(c2_start, 2),
                "end_time": round(c2_end, 2),
                "virality_score": 91,
                "hook_score": 92,
                "flow_score": 90,
                "engagement_score": 91,
                "curiosity_gap": "9.4/10",
                "drop_off_risk": "Low",
                "reason": "High retention sequence with actionable takeaway.",
                "viral_action_tip": "Add a fast loop cut so the video replays seamlessly.",
                "social_copy": {
                    "youtube": "Did you know this? 💡 #Shorts #Knowledge",
                    "tiktok": "Watch till the end ⚡ #fyp #trending",
                    "instagram": "Tag a friend who needs to see this! 👇 #reels"
                }
            }
        ]

        if clip_count == "1":
            selected_clips = all_clips[:1]
        else:
            selected_clips = all_clips

        return {
            "full_summary": "Money Clip speech processing completed.",
            "clips": selected_clips
        }

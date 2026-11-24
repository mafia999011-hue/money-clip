import os
import re
import json
import uuid
import urllib.request
import urllib.parse
import subprocess
import requests

SUPPORTED_DUB_LANGUAGES = {
    "none": "Original Audio (No Dubbing)",
    "en": "English (US / Global)",
    "hi": "Hindi (हिंदी)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ja": "Japanese (日本語)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
    "ar": "Arabic (العربية)",
    "id": "Indonesian (Bahasa)"
}

class AIDubber:
    @staticmethod
    def is_dubbing_enabled(dub_lang: str) -> bool:
        return bool(dub_lang and dub_lang != "none" and dub_lang in SUPPORTED_DUB_LANGUAGES)

    @classmethod
    def translate_script(cls, source_text: str, target_lang: str, api_key: str = None) -> str:
        """
        Translates original spoken script into natural, conversational, punchy speech
        tailored for short-form video dubbing.
        """
        if not source_text or not source_text.strip():
            return ""

        lang_name = SUPPORTED_DUB_LANGUAGES.get(target_lang, target_lang)

        if not api_key:
            return source_text

        prompt = f"""
You are an expert film and video dubbing translator.
Translate this spoken dialogue into natural, engaging spoken {lang_name} for a viral short video:
"{source_text}"

CRITICAL RULES:
- Translate for SPOKEN voiceover (natural, punchy, conversational tone).
- Keep roughly the same length and cadence so it fits video timing.
- Do NOT add markdown, explanations, or quotes. Output ONLY the translated spoken sentence.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200}
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                translated = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean any quotes or formatting
                translated = re.sub(r'^["\']|["\']$', '', translated).strip()
                return translated or source_text
        except Exception as e:
            print(f"[Money Clip Dubbing] Translation warning: {e}")

        return source_text

    @classmethod
    def synthesize_speech(cls, text: str, target_lang: str, output_path: str, target_duration: float = None) -> str:
        """
        Synthesizes translated text into high-quality spoken audio MP3,
        and dynamically adjusts speed/tempo via FFmpeg to match the target clip duration.
        """
        if not text or not text.strip():
            return None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        raw_mp3 = f"{output_path}_raw.mp3"

        # Split text into bite-sized sentences if longer than 150 chars
        chunks = [c.strip() for c in re.split(r'[,.!?;\n]+', text) if c.strip()]
        if not chunks:
            chunks = [text[:180]]

        part_files = []
        for idx, chunk in enumerate(chunks[:8]):
            part_path = f"{output_path}_part_{idx}.mp3"
            encoded_text = urllib.parse.quote(chunk[:180])
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl={target_lang}&client=tw-ob"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    with open(part_path, "wb") as f:
                        f.write(resp.read())
                if os.path.exists(part_path) and os.path.getsize(part_path) > 100:
                    part_files.append(part_path)
            except Exception as e:
                print(f"[Money Clip Dubbing] TTS error on chunk '{chunk}': {e}")

        if not part_files:
            return None

        # Concatenate audio parts
        if len(part_files) == 1:
            shutil_copy = ["cp", part_files[0], raw_mp3]
            subprocess.run(shutil_copy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            list_txt = f"{output_path}_parts.txt"
            with open(list_txt, "w") as f:
                for pf in part_files:
                    f.write(f"file '{os.path.abspath(pf)}'\n")
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_txt, "-c", "copy", raw_mp3
            ]
            subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(list_txt):
                try: os.remove(list_txt)
                except Exception: pass

        # Clean part files
        for pf in part_files:
            if os.path.exists(pf):
                try: os.remove(pf)
                except Exception: pass

        if not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) < 200:
            return None

        # Probe raw audio duration
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", raw_mp3
        ]
        probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            raw_dur = float(probe_res.stdout.decode().strip())
        except Exception:
            raw_dur = target_duration or 10.0

        # Adjust tempo if target_duration provided (bounded to 0.75x - 1.5x)
        if target_duration and raw_dur > 0.5:
            speed_factor = raw_dur / target_duration
            speed_factor = min(1.4, max(0.8, speed_factor))
            tempo_cmd = [
                "ffmpeg", "-y", "-i", raw_mp3,
                "-filter:a", f"atempo={speed_factor:.2f}",
                "-c:a", "libmp3lame", "-b:a", "128k",
                output_path
            ]
            res = subprocess.run(tempo_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(raw_mp3):
                try: os.remove(raw_mp3)
                except Exception: pass
            if res.returncode == 0 and os.path.exists(output_path):
                return output_path

        # If no tempo adjustment needed
        if os.path.exists(raw_mp3):
            os.rename(raw_mp3, output_path)
            return output_path

        return None

    @classmethod
    def duck_and_mix_audio(
        cls,
        original_input: str,
        start_time: float,
        duration: float,
        dub_audio_path: str,
        output_audio_path: str,
        bg_duck_vol: float = 0.12,
        voice_vol: float = 1.05
    ) -> str:
        """
        Ducks original video background sound down to 12% volume (preserving gameplay/music)
        and overlays the crystal-clear AI Dubbed voiceover with vocal compression.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)

        filter_str = (
            f"[0:a]volume={bg_duck_vol}[bg];"
            f"[1:a]volume={voice_vol},acompressor=threshold=-16dB:ratio=3:attack=5:release=50[dub];"
            f"[bg][dub]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", original_input,
            "-i", dub_audio_path,
            "-filter_complex", filter_str,
            "-map", "[aout]",
            "-c:a", "aac", "-b:a", "192k",
            output_audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_audio_path):
            return output_audio_path

        # Fallback to dub audio if mixing failed
        return dub_audio_path

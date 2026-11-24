import os
import re

EMOJI_KEYWORDS = {
    # English Keywords
    "MONEY": "💰", "CASH": "💵", "RICH": "🤑", "PROFIT": "📈", "DOLLAR": "💵", "BILLION": "💎", "MILLION": "💎",
    "FIRE": "🔥", "LIT": "🔥", "HOT": "🔥", "BURN": "🔥",
    "ROCKET": "🚀", "GROWTH": "🚀", "SUCCESS": "🏆", "WIN": "🏆", "WINNER": "🏆", "BEST": "🥇", "TOP": "🔝",
    "SECRET": "🤫", "HACK": "⚡", "TRICK": "🎯", "CHALLENGE": "🎯", "GOAL": "🎯",
    "MIND": "🧠", "BRAIN": "🧠", "THINK": "💡", "IDEA": "💡",
    "CRAZY": "🤯", "INSANE": "🤯", "SHOCKING": "😱", "WOW": "😲", "UNBELIEVABLE": "🤯",
    "TIME": "⏳", "CLOCK": "⏰", "WAIT": "⏱️", "NOW": "⚡", "FAST": "⚡", "SPEED": "🏎️",
    "LOVE": "❤️", "HEART": "❤️", "PASSION": "❤️", "CARE": "❤️",
    "WARNING": "⚠️", "DANGER": "🚨", "MISTAKE": "❌", "STOP": "🛑", "WRONG": "❌", "ALERT": "🚨",
    "QUESTION": "❓", "WHY": "❓", "HOW": "❓", "WHAT": "❓",
    "STRONG": "💪", "POWER": "⚡", "ENERGY": "⚡", "BEAST": "🦁",
    "KILLER": "💀", "DEAD": "💀", "GAME": "🎮", "GAMING": "🎮", "CONTROLLER": "🎮",
    "PHONE": "📱", "MOBILE": "📱", "COMPUTER": "💻", "PC": "💻", "CAMERA": "📸", "MIC": "🎙️",
    "FREE": "🎁", "GIFT": "🎁", "LUCK": "🍀", "CAR": "🚗",

    # Hinglish & Hindi Keywords
    "PAISA": "💰", "PAISE": "💰", "AMEER": "🤑", "DAULAT": "💵", "LAKH": "💰", "CRORE": "💰",
    "AAG": "🔥", "DHAMAKA": "💥", "BOMB": "💣", "KHATARNAK": "⚡",
    "JEET": "🏆", "JEETA": "🏆", "KAMIYAB": "🚀", "NUMBER1": "🥇", "BAAP": "👑", "KING": "👑", "RAJA": "👑",
    "RAAZ": "🤫", "SECRET": "🤫", "CHHUPA": "🤫", "CHORI": "🕵️",
    "DIMAG": "🧠", "SOCH": "💡", "IDEA": "💡", "SAMJH": "💡",
    "PAGAL": "🤯", "GAJAB": "🤯", "BAWAL": "💥", "SHANDAR": "✨", "JADU": "🪄",
    "WAQT": "⏳", "SAMAY": "⏰", "ROKO": "🛑", "JALDI": "⚡", "TURANT": "⚡",
    "DIL": "❤️", "PYAR": "❤️", "JAAN": "❤️", "DOST": "🤝", "YAAR": "🤝",
    "GALTI": "❌", "KHATRA": "⚠️", "KHARAB": "❌", "MAT": "🛑", "DHOKA": "⚠️", "JHUTH": "🤥",
    "SACH": "💯", "ASLI": "💎", "NAQLI": "🤡",
    "KYU": "❓", "KYA": "❓", "KAISE": "❓", "KAB": "❓", "KAUN": "❓",
    "TAQAT": "💪", "DUM": "💪", "MAZA": "🥳", "HASI": "😂", "ROYA": "😭"
}

STYLE_PRESETS = {
    "hormozi": {
        "name": "Hormozi Yellow",
        "highlight": "&H0000FFFF&", # Yellow (\c&H0000FFFF&)
        "base": "&H00FFFFFF&",      # White (\c&H00FFFFFF&)
        "outline": "&H00000000&",   # Black
        "font_size": 76,
        "outline_w": 8
    },
    "mrbeast": {
        "name": "MrBeast Neon Green",
        "highlight": "&H0000FF00&", # Neon Green
        "base": "&H00FFFFFF&",
        "outline": "&H00000000&",
        "font_size": 76,
        "outline_w": 8
    },
    "cyberpunk": {
        "name": "Cyberpunk Cyan",
        "highlight": "&H00FFFF00&", # Cyan
        "base": "&H00FFFFFF&",
        "outline": "&H004A0080&",   # Dark purple
        "font_size": 74,
        "outline_w": 8
    },
    "sunset": {
        "name": "Sunset Pink",
        "highlight": "&H00FF00FF&", # Magenta
        "base": "&H00FFFFFF&",
        "outline": "&H00000000&",
        "font_size": 74,
        "outline_w": 8
    },
    "devin": {
        "name": "Devin Viral Gold & Red",
        "highlight": "&H0000D7FF&", # Gold
        "base": "&H00FFFFFF&",
        "outline": "&H001111B3&",   # Deep Red
        "font_size": 76,
        "outline_w": 8
    },
    "minimal_clean": {
        "name": "Clean White & Electric Blue",
        "highlight": "&H00FFAA00&", # Electric Blue
        "base": "&H00FFFFFF&",
        "outline": "&H001A1A1A&",   # Deep Charcoal
        "font_size": 74,
        "outline_w": 8
    },
    "ali_abdaal": {
        "name": "Ali Abdaal Minimalist",
        "highlight": "&H0066F0FF&", # Pastel Butter Yellow
        "base": "&H00F8FAFC&",      # Soft Off-White
        "outline": "&H001E293B&",   # Slate Gray
        "font_size": 72,
        "outline_w": 6
    },
    "iman_gadzhi": {
        "name": "Iman Gadzhi Luxury Gold",
        "highlight": "&H0078C3E5&", # Champagne Luxury Gold
        "base": "&H00FFFFFF&",      # Crisp White
        "outline": "&H00000000&",   # Deep Obsidian Black
        "font_size": 74,
        "outline_w": 8
    },
    "gaming_rgb": {
        "name": "Gaming Neon RGB",
        "highlight": "&H0000FFFF&", # Electric Neon Yellow
        "base": "&H0000FF00&",      # Neon Green Base
        "outline": "&H00000000&",   # Pitch Black
        "font_size": 78,
        "outline_w": 9
    },
    "vhs_retro": {
        "name": "Retro 90s VHS Synthwave",
        "highlight": "&H00008CFF&", # Amber Orange
        "base": "&H0000FFFF&",      # Yellow Base
        "outline": "&H00800040&",   # Dark Teal
        "font_size": 76,
        "outline_w": 8
    },
    "crimson_urgent": {
        "name": "Crimson Urgency Red",
        "highlight": "&H00271EFF&", # Vibrant Crimson Red
        "base": "&H00FFFFFF&",      # Pure White
        "outline": "&H00000000&",   # Pitch Black
        "font_size": 78,
        "outline_w": 9
    }
}

ASPECT_RESOLUTIONS = {
    "9:16": {"720p": (720, 1280), "1080p": (1080, 1920), "1440p": (1440, 2560), "margin_ratio": 0.25},
    "1:1":  {"720p": (720, 720),   "1080p": (1080, 1080), "1440p": (1440, 1440), "margin_ratio": 0.14},
    "16:9": {"720p": (1280, 720),  "1080p": (1920, 1080), "1440p": (2560, 1440), "margin_ratio": 0.12},
    "4:5":  {"720p": (720, 900),   "1080p": (1080, 1350), "1440p": (1440, 1800), "margin_ratio": 0.18},
}

class SubtitleGenerator:
    @staticmethod
    def format_ass_time(seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    @classmethod
    def generate_ass(
        cls,
        words: list,
        clip_start: float,
        clip_end: float,
        output_ass_path: str,
        preset_name: str = "hormozi",
        aspect_ratio: str = "9:16",
        enable_emojis: bool = True,
        words_per_group: int = 2,
        video_quality: str = "1080p",
        hook_headline: str = None,
        show_hook_header: bool = True
    ) -> str:
        preset = STYLE_PRESETS.get(preset_name, STYLE_PRESETS["hormozi"])
        highlight_color = preset["highlight"]
        base_color = preset["base"]
        outline_color = preset["outline"]

        ar_cfg = ASPECT_RESOLUTIONS.get(aspect_ratio, ASPECT_RESOLUTIONS["9:16"])
        res_x, res_y = ar_cfg.get(video_quality, ar_cfg["1080p"])
        scale_ref = min(res_x, res_y)

        font_size = int(preset["font_size"] * (scale_ref / 1080))
        outline_w = max(4, int(preset["outline_w"] * (scale_ref / 1080)))
        margin_v = int(res_y * ar_cfg.get("margin_ratio", 0.25))

        hook_font_size = int(font_size * 0.72)
        hook_margin_v = int(res_y * 0.10)

        valid_words = []
        for w in words:
            try:
                raw_s = float(w.get("start", 0.0))
                raw_e = float(w.get("end", raw_s + 0.3))
            except (ValueError, TypeError):
                continue

            w_start = raw_s - clip_start
            w_end = raw_e - clip_start
            raw_word = str(w.get("word", "")).strip().upper()
            if not raw_word:
                continue

            clean_word = re.sub(r'[^A-Z0-9]', '', raw_word)
            emoji_tag = ""
            if enable_emojis and clean_word in EMOJI_KEYWORDS:
                emoji_tag = f" {EMOJI_KEYWORDS[clean_word]}"

            if w_end >= 0 and w_start <= (clip_end - clip_start):
                valid_words.append({
                    "word": raw_word + emoji_tag,
                    "start": max(0.0, w_start),
                    "end": min(clip_end - clip_start, max(0.05, w_end))
                })

        # Group words into punchy 2-word chunks (Opus Clip / Hormozi pacing)
        chunks = []
        for i in range(0, len(valid_words), words_per_group):
            chunks.append(valid_words[i:i + words_per_group])

        # Modern high-impact vertical subtitle styling matching target resolution
        ass_content = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {res_x}",
            f"PlayResY: {res_y}",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,Arial,{font_size},{base_color},&H000000FF&,{outline_color},&H80000000&,-1,0,0,0,100,100,2,0,1,{outline_w},4,2,60,60,{margin_v},1",
            f"Style: HookHeader,Arial,{hook_font_size},{highlight_color},&H000000FF&,{outline_color},&H90000000&,-1,0,0,0,100,100,2,0,1,{max(5, int(outline_w*0.85))},4,8,60,60,{hook_margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        # Top Hook Banner: displays for the opening 4.5 seconds with explosive scale-pop entrance
        if show_hook_header and hook_headline:
            clean_headline = hook_headline.strip().upper()
            hook_duration = min(4.5, max(1.5, clip_end - clip_start))
            end_time_str = cls.format_ass_time(hook_duration)
            ass_content.append(
                f"Dialogue: 1,0:00:00.00,{end_time_str},HookHeader,,0,0,0,,{{\\fad(60,300)\\fscx135\\fscy135\\t(0,220,\\fscx100\\fscy100)\\b1}}🔥 {clean_headline} 🔥"
            )

        for c_idx, chunk in enumerate(chunks):
            next_chunk_start = chunks[c_idx + 1][0]["start"] if c_idx + 1 < len(chunks) else clip_end - clip_start
            for active_idx, target_word in enumerate(chunk):
                w_start = target_word["start"]
                if active_idx + 1 < len(chunk):
                    # Keep dialogue visible until next word in chunk begins (smooth continuous flow)
                    w_end = chunk[active_idx + 1]["start"]
                else:
                    # Last word in chunk: keep on screen until next chunk starts for continuous flow
                    # If there is a natural pause (> 1.0s), hold word for 0.5s before fading
                    gap = next_chunk_start - target_word["start"]
                    if gap <= 1.0:
                        w_end = next_chunk_start
                    else:
                        w_end = max(target_word["end"] if target_word["end"] is not None else 0.0, target_word["start"] + 0.5)
                if w_end <= w_start:
                    w_end = w_start + 0.3

                line_parts = []
                for idx, item in enumerate(chunk):
                    if idx == active_idx:
                        # Enhanced dynamic scale-pop (130% for viral power words, 122% standard)
                        clean_w = re.sub(r'[^A-Z0-9]', '', str(item["word"]).upper())
                        is_power = clean_w in EMOJI_KEYWORDS or clean_w in {"NEVER", "ALWAYS", "SECRET", "MISTAKE", "CRAZY", "STOP", "INSANE", "WAIT", "SHOCKING", "DANGER", "MONEY"}
                        scale = "130" if is_power else "122"
                        line_parts.append(
                            rf"{{\fscx{scale}\fscy{scale}\c{highlight_color}\b1}}" +
                            item["word"] +
                            rf"{{\fscx100\fscy100\c{base_color}\b1}}"
                        )
                    else:
                        line_parts.append(item["word"])

                text_str = " ".join(line_parts)
                start_str = cls.format_ass_time(w_start)
                end_str = cls.format_ass_time(w_end)

                ass_content.append(
                    f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text_str}"
                )

        os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_content))

        return output_ass_path

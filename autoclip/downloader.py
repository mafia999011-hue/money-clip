import os
import re
import uuid
import shutil
import yt_dlp
from .live_recorder import LiveStreamRecorder

def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "twitch.tv" in url_lower:
        return "Twitch"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    if "tiktok.com" in url_lower:
        return "TikTok"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "X / Twitter"
    if "kick.com" in url_lower:
        return "Kick"
    return "Web Video"

def download_online_video(url: str, output_dir: str, live_duration: int = 180, progress_callback = None) -> dict:
    """
    High-speed online video downloader for YouTube, Twitch, TikTok, etc.
    Optimized with multi-fragment concurrent downloading, 10MB chunking to bypass
    YouTube ISP throttling, and direct android client resolution for instant 2-3s fetch.
    """
    os.makedirs(output_dir, exist_ok=True)
    platform = detect_platform(url)

    # If user explicitly provided a known live broadcast URL pattern
    is_explicit_live = any(x in url.lower() for x in ["/live", "/channel/", "twitch.tv/"]) and "watch?v=" not in url.lower()
    if is_explicit_live:
        live_info = LiveStreamRecorder.inspect_url(url)
        if live_info.get("is_live"):
            return LiveStreamRecorder.record_live_snippet(
                url=url,
                output_dir=output_dir,
                duration_seconds=live_duration,
                progress_callback=progress_callback
            )

    unique_prefix = uuid.uuid4().hex[:8]
    out_template = os.path.join(output_dir, f"{unique_prefix}_%(title).50s.%(ext)s")
    
    node_path = shutil.which('node')
    ydl_opts = {
        # Prefer fast MP4/M4A streams (1080p max) that merge in <0.5s without re-encoding
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best[height<=720]/best',
        'outtmpl': out_template,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        # Multi-thread 8 concurrent fragments + 10MB chunking bypasses YouTube 1.5MB/s throttling
        'concurrent_fragment_downloads': 8,
        'buffersize': 1024 * 1024,
        'http_chunk_size': 10485760,
        'retries': 3,
        'fragment_retries': 3,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        }
    }
    if node_path:
        ydl_opts['js_runtimes'] = {'node': {'path': node_path}}

    if progress_callback:
        def yt_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                pct = int((downloaded / total * 100)) if total > 0 else 50
                speed = d.get('speed') or 0
                speed_str = f"{(speed / (1024*1024)):.1f} MB/s" if speed > 0 else "High-speed"
                progress_callback(f"Downloading video: {pct}% ({speed_str})...", pct)
            elif d['status'] == 'finished':
                progress_callback("Muxing video streams...", 95)
        ydl_opts['progress_hooks'] = [yt_hook]

    # Automatic cookie detection for age-restricted / member-only YouTube videos
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_cookies = [
        os.path.join(base_dir, "..", "data", "cookies.txt"),
        os.path.join(base_dir, "..", "cookies.txt"),
        os.path.join(os.path.expanduser("~"), "cookies.txt")
    ]
    for c_path in possible_cookies:
        if os.path.exists(c_path) and os.path.getsize(c_path) > 10:
            ydl_opts['cookiefile'] = c_path
            break
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            final_filename = f"{base}.mp4"
            if not os.path.exists(final_filename) and os.path.exists(filename):
                final_filename = filename

            raw_title = info.get("title") or f"{platform} Video"
            clean_title = re.sub(r'[\r\n\t]+', ' ', raw_title).strip()

            return {
                "video_id": os.path.basename(final_filename),
                "title": clean_title,
                "duration": info.get("duration", 0),
                "platform": platform,
                "filepath": final_filename
            }
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm your age" in err_msg or "inappropriate for some users" in err_msg:
            raise RuntimeError(
                "This video is Age-Restricted (18+) by YouTube and requires login authentication. "
                "To process it: 1) Download the MP4 and drop it into the 'Upload Video' tab, or "
                "2) Save a YouTube 'cookies.txt' file in the 'data/' folder."
            )
        elif "Private video" in err_msg:
            raise RuntimeError("This YouTube video is set to Private.")
        elif "Video unavailable" in err_msg:
            raise RuntimeError("This YouTube video is unavailable or has been removed.")
        else:
            clean_err = re.sub(r'ERROR:\s*\[.*?\]\s*', '', err_msg)
            raise RuntimeError(clean_err.strip() or err_msg)

# Backwards compatibility alias
download_youtube_video = download_online_video

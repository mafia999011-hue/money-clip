import os
import io
import json
import uuid
import time
import zipfile
import threading
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, Response
from werkzeug.utils import secure_filename
from autoclip.pipeline import AutoClipPipeline
from autoclip.downloader import download_online_video
from autoclip.storage import HistoryStorage

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
app.config["OUTPUT_FOLDER"] = os.path.join(BASE_DIR, "output")
app.config["DATA_FOLDER"] = os.path.join(BASE_DIR, "data")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB max

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)

history_storage = HistoryStorage(os.path.join(app.config["DATA_FOLDER"], "history.json"))
CONFIG_FILE = os.path.join(app.config["DATA_FOLDER"], "config.json")

def load_saved_key() -> str:
    # 1. Environment variable
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY").strip()
    # 2. Config file
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "").strip()
        except Exception:
            pass
    return ""

def save_persistent_key(key: str):
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["api_key"] = key.strip()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

api_key_store = {"key": load_saved_key()}
tasks = {}
download_tasks = {}

@app.route("/")
def index():
    return render_template("index.html", has_key=bool(api_key_store["key"]))

@app.route("/history")
def history_page():
    return render_template("history.html")

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(history_storage.get_all_clips())

@app.route("/api/history/<filename>", methods=["DELETE"])
def delete_history_clip(filename):
    safe_name = os.path.basename(filename)
    success = history_storage.delete_clip(safe_name, output_dir=app.config["OUTPUT_FOLDER"])
    return jsonify({"status": "deleted" if success else "failed"})

@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        data = request.json or {}
        key = data.get("api_key", "").strip()
        if key.startswith("http://") or key.startswith("https://") or "youtu" in key:
            return jsonify({"status": "error", "error": "API key cannot be a URL", "has_key": False}), 400
        api_key_store["key"] = key
        save_persistent_key(key)
        return jsonify({
            "status": "ok",
            "has_key": bool(key),
            "masked_key": f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("✓ Set" if key else "")
        })
    
    current_key = api_key_store["key"]
    if current_key.startswith("http"):
        current_key = ""
        api_key_store["key"] = ""

    return jsonify({
        "has_key": bool(current_key),
        "masked_key": f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else ("✓ Set" if current_key else "")
    })

@app.route("/api/fetch_url", methods=["POST"])
@app.route("/api/youtube", methods=["POST"])
def fetch_online_video():
    data = request.json or {}
    url = data.get("url", "").strip()
    live_duration = int(data.get("live_duration", 180))
    if not url:
        return jsonify({"error": "No video link provided"}), 400

    task_id = f"dl_{uuid.uuid4().hex[:8]}"
    download_tasks[task_id] = {
        "status": "downloading",
        "progress": 10,
        "message": "Resolving video format & metadata...",
        "result": None,
        "error": None
    }

    def run_downloader():
        try:
            def update_dl_progress(msg, pct):
                download_tasks[task_id]["message"] = msg
                download_tasks[task_id]["progress"] = pct

            res = download_online_video(
                url,
                app.config["UPLOAD_FOLDER"],
                live_duration=live_duration,
                progress_callback=update_dl_progress
            )
            download_tasks[task_id]["status"] = "completed"
            download_tasks[task_id]["progress"] = 100
            download_tasks[task_id]["result"] = res
        except Exception as e:
            download_tasks[task_id]["status"] = "failed"
            download_tasks[task_id]["error"] = str(e)

    thread = threading.Thread(target=run_downloader)
    thread.daemon = True
    thread.start()

    return jsonify({
        "status": "downloading",
        "task_id": task_id
    })

@app.route("/api/download_status/<task_id>", methods=["GET"])
def download_status(task_id):
    task = download_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Download task not found"}), 404
    return jsonify(task)

@app.route("/api/live/check", methods=["POST"])
def check_live_stream():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No stream link provided"}), 400
    try:
        from autoclip.live_recorder import LiveStreamRecorder
        info = LiveStreamRecorder.inspect_url(url)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "is_live": False}), 500

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)

    return jsonify({
        "status": "uploaded",
        "video_id": unique_name,
        "filename": filename
    })

@app.route("/api/process", methods=["POST"])
def process():
    data = request.json or {}
    video_id = data.get("video_id")
    reframe_mode = data.get("reframe_mode", "blurred_background")
    aspect_ratio = data.get("aspect_ratio", "9:16")
    dub_language = data.get("dub_language", "none")
    subtitle_preset = data.get("subtitle_preset", "hormozi")
    enable_emojis = data.get("enable_emojis", True)
    length_pref = data.get("length_pref", "auto")
    clip_count = data.get("clip_count", "3")
    caption_language = data.get("caption_language", "auto")
    video_quality = data.get("video_quality", "1080p")
    show_hook_header = data.get("show_hook_header", True)
    enable_dynamic_zoom = data.get("enable_dynamic_zoom", True)
    enable_progress_bar = data.get("enable_progress_bar", True)
    enable_color_pop = data.get("enable_color_pop", True)
    enable_audio_boost = data.get("enable_audio_boost", True)

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    video_path = os.path.join(app.config["UPLOAD_FOLDER"], video_id)
    if not os.path.exists(video_path):
        return jsonify({"error": "Video file not found"}), 404

    task_id = uuid.uuid4().hex[:8]
    tasks[task_id] = {
        "status": "processing",
        "progress": 5,
        "message": "Initializing Money Clip AI pipeline...",
        "result": None,
        "error": None
    }

    def run_worker():
        try:
            def update_progress(msg, pct):
                tasks[task_id]["message"] = msg
                tasks[task_id]["progress"] = pct

            pipeline = AutoClipPipeline(
                api_key=api_key_store["key"],
                output_dir=app.config["OUTPUT_FOLDER"]
            )
            result = pipeline.process_video(
                video_path=video_path,
                reframe_mode=reframe_mode,
                aspect_ratio=aspect_ratio,
                dub_language=dub_language,
                subtitle_preset=subtitle_preset,
                enable_emojis=enable_emojis,
                length_pref=length_pref,
                clip_count=clip_count,
                caption_language=caption_language,
                video_quality=video_quality,
                show_hook_header=show_hook_header,
                enable_dynamic_zoom=enable_dynamic_zoom,
                enable_progress_bar=enable_progress_bar,
                enable_color_pop=enable_color_pop,
                enable_audio_boost=enable_audio_boost,
                progress_callback=update_progress
            )
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["result"] = result
        except Exception as e:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)

    thread = threading.Thread(target=run_worker)
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id, "status": "started"})

@app.route("/api/status/<task_id>")
def status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route("/stream/<filename>")
def stream_video(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(app.config["OUTPUT_FOLDER"], safe_name, mimetype="video/mp4")

@app.route("/download/<filename>")
def download_clip(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(app.config["OUTPUT_FOLDER"], safe_name, as_attachment=True)

@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Money Clip",
        "version": "2.0.0",
        "has_api_key": bool(api_key_store.get("key")),
        "uptime": time.time()
    })

@app.route("/api/cookies", methods=["GET", "POST", "DELETE"])
def manage_cookies():
    cookie_path = os.path.join(app.config["DATA_FOLDER"], "cookies.txt")
    if request.method == "GET":
        exists = os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 10
        size_kb = round(os.path.getsize(cookie_path) / 1024, 1) if exists else 0
        return jsonify({
            "has_cookies": exists,
            "filename": "cookies.txt" if exists else None,
            "size_kb": size_kb
        })
    elif request.method == "POST":
        if "cookies" not in request.files:
            return jsonify({"error": "No cookies file provided"}), 400
        f = request.files["cookies"]
        if not f.filename:
            return jsonify({"error": "Empty file"}), 400
        f.save(cookie_path)
        return jsonify({
            "status": "saved",
            "has_cookies": True,
            "size_kb": round(os.path.getsize(cookie_path) / 1024, 1)
        })
    elif request.method == "DELETE":
        if os.path.exists(cookie_path):
            try:
                os.remove(cookie_path)
            except Exception:
                pass
        return jsonify({"status": "deleted", "has_cookies": False})

@app.route("/api/clean_cache", methods=["POST"])
def clean_cache():
    freed_bytes = 0
    now = time.time()
    # Clean files older than 48 hours or temp snippet audio in uploads/
    cleaned_count = 0
    for folder in [app.config["UPLOAD_FOLDER"], app.config["OUTPUT_FOLDER"]]:
        if not os.path.exists(folder):
            continue
        for fn in os.listdir(folder):
            fp = os.path.join(folder, fn)
            # Remove temp snippets or files older than 48 hours
            is_snippet = fn.startswith("snippet_") or fn.startswith("test_") or fn.endswith(".wav")
            is_old = (now - os.path.getmtime(fp)) > (48 * 3600)
            if is_snippet or (is_old and not fn.endswith(".json")):
                try:
                    freed_bytes += os.path.getsize(fp)
                    os.remove(fp)
                    cleaned_count += 1
                except Exception:
                    pass
    return jsonify({
        "status": "cleaned",
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "files_removed": cleaned_count
    })

@app.route("/api/download_all/<task_id>")
def download_all_zip(task_id):
    task = tasks.get(task_id)
    if not task or not task.get("result"):
        return jsonify({"error": "Task not found or not completed"}), 404

    clips = task["result"].get("clips", [])
    if not clips:
        return jsonify({"error": "No clips found for this task"}), 404

    memory_zip = io.BytesIO()
    with zipfile.ZipFile(memory_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add each MP4 clip
        for c in clips:
            vf = c.get("video_file")
            if vf:
                vpath = os.path.join(app.config["OUTPUT_FOLDER"], vf)
                if os.path.exists(vpath):
                    zf.write(vpath, arcname=vf)

        # 2. Add complete Social Captions & Hook Strategy doc
        captions_txt = [
            "=" * 60,
            " MONEY CLIP — AI VIRAL HOOKS & SOCIAL POST CAPTIONS",
            "=" * 60,
            ""
        ]
        for c in clips:
            c_id = c.get("id", 1)
            title = c.get("title", f"Clip {c_id}")
            v_score = c.get("virality_score", 95)
            h_score = c.get("hook_score", 95)
            hook_banner = c.get("hook_headline", "")
            hook_text = c.get("hook", "")
            tip = c.get("viral_action_tip", "")
            copy_dict = c.get("social_copy", {})

            captions_txt.extend([
                f"--- [CLIP #{c_id}] {title} ---",
                f"Virality Score: {v_score}/100 | Hook Score: {h_score}/100",
                f"Hook Headline: {hook_banner}",
                f"First 3s Spoken Hook: \"{hook_text}\"",
                f"Viral Action Tip: {tip}",
                "",
                "📱 YOUTUBE SHORTS POST COPY:",
                copy_dict.get("youtube", ""),
                "",
                "⚡ TIKTOK POST COPY:",
                copy_dict.get("tiktok", ""),
                "",
                "📸 INSTAGRAM REELS POST COPY:",
                copy_dict.get("instagram", ""),
                "",
                "=" * 60,
                ""
            ])

        zf.writestr("social_captions.txt", "\n".join(captions_txt))

    memory_zip.seek(0)
    return send_file(
        memory_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"MoneyClip_{task_id}.zip"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

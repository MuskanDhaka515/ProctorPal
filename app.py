"""Flask backend: serves the UI and the speech, chat, and bookings APIs."""
import logging
import os
import threading
import time

from flask import Flask, jsonify, render_template, request

from db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("proctorpal")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB audio limit

_sessions: dict[str, list] = {}
_lock = threading.Lock()
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        from agent import ProctorPalAgent
        _agent = ProctorPalAgent()
    return _agent


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/transcribe")
def api_transcribe():
    audio = request.files.get("audio")
    if audio is None:
        return jsonify(error="No audio file received."), 400
    from stt import transcribe
    start = time.perf_counter()
    text = transcribe(audio.read())
    ms = round((time.perf_counter() - start) * 1000)
    log.info("transcribed in %sms: %r", ms, text)
    return jsonify(text=text, latency_ms=ms)


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    message = str(data.get("message", "")).strip()
    if not session_id or not message:
        return jsonify(error="session_id and message are required."), 400
    if not os.getenv("ANTHROPIC_API_KEY") and _agent is None:
        return jsonify(error="ANTHROPIC_API_KEY is not set on the server."), 500

    with _lock:
        history = list(_sessions.get(session_id, []))
    history.append({"role": "user", "content": message})

    start = time.perf_counter()
    reply, history, events = get_agent().respond(history)
    ms = round((time.perf_counter() - start) * 1000)
    log.info("session=%s tools=%s latency=%sms", session_id[:8],
             [e["tool"] for e in events], ms)

    with _lock:
        _sessions[session_id] = history[-40:]  # cap memory per session
    return jsonify(reply=reply, tool_calls=events, latency_ms=ms)


@app.post("/api/reset")
def api_reset():
    data = request.get_json(silent=True) or {}
    with _lock:
        _sessions.pop(str(data.get("session_id", "")), None)
    return jsonify(status="reset")


@app.get("/api/bookings")
def api_bookings():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, student_name, course, exam_date, start_time, status "
            "FROM bookings ORDER BY id DESC LIMIT 25"
        ).fetchall()
    return jsonify(bookings=[{**dict(r), "code": f"PP-{r['id']:04d}"} for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)

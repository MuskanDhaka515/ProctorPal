"""Speech-to-text with Whisper (faster-whisper, runs locally on CPU)."""
import os
import tempfile

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # imported lazily: heavy dependency
        _model = WhisperModel(os.getenv("WHISPER_MODEL", "base.en"),
                              device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes, suffix: str = ".webm") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        path = tmp.name
    try:
        segments, _ = _get_model().transcribe(path, language="en", vad_filter=True,
                                              beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.remove(path)

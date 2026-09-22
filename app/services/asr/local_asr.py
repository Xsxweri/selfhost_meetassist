from app.core.config import get_settings
from app.services.asr.base import BaseASR

settings = get_settings()


class LocalASR(BaseASR):
    """faster-whisper 本地转写，模型懒加载单例，避免重复载入"""

    _model = None

    def _ensure_model(self):
        if LocalASR._model is None:
            from faster_whisper import WhisperModel
            LocalASR._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
        return LocalASR._model

    def transcribe(self, samples, sample_rate: int = 16000) -> list[dict]:
        model = self._ensure_model()
        segments, _info = model.transcribe(
            samples, language=settings.ASR_LANGUAGE, vad_filter=True
        )
        return [
            {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
            for s in segments
            if s.text and s.text.strip()
        ]
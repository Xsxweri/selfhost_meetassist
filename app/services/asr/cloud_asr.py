from app.services.asr.base import BaseASR


class CloudASR(BaseASR):
    """云端 ASR 适配骨架：接入阿里/腾讯/讯飞时在此实现 HTTP/SDK 调用"""

    def transcribe(self, samples, sample_rate: int = 16000) -> list[dict]:
        raise NotImplementedError(
            "云端 ASR 未接入，请在 CloudASR.transcribe 中调用云厂商 SDK；"
            "本地/混合模式请将 ASR_BACKEND 设为 local"
        )
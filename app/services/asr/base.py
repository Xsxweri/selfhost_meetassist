from abc import ABC, abstractmethod

class BaseASR(ABC):
    """ASR 适配层统一接口，本地/云端实现均继承它"""
    @abstractmethod
    def transcribe(self, samples, sample_rate: int) -> list[dict]:
        """输入 float32 音频数组，返回 [{"start","end","text"}]（同步阻塞，调用方放线程池）"""
        raise NotImplementedError
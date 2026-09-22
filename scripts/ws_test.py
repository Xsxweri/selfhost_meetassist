import asyncio
import json
import sys
import wave

import websockets

async def main(url: str, wav_path: str):
    async with websockets.connect(url, ping_interval=20, ping_timeout=180) as ws:
        print("recv:", await ws.recv())  # ready
        with wave.open(wav_path, "rb") as wf:
            assert wf.getframerate() == 16000 and wf.getnchannels() == 1 and wf.getsampwidth() == 2, \
                "需 16kHz 单声道 16-bit PCM wav"
            while chunk := wf.readframes(1600):  # 每次 0.1s
                await ws.send(chunk)
                await asyncio.sleep(0.02)
        await ws.send(json.dumps({"type": "end"}))
        while True:
            msg = await ws.recv()
            print("recv:", msg)
            if json.loads(msg).get("type") == "end":
                break


if __name__ == "__main__":
    # 用法: python scripts/ws_test.py <token> <meeting_id> <audio.wav>
    token, mid, wav = sys.argv[1], sys.argv[2], sys.argv[3]
    asyncio.run(main(f"ws://127.0.0.1:8000/api/v1/meetings/{mid}/stream?token={token}", wav))
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../store/auth";
import type { StreamMsg, StreamSegment } from "../lib/types";

export type LiveStatus = "idle" | "connecting" | "recording" | "ended" | "error";

export function useLiveTranscription(meetingId: string) {
  const token = useAuth((s) => s.token);
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [segments, setSegments] = useState<StreamSegment[]>([]);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const nodeRef = useRef<AudioWorkletNode | null>(null);
  const rafRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    nodeRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close();
    wsRef.current = null; nodeRef.current = null; streamRef.current = null; ctxRef.current = null;
  }, []);

  const stop = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: "end" }));
    setStatus("ended");
    setLevel(0);
    cleanup();
  }, [cleanup]);

  const start = useCallback(async () => {
    setError(null); setSegments([]); setStatus("connecting");
    try {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${proto}//${location.host}/ws/meetings/${meetingId}/stream?token=${token}`);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      const mic = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = mic;

      const ctx = new AudioContext({ sampleRate: 16000 });
      ctxRef.current = ctx;
      await ctx.audioWorklet.addModule("/worklets/pcm-processor.js");

      ws.onopen = () => {
        const source = ctx.createMediaStreamSource(mic);
        const node = new AudioWorkletNode(ctx, "pcm-processor");
        nodeRef.current = node;
        node.port.onmessage = (e) => { if (ws.readyState === WebSocket.OPEN) ws.send(e.data); };
        source.connect(node);

        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
        const buf = new Uint8Array(analyser.frequencyBinCount);
        const tick = () => {
          analyser.getByteTimeDomainData(buf);
          let peak = 0;
          for (let i = 0; i < buf.length; i++) peak = Math.max(peak, Math.abs(buf[i] - 128) / 128);
          setLevel(peak);
          rafRef.current = requestAnimationFrame(tick);
        };
        tick();
      };

      ws.onmessage = (ev) => {
        const msg: StreamMsg = JSON.parse(ev.data);
        if (msg.type === "ready") setStatus("recording");
        else if (msg.type === "subtitle") setSegments((s) => [...s, ...msg.segments]);
        else if (msg.type === "end") { setStatus("ended"); cleanup(); }
        else if (msg.type === "warning") console.warn("[asr]", msg.detail);
        else if (msg.type === "error") { setError(msg.detail); setStatus("error"); }
      };
      ws.onerror = () => { setError("WebSocket 连接失败"); setStatus("error"); };
      ws.onclose = (e) => { if (e.code === 1008) { setError("连接被拒绝：录音授权或会议归属校验失败"); setStatus("error"); } };
    } catch (err: any) {
      setError(err?.message ?? "麦克风初始化失败");
      setStatus("error");
      cleanup();
    }
  }, [meetingId, token, cleanup]);

  useEffect(() => () => { cancelAnimationFrame(rafRef.current); cleanup(); }, [cleanup]);

  return { status, segments, level, error, start, stop };
}
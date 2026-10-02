import { motion } from "motion/react";

const BARS = 40;
export default function Waveform({ level, active }: { level: number; active: boolean }) {
  return (
    <div className="mt-5 flex h-16 items-center justify-center gap-[3px]">
      {Array.from({ length: BARS }).map((_, i) => {
        const h = active ? Math.max(3, Math.abs(Math.sin(i * 0.45 + level * 8)) * level * 58 + 3) : 3;
        return (
          <motion.div key={i} className="w-[3px] rounded-full bg-brand-500"
            animate={{ height: h, opacity: active ? 0.45 + level * 0.55 : 0.2 }}
            transition={{ type: "spring", stiffness: 320, damping: 22 }} />
        );
      })}
    </div>
  );
}
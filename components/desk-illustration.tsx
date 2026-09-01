import { Coffee, Monitor, StickyNote, TerminalSquare } from "lucide-react";

export function DeskIllustration() {
  return (
    <div className="paper-card relative min-h-[360px] overflow-hidden rounded-3xl bg-[#f5d8c8] p-5 md:min-h-[470px]">
      <div className="absolute inset-x-0 bottom-0 h-24 border-t-2 border-[#3b3340] bg-[#d7c6f1]" />
      <div className="absolute left-5 top-5 rotate-[-4deg] rounded-xl border-2 border-[#3b3340] bg-[#f7e8a6] p-4 shadow-[4px_4px_0_rgba(45,42,50,0.16)]">
        <StickyNote className="mb-2 size-6" aria-hidden="true" />
        <div className="text-xs font-black uppercase">closed candles</div>
        <div className="mt-2 h-2 w-28 rounded-full bg-[#3b3340]/20" />
        <div className="mt-2 h-2 w-20 rounded-full bg-[#3b3340]/20" />
      </div>

      <div className="absolute right-5 top-8 rotate-[5deg] rounded-full border-2 border-[#3b3340] bg-[#bfe8d0] p-5 shadow-[4px_4px_0_rgba(45,42,50,0.16)]">
        <Coffee className="size-8" aria-hidden="true" />
      </div>

      <div className="absolute left-1/2 top-24 w-[82%] -translate-x-1/2 rounded-3xl border-2 border-[#3b3340] bg-[#2d2a32] p-4 shadow-[8px_8px_0_rgba(45,42,50,0.2)]">
        <div className="flex gap-2">
          <span className="size-3 rounded-full bg-[#f5b9c6]" />
          <span className="size-3 rounded-full bg-[#f7e8a6]" />
          <span className="size-3 rounded-full bg-[#bfe8d0]" />
        </div>
        <div className="mt-5 grid gap-3 text-[#fff8ea]">
          <div className="flex items-center gap-2">
            <TerminalSquare className="size-5 text-[#bfe8d0]" aria-hidden="true" />
            <span className="font-mono text-sm">crypt docs: explain the system</span>
          </div>
          <div className="rounded-xl border border-[#fff8ea]/25 bg-[#fff8ea]/10 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-black text-[#f7e8a6]">
              <Monitor className="size-4" aria-hidden="true" />
              architecture map
            </div>
            <div className="grid grid-cols-3 gap-2">
              {["research", "backtest", "archive", "strategy", "risk", "runtime"].map((item) => (
                <div
                  key={item}
                  className="rounded-lg border border-[#fff8ea]/30 bg-[#fff8ea]/12 px-2 py-3 text-center text-[11px] font-bold"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
          <div className="h-3 w-4/5 rounded-full bg-[#b9d8f2]" />
          <div className="h-3 w-3/5 rounded-full bg-[#d7c6f1]" />
        </div>
      </div>

      <div className="absolute bottom-7 left-8 right-8 grid grid-cols-4 gap-3">
        {[18, 34, 25, 44].map((height, index) => (
          <div
            key={height}
            className="flex h-20 items-end rounded-xl border-2 border-[#3b3340] bg-[#fff8ea] p-2"
          >
            <div
              className={`w-full rounded-lg ${
                index % 2 === 0 ? "bg-[#b9d8f2]" : "bg-[#f5b9c6]"
              }`}
              style={{ height }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

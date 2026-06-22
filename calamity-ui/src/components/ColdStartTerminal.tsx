import React, { useState, useEffect, useRef } from "react";

interface ColdStartTerminalProps {
  isSimulating: boolean;
  synthesisStream: string;
}

const BOOT_MESSAGES = [
  "INITIATING NEURAL BOOT SEQUENCE...",
  "WAKING CLOUD TENSOR CORES...",
  "LOADING BASE QWEN3-8B KNOWLEDGE GRAPH...",
  "ALIGNING LORA ADAPTERS (CALAMITY-QWEN3-LORA-V1)...",
  "AWAITING DATA SYNTHESIS...",
];

export default function ColdStartTerminal({ isSimulating, synthesisStream }: ColdStartTerminalProps) {
  const [bootStage, setBootStage] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [synthesisStream]);

  // Cycle boot messages every 5 seconds while simulating but no stream has arrived
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSimulating && !synthesisStream) {
      interval = setInterval(() => {
        setBootStage((prev) => (prev + 1) % BOOT_MESSAGES.length);
      }, 5000);
    } else {
      setBootStage(0);
    }
    return () => clearInterval(interval);
  }, [isSimulating, synthesisStream]);

  if (!isSimulating && !synthesisStream) {
    return (
      <div className="h-full w-full rounded-md border border-zinc-800 bg-zinc-900/50 p-4 font-mono text-sm text-zinc-500 flex flex-col justify-end">
        <div className="animate-pulse">
          {">"} Awaiting simulation data for synthesis...<br />
          {">"} Request deeper tactical analysis...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-md border border-amber-900/40 bg-zinc-950 p-4 font-mono text-sm text-amber-500/80 overflow-y-auto relative custom-scrollbar flex flex-col">
      <div className="sticky top-0 bg-zinc-950/90 pb-2 mb-2 border-b border-amber-900/40 flex items-center justify-between z-10">
        <span className="text-amber-500 font-bold uppercase tracking-widest text-xs">
          [ TACTICAL SYNTHESIS ]
        </span>
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-amber-500 animate-ping opacity-75"></div>
          <div className="w-2 h-2 rounded-full bg-amber-500"></div>
        </div>
      </div>

      <div className="flex-grow whitespace-pre-wrap">
        {synthesisStream ? (
          <span>{synthesisStream}</span>
        ) : (
          <div className="flex flex-col gap-4 mt-4">
            {/* SVG Pulsing Brain / Network */}
            <div className="flex justify-center my-4 opacity-50">
              <svg width="60" height="60" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" className="animate-pulse">
                <circle cx="50" cy="50" r="40" stroke="#f59e0b" strokeWidth="2" fill="none" strokeDasharray="5,5"/>
                <circle cx="50" cy="50" r="20" stroke="#f59e0b" strokeWidth="1" fill="none" />
                <path d="M50 10 L50 30 M50 70 L50 90 M10 50 L30 50 M70 50 L90 50" stroke="#f59e0b" strokeWidth="2" />
                <circle cx="50" cy="50" r="5" fill="#f59e0b" className="animate-ping" />
              </svg>
            </div>
            
            <div className="text-center text-xs tracking-widest opacity-80 animate-pulse">
              [ {BOOT_MESSAGES[bootStage]} ]
            </div>
            <div className="text-center text-xs opacity-50">
              L40S GPU Waking from Cold Sleep (Estimated T-Minus 20s)
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from "react";

interface ColdStartTerminalProps {
  formData: any;
  results: any;
}

const BOOT_MESSAGES = [
  "INITIATING NEURAL BOOT SEQUENCE...",
  "WAKING CLOUD TENSOR CORES...",
  "LOADING BASE QWEN3-8B KNOWLEDGE GRAPH...",
  "ALIGNING LORA ADAPTERS (CALAMITY-QWEN3-LORA-V1)...",
  "AWAITING DATA SYNTHESIS...",
];

export default function ColdStartTerminal({ formData, results }: ColdStartTerminalProps) {
  const [streamData, setStreamData] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const [bootStage, setBootStage] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamData]);

  // Cycle boot messages while waiting for stream
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSimulating && !streamData) {
      interval = setInterval(() => {
        setBootStage((prev) => (prev + 1) % BOOT_MESSAGES.length);
      }, 5000);
    } else {
      setBootStage(0);
    }
    return () => clearInterval(interval);
  }, [isSimulating, streamData]);

  // Fetch the SSE Stream when simulation results are available
  useEffect(() => {
    if (!results || !formData) return;

    let isMounted = true;
    setIsSimulating(true);
    setStreamData(""); // Reset terminal on new simulation

    const fetchStream = async () => {
      try {
        const apiUrl = process.env.NODE_ENV === "production" 
          ? "https://api.calamityai.tech/api/v1/ask_ai" 
          : "https://api.calamityai.tech/api/v1/ask_ai"; // Usually http://localhost:8000/api/v1/ask_ai for dev

        const response = await fetch(apiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query_text: formData.query_text || "",
            historical_context: results.historical_context || [],
            simulation_parameters: {
              country: formData.country,
              disaster_type: formData.disaster_type,
              month: formData.month,
              event_year: formData.event_year,
              severity: formData.severity,
            },
            math_predictions: results.predictions || {},
            stream: true,
          })
        });

        if (!response.body) throw new Error("No readable stream available");

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          if (!isMounted) break;

          buffer += decoder.decode(value, { stream: true });
          
          // Process chunks line by line
          const lines = buffer.split('\n');
          buffer = lines.pop() || ""; // Keep the last incomplete line in the buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '[DONE]') {
                break;
              }
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.text) {
                  setStreamData(prev => prev + parsed.text);
                }
              } catch (e) {
                // Ignore incomplete JSON chunks (sometimes sent by proxies)
                console.warn("Skipping unparseable SSE chunk", dataStr);
              }
            }
          }
        }
      } catch (err) {
        console.error("Stream connection failed:", err);
        if (isMounted) {
          setStreamData(prev => prev + "\n\n[!] CONNECTION TO NEURAL ORCHESTRATOR LOST.");
        }
      } finally {
        if (isMounted) setIsSimulating(false);
      }
    };

    fetchStream();

    return () => {
      isMounted = false; // Cleanup on dismount
    };
  }, [results]); // Only re-run when we get new ML predictions from the backend

  // Helper to cleanly render DeepSeek / Qwen reasoning tags progressively
  const formatStream = (text: string) => {
    if (!text.includes("<think>")) return <span>{text}</span>;

    const parts = text.split(/<think>|<\/think>/g);
    return parts.map((part, index) => {
      // Even indexes are actual output, odd indexes are inside <think>
      if (index % 2 === 1) {
        return (
          <div key={index} className="text-zinc-500 italic border-l-2 border-zinc-700 pl-3 my-3 text-xs bg-zinc-900/30 p-2 rounded-r flex flex-col">
            <span className="text-zinc-600 text-[10px] uppercase font-bold tracking-widest mb-1 select-none">AI Reasoning</span>
            {part}
          </div>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  if (!results) {
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
    <div className="h-full w-full rounded-md border border-amber-900/40 bg-zinc-950 p-4 font-mono text-sm text-amber-500/80 overflow-y-auto relative custom-scrollbar flex flex-col break-words">
      <div className="sticky top-0 bg-zinc-950/90 pb-2 mb-2 border-b border-amber-900/40 flex items-center justify-between z-10">
        <span className="text-amber-500 font-bold uppercase tracking-widest text-xs shadow-amber-500 drop-shadow-md">
          [ TACTICAL SYNTHESIS ]
        </span>
        <div className="flex gap-1.5">
          {isSimulating ? (
            <>
              <div className="w-2 h-2 rounded-full bg-amber-500 animate-ping opacity-75"></div>
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
            </>
          ) : (
            <div className="w-2 h-2 rounded-full bg-zinc-600"></div>
          )}
        </div>
      </div>

      <div className="flex-grow whitespace-pre-wrap">
        {streamData ? (
          <div className="leading-relaxed">{formatStream(streamData)}</div>
        ) : (
          <div className="flex flex-col gap-4 mt-4 h-full justify-center pb-8">
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
              GPU Waking from Cold Sleep (Estimated T-Minus 20s)
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

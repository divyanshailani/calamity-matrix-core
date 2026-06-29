import React, { useState, useEffect, useRef } from "react";
import { ArrowLeft, Send, Sparkles, Clock } from "lucide-react";

interface CalamityAiChatProps {
  formData: any;
  results: any;
  onClose: () => void;
}

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  isStreaming?: boolean;
}

export default function CalamityAiChat({ formData, results, onClose }: CalamityAiChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const [timeLeft, setTimeLeft] = useState(300); // 5 minutes in seconds
  const endRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Sleep counter
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const fetchStream = async (queryText: string, isInitial: boolean = false) => {
    if (!results || !formData) return;

    const userMsgId = Date.now().toString();
    const aiMsgId = (Date.now() + 1).toString();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: queryText },
      { id: aiMsgId, role: "ai", content: "", isStreaming: true },
    ]);

    setIsSimulating(true);
    setInput("");
    setTimeLeft(300); // Reset timer on new request

    try {
      const endpoint = isInitial ? "/api/v1/ask_ai" : "/api/v1/chat";
      const apiUrl = process.env.NODE_ENV === "production" 
        ? `https://api.calamityai.tech${endpoint}`
        : `https://api.calamityai.tech${endpoint}`;

      const payloadBody = isInitial ? {
          query_text: queryText || formData.query_text || "",
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
      } : {
          query_text: queryText,
          stream: true,
      };

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      if (!response.body) throw new Error("No readable stream");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') {
              break;
            }
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.text) {
                setMessages((prev) => 
                  prev.map(msg => 
                    msg.id === aiMsgId 
                      ? { ...msg, content: msg.content + parsed.text } 
                      : msg
                  )
                );
              }
            } catch (e) {
              console.warn("Skipping unparseable chunk");
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Stream failed:", err);
      setMessages((prev) => 
        prev.map(msg => 
          msg.id === aiMsgId 
            ? { ...msg, content: msg.content + `\n\n[Error: ${err.message}]` } 
            : msg
        )
      );
    } finally {
      setIsSimulating(false);
      setTimeLeft(300); // Reset timer after finish
      setMessages((prev) => 
        prev.map(msg => 
          msg.id === aiMsgId 
            ? { ...msg, isStreaming: false } 
            : msg
        )
      );
    }
  };

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isSimulating) return;
    fetchStream(input.trim());
  };

  // Helper to cleanly render reasoning tags progressively
  const formatStream = (text: string) => {
    if (!text.includes("<think>")) return <span className="whitespace-pre-wrap">{text}</span>;

    const parts = text.split(/<think>|<\/think>/g);
    return parts.map((part, index) => {
      // Even indexes are actual output, odd indexes are inside <think>
      if (index % 2 === 1) {
        return (
          <div key={index} className="text-zinc-500 italic border-l-2 border-zinc-800 pl-3 my-3 text-[13px] bg-zinc-900/30 p-2 rounded-r flex flex-col">
            <span className="text-zinc-400 text-[10px] font-semibold tracking-wide mb-1 select-none flex items-center gap-1">
              <Sparkles size={10} /> Thought Process
            </span>
            {part}
          </div>
        );
      }
      return <span key={index} className="whitespace-pre-wrap">{part}</span>;
    });
  };

  // Kick off an initial synthesis when the component mounts if it's empty
  useEffect(() => {
    if (messages.length === 0) {
      fetchStream("Provide a tactical synthesis based on the historical context.", true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col h-full w-full bg-[#09090b] text-zinc-100 overflow-hidden border border-zinc-800 rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-[#09090b]/90 z-10 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={16} />
          </button>
          <span className="font-semibold text-sm flex items-center gap-1.5">
            <Sparkles size={14} className="text-zinc-400" /> Calamity AI
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {timeLeft === 0 ? (
            <span className="text-[10px] text-zinc-500 flex items-center gap-1 bg-zinc-900 px-2 py-1 rounded-full border border-zinc-800">
              <Clock size={10} /> Endpoint Idle
            </span>
          ) : (
            <span className={`text-[10px] flex items-center gap-1 px-2 py-1 rounded-full border ${timeLeft < 60 ? 'text-amber-500 border-amber-900/50 bg-amber-900/10' : 'text-zinc-400 border-zinc-800 bg-zinc-900'}`}>
              <Clock size={10} /> AI sleeping in {formatTime(timeLeft)}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 text-[13px] custom-scrollbar">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col max-w-[95%] ${msg.role === "user" ? "self-end items-end" : "self-start items-start"}`}>
            <span className="text-[10px] text-zinc-500 mb-1 ml-1">{msg.role === "user" ? "You" : "Calamity AI"}</span>
            <div className={`p-3 rounded-xl ${msg.role === "user" ? "bg-zinc-800 text-white rounded-tr-sm" : "bg-transparent text-zinc-200"}`}>
              {msg.role === "user" ? msg.content : formatStream(msg.content)}
              
              {msg.isStreaming && !msg.content && (
                <div className="flex items-center gap-1 h-5">
                  <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                  <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                  <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-3 bg-[#09090b] border-t border-zinc-800 shrink-0">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a follow-up question..."
            disabled={isSimulating}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-full py-2.5 pl-4 pr-10 text-[13px] text-white focus:outline-none focus:border-zinc-600 disabled:opacity-50 transition-colors"
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isSimulating}
            className="absolute right-2 p-1.5 bg-white text-black rounded-full disabled:bg-zinc-800 disabled:text-zinc-500 transition-colors"
          >
            <Send size={12} />
          </button>
        </form>
      </div>
    </div>
  );
}

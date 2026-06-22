import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Database, Search, Clock } from "lucide-react";

interface HistoricalContextProps {
  results: any;
}

export default function HistoricalContext({ results }: HistoricalContextProps) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex flex-col h-full relative overflow-hidden">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-zinc-400" />
          <h2 className="text-xs font-semibold tracking-widest uppercase text-zinc-400">
            Historical Context
          </h2>
        </div>
      </div>

      <div className="flex-grow space-y-4 overflow-y-auto max-h-[calc(100vh-250px)] pr-2">
        <p className="text-xs text-zinc-400 italic leading-relaxed mb-4">
          Displaying closest historical analogy from vector memory...
        </p>

        <AnimatePresence mode="wait">
          {!results ? (
            <motion.div 
              key="empty"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="h-full min-h-[250px] flex flex-col items-center justify-center p-6 text-center text-zinc-400 gap-3 border border-dashed border-zinc-800 rounded-lg bg-zinc-950"
            >
              <Search className="w-5 h-5 opacity-50" />
              <p className="text-xs">No simulation active</p>
            </motion.div>
          ) : (
            <motion.div 
              key="results"
              initial="hidden" animate="show"
              variants={{
                hidden: { opacity: 0 },
                show: {
                  opacity: 1,
                  transition: { staggerChildren: 0.1 }
                }
              }}
              className="space-y-4"
            >
              {results.historical_context.length === 0 ? (
                <div className="text-xs p-4 text-zinc-400 bg-zinc-950 border border-zinc-800 rounded-lg text-center">
                  No recorded analogues found.
                </div>
              ) : (
                results.historical_context.map((ctx: any, idx: number) => (
                  <motion.div 
                    key={idx}
                    variants={{
                      hidden: { opacity: 0, y: 10 },
                      show: { opacity: 1, y: 0 }
                    }}
                    className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 shadow-sm hover:shadow transition-all duration-300"
                  >
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-3">
                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-semibold text-zinc-100 uppercase">
                          {String(ctx.country).startsWith("http") ? "ReliefWeb" : String(ctx.country)}
                        </span>
                        <span className="text-[10px] font-medium text-zinc-400 uppercase">
                          {String(ctx.disaster_type).match(/^\d+$/) ? `ID:${ctx.disaster_type}` : String(ctx.disaster_type)}
                        </span>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <div className="flex items-center gap-1 text-zinc-400 text-[10px] font-medium">
                          <Clock className="w-3 h-3" />
                          {ctx.event_year || "HIST"}
                        </div>
                        <span className="text-zinc-400 bg-zinc-950 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium">
                          {(ctx.similarity_score * 100).toFixed(0)}% Match
                        </span>
                      </div>
                    </div>
                    
                    <p className="text-xs text-zinc-400 leading-relaxed">
                      {ctx.text_preview || ctx.narrative_preview}
                    </p>
                  </motion.div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface TelemetryProps {
  telemetry: {
    math_engine: {
      affected_population: {
        val_rmse: number;
        val_mae: number;
        feature_importances: Record<string, number>;
      };
      economic_damage: {
        val_rmse: number;
        val_mae: number;
        feature_importances: Record<string, number>;
      };
    };
    rag_engine: {
      average_cosine_similarity: number;
    };
  } | null;
}

export default function TelemetryHUD({ telemetry }: TelemetryProps) {
  if (!telemetry) return null;

  // Format Feature Importances for Recharts (using Affected Population model)
  const rawFeatures = telemetry.math_engine?.affected_population?.feature_importances || {};
  const chartData = Object.keys(rawFeatures)
    .map((key) => ({
      name: key,
      value: Number(rawFeatures[key].toFixed(4)),
    }))
    .sort((a, b) => b.value - a.value); // Sort descending by importance

  const rmse = telemetry.math_engine?.affected_population?.val_rmse?.toLocaleString() || "N/A";
  
  // RAG Similarity Logic
  const sim = telemetry.rag_engine?.average_cosine_similarity || 0;
  const simPercentage = Math.round(sim * 100);
  
  let simColorClass = "bg-blue-500";
  let simTextColorClass = "text-blue-400";
  if (sim > 0.8) {
    simColorClass = "bg-emerald-500";
    simTextColorClass = "text-emerald-400";
  } else if (sim < 0.6) {
    simColorClass = "bg-rose-500";
    simTextColorClass = "text-rose-400";
  }

  return (
    <div className="w-full bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-2xl relative overflow-hidden group">
      {/* Decorative scanline */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent group-hover:via-cyan-400/40 transition-all duration-1000"></div>
      
      <div className="flex items-center gap-2 mb-6">
        <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
        </svg>
        <h2 className="text-lg font-bold text-zinc-200 tracking-wide">SYSTEM DIAGNOSTICS</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Math Engine Column */}
        <div className="flex flex-col">
          <h3 className="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-4">Math Engine Predictors</h3>
          
          <div className="flex items-end gap-2 mb-4">
            <span className="text-3xl font-light text-zinc-100">{rmse}</span>
            <span className="text-xs text-zinc-500 mb-1">RMSE (Affected)</span>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 0, left: 20, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 11 }} width={80} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                  itemStyle={{ color: '#e4e4e7' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#0ea5e9' : '#3f3f46'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RAG Engine Column */}
        <div className="flex flex-col border-t md:border-t-0 md:border-l border-zinc-800 md:pl-8 pt-6 md:pt-0">
          <h3 className="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-4">RAG Semantic Confidence</h3>
          
          <div className="flex-grow flex flex-col justify-center">
            <div className="flex justify-between items-end mb-2">
              <span className={`text-4xl font-bold ${simTextColorClass}`}>{simPercentage}%</span>
              <span className="text-sm text-zinc-500 mb-1">Avg Cosine Similarity</span>
            </div>
            
            {/* Custom glowing progress bar */}
            <div className="h-4 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-800 relative">
              <div 
                className={`h-full ${simColorClass} transition-all duration-1000 ease-out`}
                style={{ width: `${simPercentage}%`, boxShadow: `0 0 15px currentColor` }}
              />
            </div>
            
            <p className="text-xs text-zinc-500 mt-6 leading-relaxed font-mono">
              {sim > 0.8 ? "Historical matrix alignment optimal. Analogies are highly relevant." :
               sim > 0.6 ? "Moderate semantic alignment. Proceed with situational awareness." :
               "Low contextual confidence. The system is operating on generalized physics without strong historical precedents."}
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

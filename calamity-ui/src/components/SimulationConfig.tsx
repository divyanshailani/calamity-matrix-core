import React from "react";
import { Cpu } from "lucide-react";
import { getSeverityLabel, countries, disasters, months, defaultContexts } from "../lib/constants";

interface SimulationConfigProps {
  formData: any;
  setFormData: (data: any) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  consoleLogs: string[];
  addLog: (msg: string) => void;
}

export default function SimulationConfig({
  formData,
  setFormData,
  handleSubmit,
  isLoading,
  consoleLogs,
  addLog
}: SimulationConfigProps) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex flex-col h-full">
      <div className="flex items-center gap-2 mb-6 pb-3 border-b border-zinc-800">
        <Cpu className="w-4 h-4 text-zinc-400" />
        <h2 className="text-xs font-semibold tracking-widest uppercase text-zinc-400">
          Simulation Config
        </h2>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-5 flex-grow flex flex-col justify-between">
        <div className="space-y-4">
          
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase block">Country</label>
            <select 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-zinc-100 focus:border-zinc-800 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
              value={formData.country}
              onChange={(e) => {
                setFormData({...formData, country: e.target.value});
                addLog(`Country changed to ${e.target.value}`);
              }}
            >
              {countries.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase block">Disaster Type</label>
            <select 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-zinc-100 focus:border-zinc-800 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
              value={formData.disaster_type}
              onChange={(e) => {
                const newType = e.target.value;
                setFormData({...formData, disaster_type: newType, query_text: defaultContexts[newType]});
                addLog(`Disaster changed to ${newType}`);
              }}
            >
              {disasters.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase block">Month</label>
              <select 
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-zinc-100 focus:border-zinc-800 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                value={formData.month}
                onChange={(e) => setFormData({...formData, month: Number(e.target.value)})}
              >
                {months.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase block">Year</label>
              <input 
                type="text"
                maxLength={4}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm font-mono text-zinc-100 focus:border-zinc-800 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                value={formData.event_year}
                onChange={(e) => {
                  let val = e.target.value.replace(/[^0-9]/g, '');
                  if (val.length === 4 && parseInt(val) > 2026) val = "2026";
                  setFormData({...formData, event_year: val});
                }}
              />
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <div className="flex justify-between items-center text-[11px]">
              <label className="font-semibold tracking-wider text-zinc-400 uppercase">
                {getSeverityLabel(formData.disaster_type)}
              </label>
              <span className="font-mono font-medium text-zinc-100 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
                {formData.severity}
              </span>
            </div>
            <input 
              type="range"
              min="1" max="10" step="0.1"
              className="w-full accent-blue-500 cursor-pointer"
              value={formData.severity}
              onChange={(e) => setFormData({...formData, severity: Number(e.target.value)})}
            />
          </div>

          <div className="space-y-1.5 pt-2">
            <label className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase block">Contextual Details</label>
            <textarea 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-3 text-sm text-zinc-100 focus:border-zinc-800 focus:ring-1 focus:ring-blue-500 outline-none h-24 resize-none transition-all"
              value={formData.query_text}
              onChange={(e) => setFormData({...formData, query_text: e.target.value})}
              placeholder="Describe specific scenario metrics..."
            />
          </div>
        </div>

        {/* Execute Button */}
        <div className="pt-4 mt-auto">
          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-600/90 text-white font-medium py-3 px-4 rounded-lg text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer shadow-sm"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                Run Simulation
              </>
            )}
          </button>
        </div>
      </form>
      
      {/* Diagnostics console */}
      <div className="mt-5 pt-4 border-t border-zinc-800">
        <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800/60 max-h-[80px] overflow-y-auto space-y-1 text-[11px] font-mono text-zinc-400">
          {consoleLogs.map((log, idx) => (
            <p key={idx} className={log.includes("failed") ? "text-red-500" : "text-zinc-400"}>
              {log}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

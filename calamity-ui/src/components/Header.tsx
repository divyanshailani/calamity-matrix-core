import React from "react";
import { Activity } from "lucide-react";

export default function Header() {
  return (
    <header className="bg-zinc-900 border-b border-zinc-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
      <div className="flex items-center gap-3">
        <Activity className="w-5 h-5 text-zinc-100" />
        <h1 className="text-sm font-semibold tracking-wide text-zinc-100">
          Calamity AI
        </h1>
      </div>
      <div className="text-xs font-medium text-zinc-400 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        System Online
      </div>
    </header>
  );
}

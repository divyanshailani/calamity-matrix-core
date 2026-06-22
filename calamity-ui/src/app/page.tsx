"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import Header from "../components/Header";
import SimulationConfig from "../components/SimulationConfig";
import GeospatialMap from "../components/GeospatialMap";
import HistoricalContext from "../components/HistoricalContext";
import { countryCoords } from "../lib/constants";

export default function Dashboard() {
  const [isMounted, setIsMounted] = useState(false);
  const [formData, setFormData] = useState({
    country: "USA",
    disaster_type: "Earthquake",
    month: 1,
    event_year: "2026",
    severity: 5.0,
    query_text: "A massive earthquake striking a populated urban area.",
  });

  const [viewState, setViewState] = useState({
    latitude: 37.0902,
    longitude: -95.7129,
    zoom: 3
  });

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([
    "System Initialized.",
    "Ready for simulation."
  ]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const addLog = (msg: string) => {
    setConsoleLogs(prev => [...prev.slice(-3), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResults(null);
    addLog(`Simulating ${formData.disaster_type} in ${formData.country}...`);

    const coords = countryCoords[formData.country];
    if (coords) {
      setViewState({
        latitude: coords.lat,
        longitude: coords.lng,
        zoom: coords.zoom
      });
    }

    try {
      const response = await axios.post("http://localhost:8000/api/v1/simulate_calamity", {
        query_text: formData.query_text,
        country: formData.country,
        disaster_type: formData.disaster_type,
        month: Number(formData.month),
        event_year: Number(formData.event_year),
        severity: Number(formData.severity),
      });
      setResults(response.data);
      addLog("Simulation completed successfully.");
      
      // Auto-zoom in when results load to focus on the 3 tactical points
      if (coords) {
        setViewState({
          latitude: coords.lat,
          longitude: coords.lng,
          zoom: coords.zoom + 2.5
        });
      }
    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail || err.message || "Connection offline.";
      setError(errMsg);
      addLog(`Execution failed: ${errMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-zinc-950 overflow-x-hidden flex flex-col relative">
      {/* Animated Tactical Background */}
      <div className="fixed inset-0 z-0 bg-[linear-gradient(to_right,rgba(39,39,42,0.4)_1px,transparent_1px),linear-gradient(to_bottom,rgba(39,39,42,0.4)_1px,transparent_1px)] bg-[size:40px_40px] animate-bg-pan opacity-60 pointer-events-none" />

      <Header />

      {/* THREE-COLUMN LAYOUT */}
      <main className="p-6 mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 flex-grow w-full max-w-[1600px] relative z-10">
        
        {/* COLUMN 1: CONFIGURATION (Span 3) */}
        <div className="lg:col-span-3 flex flex-col">
          <SimulationConfig 
            formData={formData}
            setFormData={setFormData}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
            consoleLogs={consoleLogs}
            addLog={addLog}
          />
        </div>

        {/* COLUMN 2: CENTER STAGE / MAP CANVAS (Span 6) */}
        <div className="lg:col-span-6 flex flex-col min-h-[500px]">
          {isMounted && (
            <GeospatialMap 
              viewState={viewState}
              setViewState={setViewState}
              results={results}
              error={error}
              country={formData.country}
            />
          )}
        </div>

        {/* COLUMN 3: THE ORACLE / LLM BRIEFING (Span 3) */}
        <div className="lg:col-span-3 flex flex-col">
          <HistoricalContext results={results} />
        </div>

      </main>
    </div>
  );
}

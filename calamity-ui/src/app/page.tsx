"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import Header from "../components/Header";
import SimulationConfig from "../components/SimulationConfig";
import GeospatialMap from "../components/GeospatialMap";
import HistoricalContext from "../components/HistoricalContext";
import TelemetryHUD from "../components/TelemetryHUD";
import ColdStartTerminal from "../components/ColdStartTerminal";
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
  
  const [synthesisStream, setSynthesisStream] = useState("");

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const addLog = (msg: string) => {
    setConsoleLogs(prev => [...prev.slice(-3), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const runSimulation = async (dataToSubmit: typeof formData) => {
    setIsLoading(true);
    setError(null);
    setResults(null);
    setSynthesisStream("");
    addLog(`Simulating ${dataToSubmit.disaster_type} in ${dataToSubmit.country}...`);

    const coords = countryCoords[dataToSubmit.country];
    if (coords) {
      setViewState({
        latitude: coords.lat,
        longitude: coords.lng,
        zoom: coords.zoom
      });
    }

    try {
      // Phase 1: ML and RAG
      const response = await axios.post("http://localhost:8000/api/v1/simulate_calamity", {
        query_text: dataToSubmit.query_text,
        country: dataToSubmit.country,
        disaster_type: dataToSubmit.disaster_type,
        month: Number(dataToSubmit.month),
        event_year: Number(dataToSubmit.event_year),
        severity: Number(dataToSubmit.severity),
      });
      setResults(response.data);
      addLog("ML Predictors & RAG Engine executed successfully. Triggering LLM Synthesis...");
      
      if (coords) {
        setViewState({
          latitude: coords.lat,
          longitude: coords.lng,
          zoom: coords.zoom + 2.5
        });
      }
      
      // Phase 2: SSE Stream for Calamity AI LLM Synthesis
      try {
        const synthResponse = await fetch("http://localhost:8000/api/v1/synthesize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...dataToSubmit,
            affected_population: response.data.predictions.estimated_affected_population,
            economic_impact: response.data.predictions.estimated_damage_usd_thousands,
            rag_context: response.data.historical_context
          })
        });

        if (!synthResponse.body) throw new Error("No readable stream");

        const reader = synthResponse.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;

        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          if (value) {
            const chunkValue = decoder.decode(value);
            const lines = chunkValue.split("\n");
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const dataStr = line.slice(6);
                if (dataStr === "[DONE]") {
                  addLog("Tactical Synthesis complete.");
                  done = true;
                  break;
                }
                const unescaped = dataStr.replace(/\\n/g, '\n');
                setSynthesisStream(prev => prev + unescaped);
              }
            }
          }
        }
      } catch (err: any) {
        console.error("Stream error", err);
        addLog(`Synthesis stream failed: ${err.message}`);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await runSimulation(formData);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-zinc-950 overflow-x-hidden flex flex-col relative">
      <div className="fixed inset-0 z-0 bg-[linear-gradient(to_right,rgba(39,39,42,0.4)_1px,transparent_1px),linear-gradient(to_bottom,rgba(39,39,42,0.4)_1px,transparent_1px)] bg-[size:40px_40px] animate-bg-pan opacity-60 pointer-events-none" />

      <Header />

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
        <div className="lg:col-span-3 flex flex-col gap-6">
          {/* Top Half: RAG Vector Memory */}
          <div className="flex-1 max-h-[50%] overflow-hidden flex flex-col">
            <HistoricalContext 
              results={results} 
              country={formData.country}
              onSuggestionClick={(updates) => {
                const newFormData = { ...formData, ...updates };
                setFormData(newFormData);
                runSimulation(newFormData);
              }}
            />
          </div>
          
          {/* Bottom Half: Cold Start Terminal / LLM */}
          <div className="flex-1 max-h-[50%] min-h-[300px]">
             <ColdStartTerminal 
               isSimulating={isLoading || (results !== null && synthesisStream === "")} 
               synthesisStream={synthesisStream} 
             />
          </div>
        </div>

        {/* BOTTOM ROW: TELEMETRY HUD (Span 12) */}
        <div className="lg:col-span-12 mt-2">
          {results?.telemetry && (
            <TelemetryHUD telemetry={results.telemetry} />
          )}
        </div>

      </main>
    </div>
  );
}

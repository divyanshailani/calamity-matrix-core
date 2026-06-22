import React from "react";
import Map, { NavigationControl, Marker } from "react-map-gl/maplibre";
import { MapPin, AlertTriangle } from "lucide-react";
import { countryCoords } from "../lib/constants";
import "maplibre-gl/dist/maplibre-gl.css";

interface GeospatialMapProps {
  viewState: any;
  setViewState: (state: any) => void;
  results: any;
  error: string | null;
  country: string;
}

const formatNumber = (num: number) => {
  return new Intl.NumberFormat('en-US').format(Math.round(num));
};

export default function GeospatialMap({
  viewState,
  setViewState,
  results,
  error,
  country
}: GeospatialMapProps) {
  return (
    <div className="flex-grow w-full border border-zinc-800 rounded-xl overflow-hidden bg-zinc-900 relative shadow-sm flex flex-col justify-end">
      
      {/* Outer Header Indicator */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2 text-xs font-medium text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-3 py-1.5 rounded-full shadow-sm backdrop-blur-md">
        <MapPin className="w-3.5 h-3.5" />
        Geospatial View
      </div>

      <Map
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        mapStyle="/vibrant-map.json"
        style={{ width: "100%", height: "100%", filter: "brightness(0.75) contrast(1.15) saturate(0.95)" }}
      >
        <NavigationControl position="top-right" />
        {results?.historical_context?.map((ctx: any, idx: number) => {
          const baseCoords = countryCoords[country] || { lat: 0, lng: 0, zoom: 3 };
          // Generate deterministic pseudo-random offset within a realistic radius (~3 degrees)
          const latOffset = Math.sin(idx * 12.9898 + ctx.similarity_score * 78.233) * 3.5;
          const lngOffset = Math.cos(idx * 4.1414 + ctx.similarity_score * 43.232) * 3.5;
          
          return (
            <Marker 
              key={`marker-${idx}`} 
              longitude={baseCoords.lng + lngOffset} 
              latitude={baseCoords.lat + latOffset} 
              anchor="center"
            >
              <div className="relative flex h-5 w-5 group">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500/70 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-5 w-5 bg-blue-500 border-2 border-white shadow-md flex items-center justify-center text-[8px] text-white font-bold">
                  {idx + 1}
                </span>
                
                {/* Tooltip on hover */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-32 bg-blue-600 text-white text-[10px] p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  <p className="font-semibold text-blue-400">{(ctx.similarity_score * 100).toFixed(1)}% Match</p>
                  <p className="truncate opacity-80">{String(ctx.country).startsWith("http") ? "ReliefWeb Event" : String(ctx.country)}</p>
                  <p className="opacity-80">Year: {ctx.event_year || "HIST"}</p>
                </div>
              </div>
            </Marker>
          );
        })}
      </Map>

      {/* INTEGRATED HUD FOOTER BAR: XGBOOST MATH ENGINE RESULTS */}
      <div className="absolute bottom-4 left-4 right-4 z-10 flex gap-4">
        
        {/* ESTIMATED AFFECTED POPULATION */}
        <div className="flex-1 bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-xl p-4 shadow-sm flex flex-col justify-center relative overflow-hidden group">
          <div className="w-1 h-full absolute left-0 top-0 bg-blue-500 rounded-l-xl opacity-80" />
          <p className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5">
            Affected Population
          </p>
          <p className="text-xl font-mono font-medium text-zinc-100">
            {results ? formatNumber(results.predictions.estimated_affected_population) : "—"}
          </p>
        </div>

        {/* ESTIMATED ECONOMIC DAMAGE */}
        <div className="flex-1 bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-xl p-4 shadow-sm flex flex-col justify-center relative overflow-hidden group">
          <div className="w-1 h-full absolute left-0 top-0 bg-blue-500 rounded-l-xl opacity-80" />
          <p className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5">
            Economic Impact
          </p>
          <p className="text-xl font-mono font-medium text-zinc-100">
            {results ? (
              <>
                <span className="text-zinc-400 mr-1">$</span>
                {formatNumber(results.predictions.estimated_damage_usd_thousands)}K
              </>
            ) : (
              "—"
            )}
          </p>
        </div>

      </div>

      {/* Error alerts floating over map */}
      {error && (
        <div className="absolute top-16 left-4 right-4 z-10 bg-red-50 border border-red-200 p-3 rounded-lg flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-red-800 font-semibold text-sm">Simulation Error</p>
            <p className="text-xs text-red-600 mt-0.5">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}

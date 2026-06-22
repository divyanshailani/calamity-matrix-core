import React, { useRef, useEffect, useMemo } from "react";
import Map, { NavigationControl, Marker, Source, Layer } from "react-map-gl/maplibre";
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

// Generate curved line coordinates
const generateArc = (start: {lat: number, lng: number}, end: {lat: number, lng: number}) => {
  const points = [];
  const segments = 50;
  
  const dx = end.lng - start.lng;
  const dy = end.lat - start.lat;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const curveFactor = dist * 0.2; // 20% of distance is curve height

  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const lat = start.lat + dy * t;
    const lng = start.lng + dx * t;
    
    // Perpendicular curve offset
    const perpX = -dy / dist;
    const perpY = dx / dist;
    
    // Parabolic curve height
    const curve = Math.sin(t * Math.PI) * curveFactor;
    
    points.push([lng + perpX * curve, lat + perpY * curve]);
  }
  return points;
};


export default function GeospatialMap({
  viewState,
  setViewState,
  results,
  error,
  country
}: GeospatialMapProps) {
  const mapRef = useRef<any>(null);

  // Auto zoom to fit target country and all markers
  useEffect(() => {
    if (results?.historical_context && results.historical_context.length > 0 && mapRef.current) {
      const target = countryCoords[country];
      const points = results.historical_context
        .filter((ctx: any) => ctx.lat != null && ctx.lng != null)
        .map((ctx: any) => ({ lat: ctx.lat, lng: ctx.lng }));
        
      if (target) {
        points.push(target);
      }
      
      if (points.length > 0) {
        const lats = points.map((p: any) => p.lat);
        const lngs = points.map((p: any) => p.lng);
        
        const minLng = Math.min(...lngs);
        const maxLng = Math.max(...lngs);
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        
        mapRef.current.fitBounds(
          [[minLng - 2, minLat - 2], [maxLng + 2, maxLat + 2]],
          { padding: 60, duration: 2500 }
        );
      }
    } else if (results && countryCoords[country] && mapRef.current) {
      const target = countryCoords[country];
      mapRef.current.flyTo({
        center: [target.lng, target.lat],
        zoom: target.zoom,
        duration: 2500
      });
    }
  }, [results, country]);

  // Generate GeoJSON for arcs
  const arcData = useMemo(() => {
    if (!results?.historical_context || !countryCoords[country]) return null;
    const target = countryCoords[country];
    
    const features = results.historical_context
      .filter((ctx: any) => ctx.lat != null && ctx.lng != null)
      .map((ctx: any, idx: number) => {
        // Apply identical radial jitter so the arc perfectly hits the jittered marker
        const angle = idx * ((Math.PI * 2) / 3);
        const radius = idx === 0 ? 0 : 0.8;
        const jitterLat = ctx.lat + (Math.sin(angle) * radius);
        const jitterLng = ctx.lng + (Math.cos(angle) * radius);
        
        const coords = generateArc(
          { lat: jitterLat, lng: jitterLng }, 
          { lat: target.lat, lng: target.lng }
        );
        return {
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: coords
          }
        };
      });
      
    return {
      type: "FeatureCollection" as const,
      features: features as any
    };
  }, [results, country]);
  return (
    <div className="flex-grow w-full border border-zinc-800 rounded-xl overflow-hidden bg-zinc-900 relative shadow-sm flex flex-col justify-end">
      
      {/* Outer Header Indicator */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2 text-xs font-medium text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-3 py-1.5 rounded-full shadow-sm backdrop-blur-md">
        <MapPin className="w-3.5 h-3.5" />
        Geospatial View
      </div>

      <Map
        ref={mapRef}
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        mapStyle="/vibrant-map.json"
        style={{ width: "100%", height: "100%", filter: "brightness(0.75) contrast(1.15) saturate(0.95)" }}
      >
        <NavigationControl position="top-right" />
        
        {/* Render Arcs */}
        {arcData && (
          <Source id="arcs" type="geojson" data={arcData}>
            <Layer
              id="arc-layer"
              type="line"
              paint={{
                "line-color": "#34d399", // emerald-400
                "line-width": 2,
                "line-opacity": 0.5,
                "line-dasharray": [3, 3]
              }}
            />
          </Source>
        )}

        {/* Target Country Marker — only shown when no historical matches found */}
        {countryCoords[country] && results && results.historical_context?.length === 0 && (
          <Marker 
            longitude={countryCoords[country].lng} 
            latitude={countryCoords[country].lat} 
            anchor="center"
          >
            <div className="relative flex h-12 w-12 items-center justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500/40"></span>
              <span className="absolute inline-flex h-8 w-8 rounded-full bg-red-500/30"></span>
              <span className="relative inline-flex rounded-full h-4 w-4 bg-red-600 border-[2.5px] border-zinc-900 shadow-[0_0_15px_rgba(220,38,38,0.7)]"></span>
            </div>
          </Marker>
        )}
        {results?.historical_context?.map((ctx: any, idx: number) => {
          if (ctx.lat == null || ctx.lng == null) return null;
          
          // Add a slight radial jitter so markers at the exact same coordinates don't perfectly overlap
          const angle = idx * ((Math.PI * 2) / 3); // Spread 120 degrees apart
          const radius = idx === 0 ? 0 : 0.8; // First marker centered, others offset by ~80km
          const jitterLat = ctx.lat + (Math.sin(angle) * radius);
          const jitterLng = ctx.lng + (Math.cos(angle) * radius);
          
          return (
            <Marker 
              key={`marker-${idx}`} 
              longitude={jitterLng} 
              latitude={jitterLat} 
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

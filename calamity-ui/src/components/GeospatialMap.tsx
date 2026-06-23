import React, { useRef, useEffect, useMemo, useState } from "react";
import Map, { NavigationControl, Marker, Source, Layer } from "react-map-gl/maplibre";
import { AlertTriangle } from "lucide-react";
import { countryCoords } from "../lib/constants";
import "maplibre-gl/dist/maplibre-gl.css";

interface GeospatialMapProps {
  viewState: any;
  setViewState: (s: any) => void;
  results: any;
  error: string | null;
  country: string;
}

const fmt = (n: number) => new Intl.NumberFormat("en-US").format(Math.round(n));
const fmtEcon = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}B`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}M`;
  return `$${fmt(n)}K`;
};

const generateArc = (s: { lat: number; lng: number }, e: { lat: number; lng: number }) => {
  const pts = [], segs = 50, dx = e.lng - s.lng, dy = e.lat - s.lat, dist = Math.sqrt(dx * dx + dy * dy), cf = dist * 0.2;
  for (let i = 0; i <= segs; i++) {
    const t = i / segs, curve = Math.sin(t * Math.PI) * cf;
    pts.push([s.lng + dx * t + (-dy / dist) * curve, s.lat + dy * t + (dx / dist) * curve]);
  }
  return pts;
};

export default function GeospatialMap({ viewState, setViewState, results, error, country }: GeospatialMapProps) {
  const mapRef = useRef<any>(null);
  const [hudIn, setHudIn] = useState(false);

  useEffect(() => {
    if (results) { setHudIn(false); const t = setTimeout(() => setHudIn(true), 500); return () => clearTimeout(t); }
    setHudIn(false);
  }, [results]);

  useEffect(() => {
    if (!mapRef.current) return;
    if (results?.historical_context?.length > 0) {
      const target = countryCoords[country];
      const pts = results.historical_context.filter((c: any) => c.lat != null).map((c: any) => ({ lat: c.lat, lng: c.lng }));
      if (target) pts.push(target);
      if (pts.length > 0) {
        const lats = pts.map((p: any) => p.lat), lngs = pts.map((p: any) => p.lng);
        mapRef.current.fitBounds([[Math.min(...lngs) - 2, Math.min(...lats) - 2], [Math.max(...lngs) + 2, Math.max(...lats) + 2]], { padding: 60, duration: 2000 });
      }
    } else if (results && countryCoords[country]) {
      const t = countryCoords[country];
      mapRef.current.flyTo({ center: [t.lng, t.lat], zoom: t.zoom, duration: 2000 });
    }
  }, [results, country]);

  const arcData = useMemo(() => {
    if (!results?.historical_context || !countryCoords[country]) return null;
    const target = countryCoords[country];
    return {
      type: "FeatureCollection" as const,
      features: results.historical_context.filter((c: any) => c.lat != null).map((c: any, i: number) => {
        const a = i * (Math.PI * 2 / 3), r = i === 0 ? 0 : 0.8;
        return { type: "Feature", geometry: { type: "LineString", coordinates: generateArc({ lat: c.lat + Math.sin(a) * r, lng: c.lng + Math.cos(a) * r }, target) } };
      }) as any
    };
  }, [results, country]);

  return (
    <div style={{ flex: 1, position: "relative", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden", minHeight: "400px", background: "var(--surface)" }}>

      {/* Top-left label */}
      <div style={{
        position: "absolute", top: "12px", left: "12px", zIndex: 20,
        display: "flex", alignItems: "center", gap: "6px",
        fontSize: "11px", fontWeight: 500, color: "var(--text-2)",
        background: "rgba(10,10,10,0.8)", backdropFilter: "blur(8px)",
        border: "1px solid var(--border)", borderRadius: "9999px", padding: "5px 12px",
      }}>
        <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
        Geospatial View
      </div>

      <Map ref={mapRef} {...viewState} onMove={e => setViewState(e.viewState)} mapStyle="/vibrant-map.json"
        style={{ width: "100%", height: "100%", filter: "brightness(0.75) contrast(1.1) saturate(0.9)" }}>
        <NavigationControl position="top-right" />

        {/* Target marker (no-match) */}
        {countryCoords[country] && results?.historical_context?.length === 0 && (
          <Marker longitude={countryCoords[country].lng} latitude={countryCoords[country].lat} anchor="center">
            <div style={{ position: "relative", width: "12px", height: "12px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ position: "absolute", width: "100%", height: "100%", borderRadius: "50%", background: "var(--red)", opacity: 0.35, animation: "ping 1.5s ease infinite" }} />
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--red)", border: "1.5px solid var(--bg)", display: "block" }} />
            </div>
          </Marker>
        )}

        {/* Historical markers */}
        {results?.historical_context?.map((ctx: any, i: number) => {
          if (ctx.lat == null || ctx.lng == null) return null;
          const a = i * (Math.PI * 2 / 3), r = i === 0 ? 0 : 0.8;
          return (
            <Marker key={i} longitude={ctx.lng + Math.cos(a) * r} latitude={ctx.lat + Math.sin(a) * r} anchor="center">
              <div style={{ position: "relative" }} className="group">
                <div style={{ width: "20px", height: "20px", borderRadius: "50%", background: "var(--accent)", border: "2px solid var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "8px", fontWeight: 700, color: "white", cursor: "pointer" }}>
                  {i + 1}
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity" style={{
                  position: "absolute", bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)", width: "140px", zIndex: 50,
                  background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "6px", padding: "8px 10px", pointerEvents: "none",
                }}>
                  <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-1)", marginBottom: "2px" }}>{(ctx.similarity_score * 100).toFixed(1)}% match</p>
                  <p style={{ fontSize: "10px", color: "var(--text-2)" }}>{String(ctx.country).startsWith("http") ? "ReliefWeb" : String(ctx.country)}</p>
                  <p style={{ fontSize: "10px", color: "var(--text-3)" }}>Year: {ctx.event_year || "—"}</p>
                </div>
              </div>
            </Marker>
          );
        })}
      </Map>

      {/* Floating predictions HUD */}
      {hudIn && results && (
        <div className="animate-fade-up" style={{ position: "absolute", bottom: "16px", left: "16px", right: "16px", zIndex: 20, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <div style={{ background: "rgba(10,10,10,0.88)", backdropFilter: "blur(10px)", border: "1px solid var(--border)", borderRadius: "8px", padding: "14px 16px" }}>
            <p style={{ fontSize: "10px", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>Est. Affected</p>
            <p style={{ fontSize: "18px", fontWeight: 600, fontFamily: "var(--font-geist-mono)", color: "var(--text-1)", letterSpacing: "-0.02em" }}>
              {fmt(results.predictions.estimated_affected_population)}
            </p>
          </div>
          <div style={{ background: "rgba(10,10,10,0.88)", backdropFilter: "blur(10px)", border: "1px solid var(--border)", borderRadius: "8px", padding: "14px 16px" }}>
            <p style={{ fontSize: "10px", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>Economic Impact</p>
            <p style={{ fontSize: "18px", fontWeight: 600, fontFamily: "var(--font-geist-mono)", color: "var(--text-1)", letterSpacing: "-0.02em" }}>
              {fmtEcon(results.predictions.estimated_damage_usd_thousands)}
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ position: "absolute", top: "52px", left: "12px", right: "12px", zIndex: 30, display: "flex", alignItems: "flex-start", gap: "8px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "6px", padding: "10px 12px", backdropFilter: "blur(8px)" }}>
          <AlertTriangle size={14} style={{ color: "var(--red)", flexShrink: 0, marginTop: "1px" }} />
          <div>
            <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--red)" }}>Simulation Error</p>
            <p style={{ fontSize: "11px", color: "var(--text-2)", marginTop: "2px" }}>{error}</p>
          </div>
        </div>
      )}

      <style>{`
        @keyframes ping { 0%,100%{transform:scale(1);opacity:0.35} 50%{transform:scale(2.2);opacity:0} }
      `}</style>
    </div>
  );
}

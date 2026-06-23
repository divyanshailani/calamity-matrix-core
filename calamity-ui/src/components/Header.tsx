import React from "react";
import Link from "next/link";

export default function Header() {
  return (
    <header style={{
      height: "52px",
      borderBottom: "1px solid var(--border)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      position: "sticky",
      top: 0,
      zIndex: 50,
      background: "rgba(10,10,10,0.9)",
      backdropFilter: "blur(12px)",
      flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-1)", letterSpacing: "-0.01em" }}>
            Calamity AI
          </span>
        </Link>
        <span style={{ fontSize: "11px", color: "var(--text-2)", borderLeft: "1px solid var(--border-hover)", paddingLeft: "16px" }}>
          Simulator
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <span style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "11px", color: "var(--text-2)" }}>
          <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
          API Online
        </span>
        <a href="https://github.com/divyanshailani/calamity-matrix-core" target="_blank" rel="noopener noreferrer"
          style={{ fontSize: "12px", color: "var(--text-2)", textDecoration: "none" }}>
          GitHub ↗
        </a>
      </div>
    </header>
  );
}

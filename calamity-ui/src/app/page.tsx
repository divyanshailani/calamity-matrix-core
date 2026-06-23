"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";

// ─── Background Effects ───────────────────────────────────────
function BackgroundEffect() {
  const [mousePos, setMousePos] = useState({ x: -1000, y: -1000 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => setMousePos({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
      {/* Subtle faint grid pattern */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: "radial-gradient(var(--border) 1px, transparent 1px)",
        backgroundSize: "32px 32px",
        opacity: 0.4,
        maskImage: "linear-gradient(to bottom, black 30%, transparent 100%)",
        WebkitMaskImage: "linear-gradient(to bottom, black 30%, transparent 100%)",
      }} />
      {/* Smooth glowing pointer */}
      <motion.div
        animate={{ x: mousePos.x, y: mousePos.y }}
        transition={{ type: "spring", stiffness: 60, damping: 25, mass: 0.5 }}
        style={{
          position: "absolute",
          top: -400, left: -400,
          width: 800, height: 800,
          background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 60%)",
        }}
      />
    </div>
  );
}

// ─── Animations ───────────────────────────────────────────────
const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariant = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
};

// ─── Stat item ────────────────────────────────────────────────
function Stat({ value, label }: { value: string; label: string }) {
  return (
    <motion.div variants={itemVariant} whileHover={{ y: -3 }} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <span style={{ fontSize: "22px", fontWeight: 600, color: "var(--text-1)", letterSpacing: "-0.02em" }}>
        {value}
      </span>
      <span style={{ fontSize: "12px", color: "var(--text-2)" }}>{label}</span>
    </motion.div>
  );
}

// ─── Step card ────────────────────────────────────────────────
function Step({ n, title, desc }: { n: string; title: string; desc: string }) {
  return (
    <motion.div 
      variants={itemVariant}
      whileHover={{ y: -4, borderColor: "var(--border-hover)", backgroundColor: "var(--surface-raised)" }}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "24px",
        transition: "background-color 0.3s ease, border-color 0.3s ease"
      }}>
      <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.08em", marginBottom: "12px" }}>
        {n}
      </p>
      <p style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-1)", marginBottom: "8px" }}>
        {title}
      </p>
      <p style={{ fontSize: "13px", lineHeight: "1.65", color: "var(--text-2)" }}>
        {desc}
      </p>
    </motion.div>
  );
}

// ─── Tech badge ───────────────────────────────────────────────
function TechBadge({ name }: { name: string }) {
  return (
    <motion.span 
      variants={itemVariant}
      whileHover={{ scale: 1.05, backgroundColor: "var(--surface-raised)", color: "var(--text-1)", borderColor: "var(--border-hover)" }}
      style={{
        fontSize: "12px",
        color: "var(--text-2)",
        border: "1px solid var(--border)",
        borderRadius: "6px",
        padding: "5px 10px",
        background: "var(--surface)",
        cursor: "default",
        transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease"
      }}>
      {name}
    </motion.span>
  );
}

// ─── Main ─────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
      <BackgroundEffect />

      {/* NAV */}
      <nav style={{
        borderBottom: "1px solid var(--border)",
        padding: "0 32px",
        height: "56px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "rgba(10,10,10,0.85)",
        backdropFilter: "blur(16px)",
      }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <motion.span whileHover={{ opacity: 0.8 }} style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-1)", letterSpacing: "-0.01em" }}>
            Calamity AI
          </motion.span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <motion.a
            whileHover={{ color: "var(--text-1)" }}
            href="https://github.com/divyanshailani/calamity-matrix-core"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "13px", color: "var(--text-2)", textDecoration: "none", transition: "color 0.2s ease" }}
          >
            GitHub ↗
          </motion.a>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/dashboard"
              id="nav-launch-btn"
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: "white",
                background: "var(--accent)",
                borderRadius: "6px",
                padding: "6px 14px",
                textDecoration: "none",
                display: "inline-block"
              }}
            >
              Launch Simulator →
            </Link>
          </motion.div>
        </div>
      </nav>

      <motion.div variants={staggerContainer} initial="hidden" animate="visible" style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative", zIndex: 1 }}>
        
        {/* HERO */}
        <section style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "120px 24px 100px",
          textAlign: "center",
          maxWidth: "680px",
          margin: "0 auto",
          width: "100%",
        }}>
          {/* Label pill */}
          <motion.div variants={itemVariant} style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "11px",
            fontWeight: 500,
            color: "var(--text-2)",
            border: "1px solid var(--border)",
            borderRadius: "9999px",
            padding: "4px 12px",
            marginBottom: "32px",
            background: "var(--surface)",
            letterSpacing: "0.05em",
          }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
            V1 Beta · Early Access
          </motion.div>

          <motion.h1 variants={itemVariant} style={{
            fontSize: "clamp(36px, 6vw, 58px)",
            fontWeight: 700,
            lineHeight: 1.1,
            letterSpacing: "-0.03em",
            color: "var(--text-1)",
            marginBottom: "20px",
          }}>
            A Neuro-Symbolic Disaster
            <br />Intelligence Engine.
          </motion.h1>

          <motion.p variants={itemVariant} style={{
            fontSize: "16px",
            lineHeight: "1.7",
            color: "var(--text-2)",
            maxWidth: "520px",
            marginBottom: "40px",
          }}>
            Combines XGBoost impact regression with pgvector semantic search over
            2,281 historical disaster reports to simulate affected population and
            economic damage for any hazard event, anywhere in the world.
          </motion.p>

          <motion.div variants={itemVariant} style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link
                href="/dashboard"
                id="hero-launch-btn"
                style={{
                  fontSize: "14px",
                  fontWeight: 500,
                  color: "white",
                  background: "var(--accent)",
                  borderRadius: "8px",
                  padding: "10px 22px",
                  textDecoration: "none",
                  display: "inline-block"
                }}
              >
                Launch Simulator →
              </Link>
            </motion.div>
            <motion.a
              whileHover={{ scale: 1.03, backgroundColor: "var(--surface-raised)", color: "var(--text-1)" }}
              whileTap={{ scale: 0.97 }}
              href="https://github.com/divyanshailani/calamity-matrix-core"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: "14px",
                fontWeight: 500,
                color: "var(--text-2)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "10px 22px",
                textDecoration: "none",
                background: "var(--surface)",
                display: "inline-block",
                transition: "background-color 0.2s ease, color 0.2s ease"
              }}
            >
              View on GitHub
            </motion.a>
          </motion.div>
        </section>

        {/* DIVIDER */}
        <motion.div variants={itemVariant} style={{ borderTop: "1px solid var(--border)", maxWidth: "960px", margin: "0 auto", width: "100%" }} />

        {/* STATS */}
        <motion.section variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }} style={{ padding: "64px 24px", maxWidth: "960px", margin: "0 auto", width: "100%" }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: "40px",
          }}>
            <Stat value="25 Years" label="of global disaster data (2000–2025)" />
            <Stat value="2,281" label="situation report narratives in vector DB" />
            <Stat value="1,024" label="embedding dimensions (BGE-Large)" />
            <Stat value="5+" label="hazard classes with domain-specific models" />
            <Stat value="4-source" label="fusion: USGS · NASA · EM-DAT · Smithsonian" />
          </div>
        </motion.section>

        {/* DIVIDER */}
        <motion.div variants={itemVariant} style={{ borderTop: "1px solid var(--border)", maxWidth: "960px", margin: "0 auto", width: "100%" }} />

        {/* HOW IT WORKS */}
        <motion.section variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }} style={{ padding: "80px 24px", maxWidth: "960px", margin: "0 auto", width: "100%" }}>
          <motion.h2 variants={itemVariant} style={{
            fontSize: "13px",
            fontWeight: 600,
            color: "var(--text-3)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "32px",
          }}>
            How it works
          </motion.h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
            <Step
              n="01"
              title="Configure the Event"
              desc="Select a country, hazard class (earthquake, flood, etc.), month, year, and severity on the Richter or Saffir–Simpson scale."
            />
            <Step
              n="02"
              title="Run the Math Engine"
              desc="XGBoost regression models — trained separately for each disaster type — predict estimated affected population and economic impact in USD."
            />
            <Step
              n="03"
              title="Retrieve Historical Context"
              desc="pgvector performs a cosine similarity search over 2,281 embedded disaster narratives to surface the 3 most analogous historical events by meaning."
            />
          </div>
        </motion.section>

        {/* DIVIDER */}
        <motion.div variants={itemVariant} style={{ borderTop: "1px solid var(--border)", maxWidth: "960px", margin: "0 auto", width: "100%" }} />

        {/* TECH STACK */}
        <motion.section variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }} style={{ padding: "64px 24px", maxWidth: "960px", margin: "0 auto", width: "100%" }}>
          <motion.h2 variants={itemVariant} style={{
            fontSize: "13px",
            fontWeight: 600,
            color: "var(--text-3)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "20px",
          }}>
            Built with
          </motion.h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {["Python 3.11", "XGBoost", "PostgreSQL", "pgvector", "FastAPI",
              "sentence-transformers", "BGE-Large-en-v1.5", "Next.js 16", "MapLibre GL", "Framer Motion"].map(t => (
              <TechBadge key={t} name={t} />
            ))}
          </div>
        </motion.section>

        {/* FOOTER */}
        <motion.footer variants={itemVariant} style={{
          borderTop: "1px solid var(--border)",
          padding: "32px 32px 48px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          maxWidth: "960px",
          margin: "0 auto",
          width: "100%",
        }}>
          <span style={{ fontSize: "12px", color: "var(--text-3)" }}>
            Built by Divyansh Ailani
          </span>
          <motion.a
            whileHover={{ color: "var(--text-1)" }}
            href="https://github.com/divyanshailani/calamity-matrix-core"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "12px", color: "var(--text-3)", textDecoration: "none", transition: "color 0.2s ease" }}
          >
            GitHub ↗
          </motion.a>
        </motion.footer>

      </motion.div>
    </div>
  );
}

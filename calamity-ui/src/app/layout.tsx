import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Calamity AI — Disaster Intelligence Engine",
  description:
    "A neuro-symbolic disaster intelligence engine combining XGBoost impact regression with pgvector semantic RAG over 25 years of global disaster data.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`}>
      <body style={{ background: "var(--bg)", color: "var(--text-1)", minHeight: "100vh" }}>
        {children}
      </body>
    </html>
  );
}

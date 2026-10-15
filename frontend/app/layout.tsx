import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DOXERA | Cognitive OCR & Logistics Sales Intelligence",
  description: "Next-generation VisionOS Liquid Glass operational dashboard and cognitive document extraction engine.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen text-slate-900 antialiased selection:bg-blue-600 selection:text-white">
        {/* Dynamic Ambient Fluid Mesh Canvas (Optical Substrate for Refraction Lenses) */}
        <div className="liquid-ambient-canvas" aria-hidden="true">
          <div className="liquid-orb-cyan animate-fluid-orb-slow" />
          <div className="liquid-orb-indigo animate-fluid-orb-reverse" />
          <div className="liquid-orb-amber animate-fluid-orb-slow" />
        </div>

        {/* Application Viewport */}
        <div className="relative z-10 flex min-h-screen flex-col">
          {children}
        </div>
      </body>
    </html>
  );
}

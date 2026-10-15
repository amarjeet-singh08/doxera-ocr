"use client";

import React, { useEffect, useRef, useState } from "react";

interface LiquidLensProps {
  children: React.ReactNode;
  className?: string;
  refraction?: number;
  bevel?: number;
  aberration?: number;
  interaction?: "fluid" | "none";
  interactionStrength?: number;
  interactionRadius?: number;
  zIndex?: number;
  snapshotSelector?: string;
}

export const LiquidLens: React.FC<LiquidLensProps> = ({
  children,
  className = "",
  refraction = 0.12,
  bevel = 18,
  aberration = 0.16,
  interaction = "fluid",
  interactionStrength = 0.25,
  interactionRadius = 140,
  zIndex = 10,
  snapshotSelector = ".liquid-ambient-canvas",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [specularPos, setSpecularPos] = useState({ x: 50, y: 0 });
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    let lensInstance: any = null;
    let isMounted = true;

    const initLiquid = async () => {
      if (typeof window === "undefined" || !containerRef.current) return;

      try {
        const liquidModule = await import("liquid-gl");
        const liquidGL = liquidModule.default || liquidModule;

        if (typeof liquidGL === "function" && isMounted && containerRef.current) {
          lensInstance = liquidGL({
            target: containerRef.current,
            snapshot: snapshotSelector,
            engine: "auto",
            refraction: refraction,
            bevel: bevel,
            aberration: aberration,
            interaction: interaction,
            interactionStrength: interactionStrength,
            interactionRadius: interactionRadius,
            zIndex: zIndex,
            shadow: false,
            tilt: true,
          });
        }
      } catch (err) {
        // Fallback to high-spec CSS backdrop-filter pipeline
        console.warn("liquidGL WebGPU/WebGL acceleration fallback engaged:", err);
        if (isMounted) setIsSupported(false);
      }
    };

    initLiquid();

    return () => {
      isMounted = false;
      if (lensInstance && typeof lensInstance.destroy === "function") {
        try {
          lensInstance.destroy();
        } catch (e) {
          // Cleanup error suppression
        }
      }
    };
  }, [refraction, bevel, aberration, interaction, interactionStrength, interactionRadius, zIndex, snapshotSelector]);

  // Dynamic specular light reflection shifting with cursor
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setSpecularPos({ x, y });
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className={`liquid-glass-substrate relative overflow-hidden group ${className}`}
      style={{
        zIndex: zIndex,
      }}
    >
      {/* Specular fluid light sheen tracking cursor */}
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-300 opacity-60 group-hover:opacity-100"
        style={{
          background: `radial-gradient(circle 240px at ${specularPos.x}% ${specularPos.y}%, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.08) 50%, transparent 80%)`,
        }}
        aria-hidden="true"
      />

      {/* Content isolated above refraction layer */}
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  );
};

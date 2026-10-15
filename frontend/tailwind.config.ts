import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        glass: {
          surface: "var(--glass-surface)",
          "surface-elevated": "var(--glass-surface-elevated)",
          border: "var(--glass-border)",
          "border-active": "var(--glass-border-active)",
          specular: "var(--glass-specular-color)",
        },
        doxera: {
          blue: "#1D4ED8",
          sky: "#0284C7",
          amber: "#D97706",
          emerald: "#059669",
          rose: "#E11D48",
          ink: "#0F172A",
          muted: "#64748B",
        },
      },
      borderRadius: {
        squircle: "22px",
        "squircle-sm": "14px",
        "squircle-lg": "30px",
        "squircle-pill": "9999px",
      },
      boxShadow: {
        "liquid-ambient": "0 24px 60px -12px rgba(15, 23, 42, 0.08), 0 8px 24px -4px rgba(15, 23, 42, 0.04)",
        "liquid-elevated": "0 32px 80px -16px rgba(15, 23, 42, 0.14), 0 12px 32px -4px rgba(15, 23, 42, 0.06)",
        "liquid-modal": "0 40px 100px -20px rgba(15, 23, 42, 0.28), 0 16px 40px -8px rgba(15, 23, 42, 0.12)",
        "specular-dual": "inset 0 1.5px 1px 0 rgba(255, 255, 255, 0.95), inset 0 -1.5px 1.5px 0 rgba(15, 23, 42, 0.03)",
        "specular-glow": "0 0 20px rgba(59, 130, 246, 0.25), inset 0 1.5px 1px 0 rgba(255, 255, 255, 1)",
      },
      backdropBlur: {
        xs: "2px",
        liquid: "32px",
        vision: "44px",
      },
      animation: {
        "fluid-orb-slow": "orbDrift 28s ease-in-out infinite alternate",
        "fluid-orb-reverse": "orbDriftReverse 32s ease-in-out infinite alternate",
        "pulse-subtle": "pulseSubtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        orbDrift: {
          "0%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(60px, -40px) scale(1.1)" },
          "100%": { transform: "translate(-30px, 50px) scale(0.95)" },
        },
        orbDriftReverse: {
          "0%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(-50px, 40px) scale(0.92)" },
          "100%": { transform: "translate(40px, -60px) scale(1.08)" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.65" },
        },
      },
      transitionTimingFunction: {
        "apple-spring": "cubic-bezier(0.16, 1, 0.3, 1)",
        "jelly-spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [],
};

export default config;

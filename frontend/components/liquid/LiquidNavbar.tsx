"use client";

import React, { useState } from "react";
import { Search, LayoutDashboard, Files, Inbox, BarChart3, Download, Menu, X, ShieldCheck } from "lucide-react";
import { NotificationCenter } from "./NotificationCenter";
import { motion, AnimatePresence } from "framer-motion";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: "dockets", label: "All Dockets", icon: <Files className="w-4 h-4" /> },
  { id: "review", label: "Review Center", icon: <Inbox className="w-4 h-4" /> },
  { id: "sales", label: "Sales Intelligence", icon: <BarChart3 className="w-4 h-4" /> },
  { id: "exports", label: "Exports", icon: <Download className="w-4 h-4" /> },
];

interface LiquidNavbarProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export const LiquidNavbar: React.FC<LiquidNavbarProps> = ({ activeTab, onTabChange }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full px-4 sm:px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 px-4 sm:px-6 py-2.5 rounded-2xl bg-white/75 backdrop-blur-vision border border-white/90 shadow-liquid-ambient">
        {/* Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white font-extrabold shadow-md shadow-blue-600/30 ring-1 ring-white/80">
            D
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight text-slate-900 block leading-none">
              DOXERA
            </span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5 block">
              Cognitive OCR
            </span>
          </div>
        </div>

        {/* Desktop Navigation Links with Spring Active Indicator */}
        <nav className="hidden lg:flex items-center gap-1.5 p-1 bg-slate-100/70 rounded-xl border border-slate-200/60">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`relative px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 select-none ${
                  isActive ? "text-blue-700" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavPill"
                    className="absolute inset-0 bg-white rounded-lg shadow-sm border border-blue-200/80"
                    transition={{ type: "spring", stiffness: 480, damping: 32 }}
                  />
                )}
                <span className="relative z-10 shrink-0">{item.icon}</span>
                <span className="relative z-10">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Tools: Search, Notification Center, Account */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Search Input */}
          <div className="relative hidden md:block w-48 lg:w-60">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search docket, customer..."
              className="w-full h-9 pl-9 pr-3 text-xs bg-white/80 border border-slate-200/90 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-900 placeholder:text-slate-400"
            />
          </div>

          {/* Isolated Control Center Notifications */}
          <NotificationCenter />

          {/* User Badge */}
          <div className="hidden sm:flex items-center gap-2.5 pl-2 border-l border-slate-200/80">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-slate-900 to-indigo-950 text-white font-bold text-xs flex items-center justify-center ring-1 ring-white/90 shadow-2xs">
              A
            </div>
            <div className="text-left hidden xl:block leading-tight">
              <p className="text-xs font-bold text-slate-900">Admin</p>
              <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Reconciled
              </p>
            </div>
          </div>

          {/* Mobile Menu Trigger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-100/70"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden mt-2 p-3 rounded-2xl bg-white/95 backdrop-blur-vision border border-white/90 shadow-2xl space-y-1 overflow-hidden"
          >
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`w-full px-3 py-2.5 rounded-xl text-left text-xs font-bold flex items-center gap-2.5 transition-colors ${
                  activeTab === item.id ? "bg-blue-50 text-blue-700" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

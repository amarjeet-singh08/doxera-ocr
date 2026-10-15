"use client";

import React, { useState, useEffect, useRef } from "react";
import { Bell, Inbox, AlertTriangle, XCircle, Zap, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface NotificationCenterProps {
  pendingCount?: number;
  failedCount?: number;
  rejectedCount?: number;
  quotaRemaining?: number;
  quotaTotal?: number;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  pendingCount = 16,
  failedCount = 0,
  rejectedCount = 0,
  quotaRemaining = 150,
  quotaTotal = 200,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const totalAlerts = pendingCount + failedCount + rejectedCount;

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener("click", handleOutsideClick);
      document.addEventListener("keydown", handleEscape);
    }
    return () => {
      document.removeEventListener("click", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  const quotaPercent = Math.min(Math.round((quotaRemaining / quotaTotal) * 100), 100);

  return (
    <div className="relative shrink-0" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-white/80 active:scale-95 transition-all relative border border-transparent hover:border-slate-200/80"
        aria-label="View operational notifications and quota"
        aria-expanded={isOpen}
      >
        <Bell className="w-5 h-5" />
        {totalAlerts > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500 ring-2 ring-white" />
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 8 }}
            transition={{ type: "spring", stiffness: 450, damping: 26 }}
            className="absolute right-0 mt-2.5 w-[calc(100vw-32px)] sm:w-84 max-w-sm rounded-2xl shadow-2xl border border-slate-200/90 overflow-hidden z-50 origin-top-right"
            style={{
              background: "#FFFFFF",
              boxShadow: "0 25px 60px -12px rgba(15, 23, 42, 0.28), 0 0 0 1px rgba(15, 23, 42, 0.08)",
            }}
          >
            {/* Control Center Header */}
            <div className="px-4 py-3 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 text-white flex items-center justify-between border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-bold text-xs uppercase tracking-wider text-slate-100">Notifications</span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-slate-300 border border-white/15 tracking-wide">
                Live Quota
              </span>
            </div>

            {/* List Items */}
            <div className="divide-y divide-slate-100 bg-white">
              <a
                href="#review"
                onClick={() => setIsOpen(false)}
                className="group px-4 py-3 hover:bg-amber-50/70 transition-colors flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 border border-amber-200 shadow-sm group-hover:scale-105 transition-transform">
                    <Inbox className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-900 group-hover:text-amber-900 truncate">Pending Review</p>
                    <p className="text-[11px] text-slate-500 truncate">Awaiting human verification</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                    {pendingCount}
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-amber-600 transition-colors" />
                </div>
              </a>

              <a
                href="#failed"
                onClick={() => setIsOpen(false)}
                className="group px-4 py-3 hover:bg-rose-50/70 transition-colors flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center shrink-0 border border-rose-200 shadow-sm group-hover:scale-105 transition-transform">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-900 group-hover:text-rose-900 truncate">Failed Extraction</p>
                    <p className="text-[11px] text-slate-500 truncate">Format or OCR mismatch</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-900 border border-rose-300">
                    {failedCount}
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-rose-600 transition-colors" />
                </div>
              </a>

              <a
                href="#rejected"
                onClick={() => setIsOpen(false)}
                className="group px-4 py-3 hover:bg-rose-50/70 transition-colors flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center shrink-0 border border-rose-200 shadow-sm group-hover:scale-105 transition-transform">
                    <XCircle className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-900 group-hover:text-rose-900 truncate">Rejected Dockets</p>
                    <p className="text-[11px] text-slate-500 truncate">Flagged by supervisor</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-900 border border-rose-300">
                    {rejectedCount}
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-rose-600 transition-colors" />
                </div>
              </a>
            </div>

            {/* Quota Progress Meter Footer */}
            <div className="px-4 py-3.5 bg-slate-50/95 border-t border-slate-100">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  Remaining AI Limit
                </span>
                <span className={`text-xs font-extrabold ${quotaRemaining < 20 ? "text-rose-600" : "text-emerald-700"}`}>
                  {quotaRemaining} Dockets
                </span>
              </div>
              <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    quotaRemaining < 20 ? "bg-rose-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${quotaPercent}%` }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

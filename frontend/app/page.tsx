"use client";

import React, { useState } from "react";
import { LiquidNavbar } from "@/components/liquid/LiquidNavbar";
import { LiquidLens } from "@/components/liquid/LiquidLens";
import { LiquidButton } from "@/components/liquid/LiquidButton";
import {
  UploadCloud,
  FileText,
  Presentation,
  Layers,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowUpRight,
  TrendingUp,
  Package,
  Scale,
  RefreshCw,
  Search,
  Filter,
} from "lucide-react";
import { motion } from "framer-motion";

export default function DoxeraDashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [activeSegment, setActiveSegment] = useState("unbilled");
  const [selectedMonth, setSelectedMonth] = useState("ALL");

  return (
    <div className="flex-1 flex flex-col w-full pb-20">
      {/* Top Floating VisionOS Navbar */}
      <LiquidNavbar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Workspace Container */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 space-y-6 mt-4">
        {/* 1. Header Banner & Action Lens */}
        <LiquidLens
          refraction={0.14}
          bevel={20}
          aberration={0.18}
          zIndex={10}
          className="p-5 sm:p-7"
        >
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-slate-100/90 text-slate-700 border border-slate-200/80 mb-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                North Express Logistics Commercial Audit
              </div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900 tracking-tight">
                Logistics Sales Intelligence & OCR Audit
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium">
                Cognitive extraction ledger reconciled across 797 consignments.
              </p>
            </div>

            {/* Top Tactical Action Cluster */}
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <LiquidButton variant="secondary" size="md" icon={<FileText className="w-4 h-4 text-slate-500" />}>
                Audit PDF
              </LiquidButton>
              <LiquidButton variant="secondary" size="md" icon={<Presentation className="w-4 h-4 text-slate-500" />}>
                Export PPTX
              </LiquidButton>
              <LiquidButton variant="primary" size="md" icon={<UploadCloud className="w-4 h-4" />}>
                Ingest Dockets
              </LiquidButton>
            </div>
          </div>

          {/* Two-Tier Segment & Saved Report Management Toolbar */}
          <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4 mt-6 pt-5 border-t border-slate-200/80">
            {/* Tier 1: View Segments */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="p-1 rounded-xl bg-slate-100/80 border border-slate-200/90 flex items-center gap-1">
                {[
                  { id: "unbilled", label: "Unbilled", color: "bg-amber-500" },
                  { id: "billed", label: "Billed", color: "bg-blue-600" },
                  { id: "for_update", label: "Rate Pending", color: "bg-rose-500" },
                  { id: "all", label: "Consolidated", color: "bg-slate-700" },
                ].map((seg) => (
                  <button
                    key={seg.id}
                    onClick={() => setActiveSegment(seg.id)}
                    className={`relative px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 select-none ${
                      activeSegment === seg.id ? "text-slate-900" : "text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {activeSegment === seg.id && (
                      <motion.div
                        layoutId="activeSegmentPill"
                        className="absolute inset-0 bg-white rounded-lg shadow-sm border border-slate-200/90"
                        transition={{ type: "spring", stiffness: 450, damping: 28 }}
                      />
                    )}
                    <span className={`relative z-10 w-2 h-2 rounded-full ${seg.color}`} />
                    <span className="relative z-10">{seg.label}</span>
                  </button>
                ))}
              </div>

              {/* Month Selector */}
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="h-9 px-3 text-xs font-bold text-slate-700 bg-white/90 border border-slate-200/90 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                aria-label="Filter by month"
              >
                <option value="ALL">All Recorded Months</option>
                <option value="2026-10">October 2026</option>
                <option value="2026-09">September 2026</option>
              </select>
            </div>

            {/* Tier 2: Report Switcher & Actions */}
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5">
              <select
                className="flex-1 sm:flex-initial h-9 px-3 text-xs font-bold text-slate-800 bg-white/90 border border-slate-200/90 rounded-xl min-w-[220px]"
                aria-label="Select saved report"
              >
                <option>October Sales Audit Till 13th Oct 2026</option>
                <option>September Consolidated Ledger Final</option>
              </select>
              <div className="flex items-center gap-2 shrink-0">
                <LiquidButton variant="secondary" size="sm" icon={<Layers className="w-3.5 h-3.5 text-slate-500" />}>
                  All Reports (2)
                </LiquidButton>
                <LiquidButton variant="danger" size="sm" icon={<Trash2 className="w-3.5 h-3.5" />}>
                  Delete
                </LiquidButton>
              </div>
            </div>
          </div>
        </LiquidLens>

        {/* 2. Executive Metric Grid */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          <LiquidLens refraction={0.1} bevel={16} zIndex={10} className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Revenue</span>
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-slate-900 tracking-tight mt-3">₹4,28,490</p>
            <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-400 font-semibold">Reconciled Freight</span>
              <span className="font-bold text-emerald-600 flex items-center gap-0.5">
                +12.4% <ArrowUpRight className="w-3 h-3" />
              </span>
            </div>
          </LiquidLens>

          <LiquidLens refraction={0.1} bevel={16} zIndex={10} className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Verified AWBs</span>
              <div className="w-8 h-8 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center font-bold">
                <Package className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-slate-900 tracking-tight mt-3">797</p>
            <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-400 font-semibold">OCR Verification</span>
              <span className="font-bold text-slate-700">98.6% Accuracy</span>
            </div>
          </LiquidLens>

          <LiquidLens refraction={0.1} bevel={16} zIndex={10} className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Billed Weight</span>
              <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <Scale className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-slate-900 tracking-tight mt-3">14,820 kg</p>
            <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-400 font-semibold">Average Consignment</span>
              <span className="font-bold text-slate-700">18.6 kg</span>
            </div>
          </LiquidLens>

          <LiquidLens refraction={0.1} bevel={16} zIndex={10} className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Pending Review</span>
              <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-amber-700 tracking-tight mt-3">16 Dockets</p>
            <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-400 font-semibold">Action Required</span>
              <span className="font-bold text-amber-800">Verification Queue</span>
            </div>
          </LiquidLens>
        </section>

        {/* 3. Consignments & Ingestion Registry */}
        <LiquidLens refraction={0.12} bevel={22} zIndex={10} className="p-0 overflow-hidden">
          {/* Table Header Filter Toolbar */}
          <div className="p-5 border-b border-slate-200/80 flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-50/50">
            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">Active Consignment Ledger</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time extraction records matched against billing parameters.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter AWB, customer, city..."
                  className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200/90 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
              <LiquidButton variant="secondary" size="sm" icon={<Filter className="w-3.5 h-3.5 text-slate-500" />}>
                Filter
              </LiquidButton>
              <LiquidButton variant="secondary" size="sm" icon={<RefreshCw className="w-3.5 h-3.5 text-slate-500" />}>
                Reset
              </LiquidButton>
            </div>
          </div>

          {/* High-Contrast Accessible Data Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-100/80 text-slate-700 font-bold uppercase tracking-wider text-[11px] border-b border-slate-200/80">
                <tr>
                  <th className="py-3 px-4">AWB No.</th>
                  <th className="py-3 px-4">Customer Name</th>
                  <th className="py-3 px-4">Destination</th>
                  <th className="py-3 px-4 text-right">Weight (kg)</th>
                  <th className="py-3 px-4 text-right">Freight (₹)</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white/70">
                {[
                  {
                    awb: "NE-9082141",
                    customer: "Tata Motors Limited",
                    dest: "Pune Hub (PNQ)",
                    wt: "34.5",
                    freight: "₹3,450",
                    status: "VERIFIED",
                  },
                  {
                    awb: "NE-9082142",
                    customer: "Reliance Retail Logistics",
                    dest: "Bhiwandi DC (BHW)",
                    wt: "128.0",
                    freight: "₹12,800",
                    status: "VERIFIED",
                  },
                  {
                    awb: "NE-9082143",
                    customer: "Mahindra Heavy Auto",
                    dest: "Nashik Hub (NSK)",
                    wt: "12.4",
                    freight: "Pending",
                    status: "REVIEW",
                  },
                  {
                    awb: "NE-9082144",
                    customer: "Bajaj Electricals",
                    dest: "Chakan Plant (CHK)",
                    wt: "45.0",
                    freight: "₹4,950",
                    status: "VERIFIED",
                  },
                  {
                    awb: "NE-9082145",
                    customer: "Godrej Appliances",
                    dest: "Vikhroli (VKR)",
                    wt: "8.2",
                    freight: "₹1,230",
                    status: "VERIFIED",
                  },
                ].map((row, idx) => (
                  <tr key={idx} className="hover:bg-blue-50/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">{row.awb}</td>
                    <td className="py-3 px-4 font-bold text-slate-800">{row.customer}</td>
                    <td className="py-3 px-4 text-slate-600">{row.dest}</td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-slate-800">{row.wt}</td>
                    <td className="py-3 px-4 text-right font-mono font-extrabold text-slate-900">{row.freight}</td>
                    <td className="py-3 px-4 text-center">
                      {row.status === "VERIFIED" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          <CheckCircle2 className="w-3 h-3" /> Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                          <AlertCircle className="w-3 h-3" /> Review
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button className="px-3 py-1 rounded-lg text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors">
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Table Pagination Footer */}
          <div className="p-4 bg-slate-50/70 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
            <span>Showing 1 to 5 of 797 consignments</span>
            <div className="flex items-center gap-1.5">
              <button className="px-3 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 font-bold">
                Previous
              </button>
              <button className="px-3 py-1 rounded-lg border border-blue-300 bg-blue-50 text-blue-700 font-bold">
                1
              </button>
              <button className="px-3 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 font-bold">
                2
              </button>
              <button className="px-3 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 font-bold">
                Next
              </button>
            </div>
          </div>
        </LiquidLens>
      </main>
    </div>
  );
}

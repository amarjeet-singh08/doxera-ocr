"use client";

import React from "react";
import { motion, HTMLMotionProps } from "framer-motion";

interface LiquidButtonProps extends Omit<HTMLMotionProps<"button">, "children"> {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "danger" | "glass";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  className?: string;
}

export const LiquidButton: React.FC<LiquidButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  icon,
  className = "",
  ...props
}) => {
  const sizeClasses = {
    sm: "h-8 px-3 text-xs gap-1.5 rounded-lg",
    md: "h-10 px-4 text-sm gap-2 rounded-xl",
    lg: "h-12 px-6 text-base gap-2.5 rounded-2xl",
  }[size];

  const variantClasses = {
    primary:
      "bg-gradient-to-br from-blue-700 to-blue-800 text-white font-bold border border-white/30 shadow-md shadow-blue-600/30",
    secondary:
      "bg-white/95 text-slate-900 font-bold border border-slate-300/90 shadow-sm hover:border-slate-400",
    danger:
      "bg-gradient-to-br from-rose-600 to-red-700 text-white font-bold border border-white/25 shadow-md shadow-rose-600/30",
    glass:
      "bg-white/80 backdrop-blur-xl text-slate-800 font-bold border border-white/90 shadow-sm hover:bg-white/95",
  }[variant];

  return (
    <motion.button
      whileHover={{ y: -2, scale: 1.02 }}
      whileTap={{ scale: 0.95, y: 1 }}
      transition={{
        type: "spring",
        stiffness: 420,
        damping: 18,
        mass: 0.8,
      }}
      className={`inline-flex items-center justify-center select-none cursor-pointer tracking-tight transition-colors ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span className="truncate">{children}</span>
    </motion.button>
  );
};

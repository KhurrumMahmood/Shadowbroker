"use client";

import { type ReactNode } from "react";

interface ArtifactShellProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export default function ArtifactShell({ title, children, className = "" }: ArtifactShellProps) {
  return (
    <div className={`sb-card ${className}`}>
      {title && <h2 className="sb-heading">{title}</h2>}
      {children}
    </div>
  );
}

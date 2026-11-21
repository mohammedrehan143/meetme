"use client";

import React, { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { api } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);

  useEffect(() => {
    loadApprovalsCount();
  }, []);

  const loadApprovalsCount = async () => {
    try {
      const approvals = await api.getApprovals("PENDING");
      setPendingApprovalsCount(approvals.length);
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-primary text-text-primary">
      <Sidebar pendingApprovalsCount={pendingApprovalsCount} />
      <div className="flex flex-col flex-1 h-full overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto bg-bg-primary p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

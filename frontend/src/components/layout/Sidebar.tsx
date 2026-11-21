"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Radio, 
  History, 
  CheckSquare, 
  ShieldAlert, 
  Cpu, 
  BarChart3, 
  Users, 
  Mail, 
  Settings,
  ChevronLeft,
  ChevronRight
} from "lucide-react";

interface SidebarProps {
  pendingApprovalsCount?: number;
}

export function Sidebar({ pendingApprovalsCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);

  const workspaceLinks = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Live Meeting", href: "/live", icon: Radio, highlight: true },
    { name: "Meeting History", href: "/meetings", icon: History },
    { name: "Tasks", href: "/tasks", icon: CheckSquare },
    { 
      name: "Approvals", 
      href: "/approvals", 
      icon: ShieldAlert, 
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined 
    },
    { name: "Automations", href: "/automations", icon: Cpu },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
  ];

  const managementLinks = [
    { name: "Team", href: "/team", icon: Users },
    { name: "Email Activity", href: "/emails", icon: Mail },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={`relative flex flex-col bg-bg-secondary border-r border-border-subtle transition-all duration-200 select-none ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Brand Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border-subtle">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-accent-orange flex items-center justify-center font-bold text-xs text-black tracking-wider">
              M
            </div>
            <div className="flex flex-col">
              <span className="font-bold tracking-wider text-sm text-text-primary">MEETME</span>
              <span className="text-[9px] font-mono tracking-widest text-accent-neon uppercase">EXECUTION OUT</span>
            </div>
          </Link>
        )}
        {collapsed && (
          <Link href="/" className="mx-auto">
            <div className="w-6 h-6 rounded bg-accent-orange flex items-center justify-center font-bold text-xs text-black">
              M
            </div>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-text-secondary hover:text-text-primary p-1 rounded hover:bg-bg-elevated transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Nav Content */}
      <div className="flex-1 py-4 overflow-y-auto px-2 space-y-6">
        {/* Workspace Section */}
        <div>
          {!collapsed && (
            <div className="px-2 pb-2 text-[10px] font-mono font-semibold tracking-wider text-text-muted uppercase">
              Workspace
            </div>
          )}
          <nav className="space-y-0.5">
            {workspaceLinks.map((item) => {
              const active = isActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-2.5 py-2 text-xs font-medium rounded transition-colors ${
                    active
                      ? "bg-accent-orange text-black font-semibold shadow-sm"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-card"
                  }`}
                  title={collapsed ? item.name : undefined}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={15} className={active ? "text-black" : "text-text-secondary"} />
                    {!collapsed && <span>{item.name}</span>}
                  </div>
                  {!collapsed && item.badge && (
                    <span
                      className={`px-1.5 py-0.5 text-[10px] font-mono font-bold rounded ${
                        active ? "bg-black text-accent-orange" : "bg-accent-orange text-black"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Management Section */}
        <div>
          {!collapsed && (
            <div className="px-2 pb-2 text-[10px] font-mono font-semibold tracking-wider text-text-muted uppercase">
              Management
            </div>
          )}
          <nav className="space-y-0.5">
            {managementLinks.map((item) => {
              const active = isActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-2.5 py-2 text-xs font-medium rounded transition-colors ${
                    active
                      ? "bg-accent-orange text-black font-semibold shadow-sm"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-card"
                  }`}
                  title={collapsed ? item.name : undefined}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={15} className={active ? "text-black" : "text-text-secondary"} />
                    {!collapsed && <span>{item.name}</span>}
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer System Status */}
      {!collapsed && (
        <div className="p-3 border-t border-border-subtle bg-bg-card/50">
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-neon animate-pulse"></span>
              <span className="text-text-secondary font-mono text-[10px]">Groq Pipeline</span>
            </div>
            <span className="text-accent-neon font-mono text-[10px] font-medium">READY</span>
          </div>
        </div>
      )}
    </aside>
  );
}

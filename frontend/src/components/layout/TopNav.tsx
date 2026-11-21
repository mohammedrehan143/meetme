"use client";

import React, { useState, useEffect } from "react";
import { Bell, Search, ChevronDown, Check, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import { api } from "@/lib/api";
import { NotificationItem } from "@/lib/types";

export function TopNav() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [currentUser, setCurrentUser] = useState<{ name: string; title: string; initials: string }>({
    name: "Workspace Member",
    title: "Admin",
    initials: "ME",
  });
  const [workspaceName, setWorkspaceName] = useState("MEETME Workspace");

  useEffect(() => {
    loadNotifications();
    loadUserProfile();
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadUserProfile = async () => {
    try {
      const team = await api.getTeam();
      if (team && team.length > 0) {
        const primary = team.find((m) => m.role === "admin") || team[0];
        const names = primary.full_name.trim().split(/\s+/);
        const initials = names.length > 1
          ? `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase()
          : primary.full_name.slice(0, 2).toUpperCase();
        setCurrentUser({
          name: primary.full_name,
          title: primary.title || "Team Member",
          initials,
        });
      }
    } catch {
      // ignore
    }
  };

  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(data);
      setUnreadCount(data.filter((n) => !n.is_read).length);
    } catch {
      // ignore
    }
  };

  const markRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  return (
    <header className="h-14 bg-bg-secondary border-b border-border-subtle flex items-center justify-between px-6 z-20">
      {/* Workspace Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-bg-card border border-border-subtle text-xs font-medium text-text-primary cursor-pointer hover:border-border-strong transition-colors">
          <div className="w-2 h-2 rounded-full bg-accent-orange"></div>
          <span>{workspaceName}</span>
          <ChevronDown size={12} className="text-text-secondary" />
        </div>
      </div>

      {/* Center Search */}
      <div className="relative w-80 max-w-sm hidden md:block">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          placeholder="Search meetings, tasks, decisions..."
          className="w-full bg-bg-card border border-border-subtle rounded py-1.5 pl-8 pr-3 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-orange transition-colors"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Notifications Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="relative p-2 text-text-secondary hover:text-text-primary rounded hover:bg-bg-card transition-colors"
            title="Notifications"
          >
            <Bell size={16} />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent-orange"></span>
            )}
          </button>

          {showNotifs && (
            <div className="absolute right-0 mt-2 w-80 bg-bg-card border border-border-subtle rounded-md shadow-xl py-2 z-50">
              <div className="flex items-center justify-between px-3 py-1.5 border-b border-border-subtle text-xs">
                <span className="font-semibold text-text-primary">Notifications</span>
                <span className="font-mono text-[10px] text-text-muted">{unreadCount} Unread</span>
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-border-subtle">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-xs text-text-muted">No notifications</div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => markRead(n.id)}
                      className={`p-3 text-xs hover:bg-bg-elevated cursor-pointer transition-colors ${
                        !n.is_read ? "bg-bg-elevated/40" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-text-primary">{n.title}</span>
                        {!n.is_read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-accent-orange"></span>
                        )}
                      </div>
                      <p className="text-text-secondary text-[11px] leading-relaxed">{n.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="h-4 w-px bg-border-subtle"></div>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-1">
          <div className="w-7 h-7 rounded bg-bg-elevated border border-border-subtle flex items-center justify-center font-mono text-xs font-semibold text-accent-orange">
            {currentUser.initials}
          </div>
          <div className="hidden sm:flex flex-col text-left">
            <span className="text-xs font-medium text-text-primary leading-none">{currentUser.name}</span>
            <span className="text-[10px] font-mono text-text-muted">{currentUser.title}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

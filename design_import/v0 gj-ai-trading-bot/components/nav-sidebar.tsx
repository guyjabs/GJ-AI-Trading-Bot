"use client"

import type React from "react"

import { BarChart3, TrendingUp, Zap, Search, Bot, Wifi } from "lucide-react"
import type { ViewType } from "@/app/page"

interface NavSidebarProps {
  activeView: ViewType
  onViewChange: (view: ViewType) => void
}

const navItems: { id: ViewType; label: string; icon: React.ElementType }[] = [
  { id: "strategy", label: "Strategy", icon: BarChart3 },
  { id: "trading", label: "Trading Dashboard", icon: TrendingUp },
  { id: "day-trading", label: "Day Trading", icon: Zap },
  { id: "research", label: "Research", icon: Search },
  { id: "scalping", label: "Scalping Bot", icon: Bot },
]

export function NavSidebar({ activeView, onViewChange }: NavSidebarProps) {
  return (
    <aside className="w-[200px] bg-card border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-semibold text-sm text-foreground">GJ Trading</h1>
            <p className="text-[11px] text-muted-foreground">AI Bot v2.0</p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-2">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeView === item.id
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-colors ${
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Connection Status */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2 px-3 py-2 bg-success/10 rounded-md">
          <Wifi className="w-4 h-4 text-success" />
          <span className="text-[12px] font-medium text-success">Alpaca Connected</span>
        </div>
      </div>
    </aside>
  )
}

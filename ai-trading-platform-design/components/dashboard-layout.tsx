"use client"

import type React from "react"

import { useState } from "react"
import Link from "next/link"
import {
  Activity,
  Bot,
  ChevronDown,
  Cpu,
  DollarSign,
  LayoutDashboard,
  LineChart,
  Menu,
  Settings,
  Shield,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard, current: true },
  { name: "Portfolio", href: "#", icon: Wallet },
  { name: "Screener", href: "#", icon: TrendingUp },
  { name: "Risk Control", href: "#", icon: Shield },
  { name: "Bot Manager", href: "#", icon: Bot },
  { name: "Analytics", href: "#", icon: LineChart },
  { name: "Settings", href: "#", icon: Settings },
]

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-64 bg-sidebar border-r border-sidebar-border transition-transform duration-300 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-sidebar-border">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-primary/20">
                <Cpu className="h-5 w-5 text-primary" />
              </div>
              <span className="text-lg font-bold text-foreground glow-green">NexTrade</span>
              <span className="text-xs text-primary bg-primary/20 px-1.5 py-0.5 rounded">AI</span>
            </div>
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Connection Status */}
          <div className="px-4 py-3 border-b border-sidebar-border">
            <div className="flex items-center gap-2 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              <span className="text-muted-foreground">Connected to Robinhood</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  item.current
                    ? "bg-sidebar-accent text-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Bot Status */}
          <div className="p-4 border-t border-sidebar-border">
            <div className="p-3 rounded-md bg-primary/10 border border-primary/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-primary">Trading Bot</span>
                <span className="text-xs text-primary bg-primary/20 px-2 py-0.5 rounded-full">ACTIVE</span>
              </div>
              <div className="text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Trades Today</span>
                  <span className="text-foreground">24</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span>Win Rate</span>
                  <span className="text-primary">78.3%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 bg-background/95 backdrop-blur border-b border-border">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <div className="hidden sm:flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Market Status:</span>
              <span className="flex items-center gap-1.5 text-primary">
                <Activity className="h-3 w-3" />
                Open
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Balance:</span>
                <span className="text-foreground font-medium">$127,432.89</span>
              </div>
              <div className="h-4 w-px bg-border" />
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                <span className="text-primary font-medium">+$3,241.56</span>
                <span className="text-muted-foreground">(+2.61%)</span>
              </div>
            </div>
            <Button variant="outline" size="sm" className="gap-2 bg-transparent">
              <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              Demo Mode
              <ChevronDown className="h-3 w-3" />
            </Button>
          </div>
        </header>

        {/* Page content */}
        <main className="min-h-[calc(100vh-4rem)]">{children}</main>
      </div>
    </div>
  )
}

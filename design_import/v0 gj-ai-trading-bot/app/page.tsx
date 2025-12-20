"use client"

import { useState } from "react"
import { NavSidebar } from "@/components/nav-sidebar"
import { ContentHeader } from "@/components/content-header"
import { TickerTape } from "@/components/ticker-tape"
import { ActivitySidebar } from "@/components/activity-sidebar"
import { StrategyView } from "@/components/views/strategy-view"
import { TradingView } from "@/components/views/trading-view"
import { DayTradingView } from "@/components/views/day-trading-view"
import { ResearchView } from "@/components/views/research-view"
import { ScalpingView } from "@/components/views/scalping-view"

export type ViewType = "strategy" | "trading" | "day-trading" | "research" | "scalping"

export default function TradingBot() {
  const [activeView, setActiveView] = useState<ViewType>("trading")

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Sidebar - 200px */}
      <NavSidebar activeView={activeView} onViewChange={setActiveView} />

      {/* Center - Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-background">
        <ContentHeader />
        <TickerTape />

        <div className="flex-1 overflow-auto p-4">
          {activeView === "strategy" && <StrategyView />}
          {activeView === "trading" && <TradingView />}
          {activeView === "day-trading" && <DayTradingView />}
          {activeView === "research" && <ResearchView />}
          {activeView === "scalping" && <ScalpingView />}
        </div>
      </main>

      {/* Right Sidebar - 280px */}
      <ActivitySidebar />
    </div>
  )
}

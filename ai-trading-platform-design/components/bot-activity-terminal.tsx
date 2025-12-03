"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Play, Pause, RotateCcw, Terminal, ChevronRight, Cpu, Activity, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

const initialLogs = [
  { time: "14:32:01", type: "system", message: "[BOOT] NexTrade AI v2.4.1 initialized" },
  { time: "14:32:02", type: "system", message: "[AUTH] Robinhood API connection established" },
  { time: "14:32:03", type: "info", message: "[SCAN] Running momentum screener on 500+ assets..." },
  { time: "14:32:05", type: "success", message: "[SIGNAL] NVDA: Strong buy signal detected (score: 94)" },
  { time: "14:32:06", type: "trade", message: "[EXEC] BUY 5 NVDA @ $875.28 (limit order placed)" },
  { time: "14:32:08", type: "success", message: "[FILL] Order filled: 5 NVDA @ $875.12" },
  { time: "14:32:10", type: "info", message: "[RISK] Position size: 3.4% (within limits)" },
  { time: "14:32:12", type: "info", message: "[STOP] Auto stop-loss set at $831.36 (-5%)" },
  { time: "14:32:15", type: "system", message: "[SCAN] Crypto market analysis in progress..." },
  { time: "14:32:18", type: "warning", message: "[ALERT] High volatility detected: ETH ±4.2%" },
  { time: "14:32:20", type: "info", message: "[HOLD] ETH position maintained (no action)" },
  { time: "14:32:25", type: "success", message: "[P/L] Daily profit: +$3,241.56 (+2.61%)" },
]

const newLogs = [
  { type: "info", message: "[SCAN] Analyzing 847 assets across 12 sectors..." },
  { type: "success", message: "[SIGNAL] AMD: Momentum breakout detected" },
  { type: "trade", message: "[EXEC] Evaluating position sizing for AMD..." },
  { type: "warning", message: "[RISK] Sector exposure limit approaching (Tech: 45%)" },
  { type: "info", message: "[ML] Model confidence: 87.3% for current signals" },
  { type: "success", message: "[PERF] Win rate today: 78.3% (18/23 trades)" },
  { type: "system", message: "[SYNC] Portfolio data refreshed" },
]

export function BotActivityTerminal() {
  const [logs, setLogs] = useState(initialLogs)
  const [isRunning, setIsRunning] = useState(true)
  const [logIndex, setLogIndex] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isRunning) return

    const interval = setInterval(() => {
      const now = new Date()
      const timeStr = now.toLocaleTimeString("en-US", { hour12: false })
      const newLog = {
        time: timeStr,
        ...newLogs[logIndex % newLogs.length],
      }

      setLogs((prev) => [...prev.slice(-50), newLog])
      setLogIndex((prev) => prev + 1)
    }, 3000)

    return () => clearInterval(interval)
  }, [isRunning, logIndex])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  const getLogColor = (type: string) => {
    switch (type) {
      case "success":
        return "text-primary"
      case "trade":
        return "text-accent"
      case "warning":
        return "text-warning"
      case "error":
        return "text-destructive"
      case "system":
        return "text-muted-foreground"
      default:
        return "text-foreground"
    }
  }

  const stats = [
    { label: "Trades Today", value: "24", icon: Activity },
    { label: "Win Rate", value: "78.3%", icon: Zap },
    { label: "Avg Latency", value: "12ms", icon: Cpu },
  ]

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <CardTitle className="text-lg font-medium flex items-center gap-2">
            <span className="text-primary">{">>"}</span>
            <Terminal className="h-4 w-4" />
            Bot Activity Terminal
            <Badge
              variant="outline"
              className={cn(
                "text-xs ml-2",
                isRunning ? "border-primary/50 text-primary" : "border-muted-foreground/50 text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full mr-1.5",
                  isRunning ? "bg-primary animate-pulse" : "bg-muted-foreground",
                )}
              />
              {isRunning ? "RUNNING" : "PAUSED"}
            </Badge>
          </CardTitle>

          <div className="flex items-center gap-2">
            <div className="hidden md:flex items-center gap-4 mr-4">
              {stats.map((stat) => (
                <div key={stat.label} className="flex items-center gap-1.5 text-xs">
                  <stat.icon className="h-3 w-3 text-muted-foreground" />
                  <span className="text-muted-foreground">{stat.label}:</span>
                  <span className="text-foreground font-medium">{stat.value}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0 bg-transparent"
                onClick={() => setIsRunning(!isRunning)}
              >
                {isRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0 bg-transparent"
                onClick={() => setLogs(initialLogs)}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          ref={scrollRef}
          className="h-[200px] overflow-y-auto rounded-md bg-[oklch(0.11_0.005_260)] border border-border p-3 terminal-grid"
        >
          <div className="space-y-1 font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 group">
                <span className="text-muted-foreground shrink-0">{log.time}</span>
                <ChevronRight className="h-3 w-3 text-primary mt-0.5 shrink-0 opacity-50 group-hover:opacity-100" />
                <span className={cn(getLogColor(log.type), "break-all")}>{log.message}</span>
              </div>
            ))}
            <div className="flex items-center gap-2 text-primary">
              <span className="animate-pulse">█</span>
              <span className="text-muted-foreground">Awaiting next signal...</span>
            </div>
          </div>
        </div>

        {/* Command Input */}
        <div className="mt-3 flex items-center gap-2 p-2 rounded-md bg-secondary/30 border border-border">
          <ChevronRight className="h-4 w-4 text-primary" />
          <input
            type="text"
            placeholder="Enter command (e.g., 'status', 'pause', 'positions')..."
            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.currentTarget.value) {
                const now = new Date()
                const timeStr = now.toLocaleTimeString("en-US", { hour12: false })
                setLogs((prev) => [
                  ...prev,
                  {
                    time: timeStr,
                    type: "system",
                    message: `[CMD] Executing: ${e.currentTarget.value}`,
                  },
                ])
                e.currentTarget.value = ""
              }
            }}
          />
        </div>
      </CardContent>
    </Card>
  )
}

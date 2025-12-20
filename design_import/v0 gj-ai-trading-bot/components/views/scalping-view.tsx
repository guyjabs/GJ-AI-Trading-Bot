"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Bot, Square, Settings, Zap, TrendingUp, TrendingDown, Clock, AlertCircle } from "lucide-react"

const signalLog = [
  { time: "13:45:32", type: "entry", symbol: "AAPL", action: "BUY", price: "$178.45", status: "executed" },
  {
    time: "13:44:58",
    type: "exit",
    symbol: "MSFT",
    action: "SELL",
    price: "$378.90",
    pnl: "+$12.40",
    status: "executed",
  },
  { time: "13:44:12", type: "signal", symbol: "NVDA", action: "ANALYZING", price: "$875.20", status: "pending" },
  {
    time: "13:43:45",
    type: "skip",
    symbol: "TSLA",
    action: "SKIP",
    price: "$248.50",
    reason: "Low volume",
    status: "skipped",
  },
  { time: "13:42:30", type: "entry", symbol: "META", action: "BUY", price: "$505.60", status: "executed" },
  {
    time: "13:41:15",
    type: "exit",
    symbol: "GOOGL",
    action: "SELL",
    price: "$141.75",
    pnl: "-$3.20",
    status: "executed",
  },
]

function getSignalIcon(type: string) {
  switch (type) {
    case "entry":
      return <TrendingUp className="w-3.5 h-3.5 text-success" />
    case "exit":
      return <TrendingDown className="w-3.5 h-3.5 text-destructive" />
    case "signal":
      return <Zap className="w-3.5 h-3.5 text-amber-500" />
    case "skip":
      return <AlertCircle className="w-3.5 h-3.5 text-muted-foreground" />
    default:
      return <Clock className="w-3.5 h-3.5 text-muted-foreground" />
  }
}

export function ScalpingView() {
  return (
    <div className="space-y-4">
      {/* Status Banner */}
      <Card className="bg-success/10 border-success/30">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-success/20 rounded-lg">
                <Bot className="w-6 h-6 text-success" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-semibold text-success">RUNNING</span>
                  <span className="flex items-center gap-1 text-[11px] text-success/80">
                    <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                    Active
                  </span>
                </div>
                <p className="text-[12px] text-muted-foreground mt-0.5">
                  Penny Flip Engine • Scanning 142 symbols • Last signal 45s ago
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-8 gap-1.5 bg-transparent">
                <Settings className="w-3.5 h-3.5" />
                Config
              </Button>
              <Button variant="destructive" size="sm" className="h-8 gap-1.5">
                <Square className="w-3.5 h-3.5" />
                Stop Bot
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        {/* Configuration Panel */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Settings className="w-4 h-4 text-primary" />
              Bot Configuration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-muted-foreground">Min Volatility (%)</Label>
                <Input type="number" defaultValue="2.5" className="h-8 text-[13px] font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-muted-foreground">Profit Target (%)</Label>
                <Input type="number" defaultValue="0.5" className="h-8 text-[13px] font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-muted-foreground">Stop Loss (%)</Label>
                <Input type="number" defaultValue="0.25" className="h-8 text-[13px] font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-muted-foreground">Max Position Size ($)</Label>
                <Input type="number" defaultValue="5000" className="h-8 text-[13px] font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-muted-foreground">Min Volume (K)</Label>
                <Input type="number" defaultValue="500" className="h-8 text-[13px] font-mono" />
              </div>
              <Button className="w-full h-8 text-[12px]">Update Configuration</Button>
            </div>
          </CardContent>
        </Card>

        {/* Stats + Controls */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Session Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Trades Today</span>
                <span className="text-[13px] font-semibold font-mono text-foreground">24</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Win Rate</span>
                <span className="text-[13px] font-semibold font-mono text-success">68%</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Session P&L</span>
                <span className="text-[13px] font-semibold font-mono text-success">+$342.50</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Avg Trade P&L</span>
                <span className="text-[13px] font-semibold font-mono text-success">+$14.27</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Active Positions</span>
                <span className="text-[13px] font-semibold font-mono text-foreground">3</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md">
                <span className="text-[12px] text-muted-foreground">Signals Skipped</span>
                <span className="text-[13px] font-semibold font-mono text-muted-foreground">12</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Signal Log */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              Live Signal Log
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5 max-h-[320px] overflow-auto custom-scrollbar">
              {signalLog.map((signal, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2 p-2 rounded-md text-[11px] ${
                    signal.status === "pending"
                      ? "bg-amber-500/10 border border-amber-500/30"
                      : signal.status === "skipped"
                        ? "bg-muted/30"
                        : "bg-muted/50"
                  }`}
                >
                  {getSignalIcon(signal.type)}
                  <span className="font-mono text-muted-foreground w-16 shrink-0">{signal.time}</span>
                  <span className="font-semibold text-foreground w-12">{signal.symbol}</span>
                  <span
                    className={`w-16 font-medium ${
                      signal.action === "BUY"
                        ? "text-success"
                        : signal.action === "SELL"
                          ? "text-destructive"
                          : signal.action === "ANALYZING"
                            ? "text-amber-500"
                            : "text-muted-foreground"
                    }`}
                  >
                    {signal.action}
                  </span>
                  <span className="font-mono text-foreground">{signal.price}</span>
                  {signal.pnl && (
                    <span
                      className={`ml-auto font-mono ${
                        signal.pnl.startsWith("+") ? "text-success" : "text-destructive"
                      }`}
                    >
                      {signal.pnl}
                    </span>
                  )}
                  {signal.reason && <span className="ml-auto text-muted-foreground truncate">{signal.reason}</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

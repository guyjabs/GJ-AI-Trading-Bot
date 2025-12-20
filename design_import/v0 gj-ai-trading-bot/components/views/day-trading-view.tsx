"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Zap, TrendingUp, ArrowUpRight, ArrowDownRight, Target, ShieldAlert, Search } from "lucide-react"

const gappers = [
  { symbol: "SMCI", gap: "+12.5%", volume: "2.4M", price: "$845.20" },
  { symbol: "ARM", gap: "+8.2%", volume: "1.8M", price: "$152.30" },
  { symbol: "PLTR", gap: "+5.7%", volume: "3.2M", price: "$24.85" },
]

const momentum = [
  { symbol: "COIN", change: "+4.2%", rsi: 72, volume: "High" },
  { symbol: "MARA", change: "+3.8%", rsi: 68, volume: "High" },
  { symbol: "RIOT", change: "+3.1%", rsi: 65, volume: "Med" },
]

const dayTrades = [
  {
    symbol: "SMCI",
    shares: 10,
    entry: 842.5,
    current: 845.2,
    sl: 835.0,
    tp: 860.0,
    pnl: 27.0,
    pnlPct: 0.32,
  },
  {
    symbol: "COIN",
    shares: 50,
    entry: 245.8,
    current: 248.5,
    sl: 242.0,
    tp: 255.0,
    pnl: 135.0,
    pnlPct: 1.1,
  },
]

export function DayTradingView() {
  return (
    <div className="space-y-4">
      {/* Market Context Banner */}
      <Card className="bg-accent/30 border-accent">
        <CardContent className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-1.5 bg-success/10 rounded-md">
                <TrendingUp className="w-4 h-4 text-success" />
              </div>
              <div>
                <p className="text-[13px] font-medium text-foreground">Market Context: Bullish</p>
                <p className="text-[12px] text-muted-foreground">SPY +0.8% • VIX 14.2 • Sector rotation into tech</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[12px]">
              <span className="text-muted-foreground">Day Trades Used:</span>
              <span className="font-semibold text-foreground">1 / 3</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scanner Results */}
      <div className="grid grid-cols-2 gap-4">
        {/* Gappers */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              Pre-Market Gappers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {gappers.map((stock) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md border border-border/50"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-[13px] text-foreground">{stock.symbol}</span>
                    <span className="text-[12px] text-success font-mono">{stock.gap}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-muted-foreground">Vol: {stock.volume}</span>
                    <span className="text-[12px] font-mono text-foreground">{stock.price}</span>
                    <Button size="sm" variant="outline" className="h-6 text-[11px] px-2 bg-transparent">
                      <Search className="w-3 h-3 mr-1" />
                      Analyze
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Momentum */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Momentum Movers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {momentum.map((stock) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-2.5 bg-muted/50 rounded-md border border-border/50"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-[13px] text-foreground">{stock.symbol}</span>
                    <span className="text-[12px] text-success font-mono">{stock.change}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-muted-foreground">RSI: {stock.rsi}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded ${
                        stock.volume === "High" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {stock.volume}
                    </span>
                    <Button size="sm" variant="outline" className="h-6 text-[11px] px-2 bg-transparent">
                      <Search className="w-3 h-3 mr-1" />
                      Analyze
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Day Trades */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            Active Day Trades
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 font-medium text-muted-foreground">Symbol</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">Shares</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">Entry</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">Current</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">
                    <span className="flex items-center justify-end gap-1">
                      <ShieldAlert className="w-3 h-3" /> Stop Loss
                    </span>
                  </th>
                  <th className="text-right py-2 font-medium text-muted-foreground">
                    <span className="flex items-center justify-end gap-1">
                      <Target className="w-3 h-3" /> Take Profit
                    </span>
                  </th>
                  <th className="text-right py-2 font-medium text-muted-foreground">P&L</th>
                </tr>
              </thead>
              <tbody>
                {dayTrades.map((trade) => (
                  <tr key={trade.symbol} className="border-b border-border/50">
                    <td className="py-2.5 font-medium text-foreground">{trade.symbol}</td>
                    <td className="py-2.5 text-right font-mono text-foreground">{trade.shares}</td>
                    <td className="py-2.5 text-right font-mono text-muted-foreground">${trade.entry.toFixed(2)}</td>
                    <td className="py-2.5 text-right font-mono text-foreground">${trade.current.toFixed(2)}</td>
                    <td className="py-2.5 text-right font-mono text-destructive">${trade.sl.toFixed(2)}</td>
                    <td className="py-2.5 text-right font-mono text-success">${trade.tp.toFixed(2)}</td>
                    <td
                      className={`py-2.5 text-right font-mono ${trade.pnl >= 0 ? "text-success" : "text-destructive"}`}
                    >
                      <span className="flex items-center justify-end gap-0.5">
                        {trade.pnl >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        ${Math.abs(trade.pnl).toFixed(2)} ({trade.pnlPct}%)
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

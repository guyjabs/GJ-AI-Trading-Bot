"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Wallet, Banknote, Calendar, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from "lucide-react"

const equityData = [
  { date: "9:30", value: 120000 },
  { date: "10:00", value: 121500 },
  { date: "10:30", value: 120800 },
  { date: "11:00", value: 122400 },
  { date: "11:30", value: 123100 },
  { date: "12:00", value: 122800 },
  { date: "12:30", value: 123500 },
  { date: "13:00", value: 124200 },
  { date: "13:30", value: 124582 },
]

const positions = [
  { symbol: "NVDA", shares: 25, avgCost: 850.0, current: 875.28, pnl: 632.0, pnlPct: 2.97 },
  { symbol: "AAPL", shares: 50, avgCost: 175.5, current: 178.52, pnl: 151.0, pnlPct: 1.72 },
  { symbol: "MSFT", shares: 30, avgCost: 372.0, current: 378.91, pnl: 207.3, pnlPct: 1.86 },
  { symbol: "META", shares: 15, avgCost: 498.0, current: 505.75, pnl: 116.25, pnlPct: 1.56 },
]

const recentTrades = [
  { symbol: "TSLA", type: "sell", shares: 10, price: 248.5, pnl: 245.0, time: "12:45 PM" },
  { symbol: "GOOGL", type: "buy", shares: 20, price: 141.8, pnl: null, time: "11:32 AM" },
  { symbol: "AMD", type: "sell", shares: 40, price: 178.25, pnl: -89.6, time: "10:15 AM" },
  { symbol: "SPY", type: "buy", shares: 15, price: 512.34, pnl: null, time: "09:45 AM" },
]

export function TradingView() {
  return (
    <div className="space-y-4">
      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-md">
                <Wallet className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Total Equity</p>
                <p className="text-lg font-semibold font-mono text-foreground">$124,582</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success/10 rounded-md">
                <Banknote className="w-4 h-4 text-success" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Cash Available</p>
                <p className="text-lg font-semibold font-mono text-foreground">$34,218</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent rounded-md">
                <TrendingUp className="w-4 h-4 text-accent-foreground" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Buying Power</p>
                <p className="text-lg font-semibold font-mono text-foreground">$68,436</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-md">
                <Calendar className="w-4 h-4 text-amber-600" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Day Trades Left</p>
                <p className="text-lg font-semibold font-mono text-foreground">2 / 3</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Equity Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Portfolio Equity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData}>
                <defs>
                  <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#28a745" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#28a745" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#6b7280" />
                <YAxis
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  domain={["dataMin - 1000", "dataMax + 1000"]}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    backgroundColor: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: 6,
                  }}
                  formatter={(value: number) => [`$${value.toLocaleString()}`, "Equity"]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#28a745"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorEquity)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Tables Row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Active Positions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Active Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 font-medium text-muted-foreground">Symbol</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">Shares</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">Avg Cost</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">Current</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.symbol} className="border-b border-border/50">
                      <td className="py-2 font-medium text-foreground">{pos.symbol}</td>
                      <td className="py-2 text-right font-mono text-foreground">{pos.shares}</td>
                      <td className="py-2 text-right font-mono text-muted-foreground">${pos.avgCost.toFixed(2)}</td>
                      <td className="py-2 text-right font-mono text-foreground">${pos.current.toFixed(2)}</td>
                      <td className={`py-2 text-right font-mono ${pos.pnl >= 0 ? "text-success" : "text-destructive"}`}>
                        <span className="flex items-center justify-end gap-0.5">
                          {pos.pnl >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                          ${Math.abs(pos.pnl).toFixed(2)} ({pos.pnlPct}%)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Recent Trades */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Recent Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 font-medium text-muted-foreground">Symbol</th>
                    <th className="text-center py-2 font-medium text-muted-foreground">Type</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">Shares</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">Price</th>
                    <th className="text-right py-2 font-medium text-muted-foreground">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((trade, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2 font-medium text-foreground">{trade.symbol}</td>
                      <td className="py-2 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            trade.type === "buy" ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
                          }`}
                        >
                          {trade.type === "buy" ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          {trade.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 text-right font-mono text-foreground">{trade.shares}</td>
                      <td className="py-2 text-right font-mono text-foreground">${trade.price.toFixed(2)}</td>
                      <td
                        className={`py-2 text-right font-mono ${
                          trade.pnl === null
                            ? "text-muted-foreground"
                            : trade.pnl >= 0
                              ? "text-success"
                              : "text-destructive"
                        }`}
                      >
                        {trade.pnl === null ? "—" : `${trade.pnl >= 0 ? "+" : ""}$${trade.pnl.toFixed(2)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

"use client"

import { useState } from "react"
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, PieChart, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

const portfolioData = [
  { time: "09:30", value: 124000, stocks: 95000, crypto: 29000 },
  { time: "10:00", value: 124800, stocks: 95500, crypto: 29300 },
  { time: "10:30", value: 125200, stocks: 95800, crypto: 29400 },
  { time: "11:00", value: 124600, stocks: 95200, crypto: 29400 },
  { time: "11:30", value: 125800, stocks: 96200, crypto: 29600 },
  { time: "12:00", value: 126400, stocks: 96800, crypto: 29600 },
  { time: "12:30", value: 126200, stocks: 96600, crypto: 29600 },
  { time: "13:00", value: 127100, stocks: 97300, crypto: 29800 },
  { time: "13:30", value: 127400, stocks: 97500, crypto: 29900 },
  { time: "14:00", value: 127432, stocks: 97532, crypto: 29900 },
]

const holdings = [
  { symbol: "NVDA", name: "NVIDIA Corp", shares: 45, value: 39387.6, change: 4.21, allocation: 30.9 },
  { symbol: "AAPL", name: "Apple Inc", shares: 120, value: 21410.4, change: 1.33, allocation: 16.8 },
  { symbol: "MSFT", name: "Microsoft", shares: 35, value: 13261.85, change: 1.1, allocation: 10.4 },
  { symbol: "BTC", name: "Bitcoin", shares: 0.28, value: 18995.9, change: 1.87, allocation: 14.9 },
  { symbol: "ETH", name: "Ethereum", shares: 3.15, value: 10888.86, change: 2.65, allocation: 8.5 },
  { symbol: "SOL", name: "Solana", shares: 70, value: 9986.9, change: 3.81, allocation: 7.8 },
]

const stats = [
  { label: "Total Value", value: "$127,432.89", change: "+2.61%", positive: true, icon: Wallet },
  { label: "Day's P/L", value: "+$3,241.56", change: "+2.61%", positive: true, icon: TrendingUp },
  { label: "Stocks", value: "$97,532.00", change: "+2.43%", positive: true, icon: PieChart },
  { label: "Crypto", value: "$29,900.89", change: "+3.12%", positive: true, icon: Activity },
]

export function PortfolioOverview() {
  const [chartView, setChartView] = useState("total")

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium flex items-center gap-2">
            <span className="text-primary">{">>"}</span>
            Portfolio Overview
          </CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            Live
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {stats.map((stat) => (
            <div key={stat.label} className="p-3 rounded-md bg-secondary/50 border border-border">
              <div className="flex items-center gap-2 mb-1">
                <stat.icon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">{stat.label}</span>
              </div>
              <div className="text-lg font-bold text-foreground">{stat.value}</div>
              <div
                className={cn("flex items-center gap-1 text-xs", stat.positive ? "text-primary" : "text-destructive")}
              >
                {stat.positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                {stat.change}
              </div>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="space-y-3">
          <Tabs value={chartView} onValueChange={setChartView}>
            <TabsList className="bg-secondary/50 border border-border">
              <TabsTrigger
                value="total"
                className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                Total
              </TabsTrigger>
              <TabsTrigger
                value="stocks"
                className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                Stocks
              </TabsTrigger>
              <TabsTrigger
                value="crypto"
                className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                Crypto
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={portfolioData}>
                <defs>
                  <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.75 0.18 160)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="oklch(0.75 0.18 160)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="time"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "oklch(0.6 0.02 260)", fontSize: 10 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "oklch(0.6 0.02 260)", fontSize: 10 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  domain={["dataMin - 1000", "dataMax + 1000"]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "oklch(0.16 0.008 260)",
                    border: "1px solid oklch(0.25 0.01 260)",
                    borderRadius: "6px",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "oklch(0.6 0.02 260)" }}
                  itemStyle={{ color: "oklch(0.75 0.18 160)" }}
                  formatter={(value: number) => [`$${value.toLocaleString()}`, "Value"]}
                />
                <Area
                  type="monotone"
                  dataKey={chartView === "total" ? "value" : chartView}
                  stroke="oklch(0.75 0.18 160)"
                  strokeWidth={2}
                  fill="url(#portfolioGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Holdings Table */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-muted-foreground">Top Holdings</div>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-secondary/30">
                <tr className="text-muted-foreground">
                  <th className="text-left p-2 font-medium">Asset</th>
                  <th className="text-right p-2 font-medium hidden sm:table-cell">Qty</th>
                  <th className="text-right p-2 font-medium">Value</th>
                  <th className="text-right p-2 font-medium">Change</th>
                  <th className="text-right p-2 font-medium hidden md:table-cell">Alloc</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {holdings.map((holding) => (
                  <tr key={holding.symbol} className="hover:bg-secondary/20">
                    <td className="p-2">
                      <div className="font-medium text-foreground">{holding.symbol}</div>
                      <div className="text-muted-foreground hidden sm:block">{holding.name}</div>
                    </td>
                    <td className="p-2 text-right text-muted-foreground hidden sm:table-cell">{holding.shares}</td>
                    <td className="p-2 text-right text-foreground">${holding.value.toLocaleString()}</td>
                    <td className={cn("p-2 text-right", holding.change >= 0 ? "text-primary" : "text-destructive")}>
                      {holding.change >= 0 ? "+" : ""}
                      {holding.change}%
                    </td>
                    <td className="p-2 text-right text-muted-foreground hidden md:table-cell">{holding.allocation}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

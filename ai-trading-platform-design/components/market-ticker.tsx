"use client"

import { useEffect, useState } from "react"
import { TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

const tickerData = [
  { symbol: "AAPL", price: 178.42, change: 2.34, changePercent: 1.33 },
  { symbol: "NVDA", price: 875.28, change: 12.45, changePercent: 1.44 },
  { symbol: "TSLA", price: 242.68, change: -3.21, changePercent: -1.31 },
  { symbol: "MSFT", price: 378.91, change: 4.12, changePercent: 1.1 },
  { symbol: "BTC", price: 67842.5, change: 1245.3, changePercent: 1.87 },
  { symbol: "ETH", price: 3456.78, change: 89.23, changePercent: 2.65 },
  { symbol: "GOOGL", price: 141.23, change: 1.87, changePercent: 1.34 },
  { symbol: "AMZN", price: 178.34, change: -2.12, changePercent: -1.18 },
  { symbol: "META", price: 485.92, change: 8.45, changePercent: 1.77 },
  { symbol: "SOL", price: 142.67, change: 5.23, changePercent: 3.81 },
]

export function MarketTicker() {
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setOffset((prev) => (prev + 1) % 100)
    }, 50)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative overflow-hidden bg-card border border-border rounded-lg">
      <div className="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-card to-transparent z-10" />
      <div className="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-card to-transparent z-10" />

      <div
        className="flex items-center gap-8 py-3 px-4 whitespace-nowrap"
        style={{ transform: `translateX(-${offset}px)` }}
      >
        {[...tickerData, ...tickerData].map((item, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-sm font-medium text-foreground">{item.symbol}</span>
            <span className="text-sm text-muted-foreground">
              ${item.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span
              className={cn(
                "flex items-center gap-1 text-xs font-medium",
                item.change >= 0 ? "text-primary" : "text-destructive",
              )}
            >
              {item.change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {item.change >= 0 ? "+" : ""}
              {item.changePercent.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

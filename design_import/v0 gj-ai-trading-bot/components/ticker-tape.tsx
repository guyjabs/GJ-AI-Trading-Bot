import { TrendingUp, TrendingDown } from "lucide-react"

const tickers = [
  { symbol: "AAPL", price: "178.52", change: "+1.23", positive: true },
  { symbol: "MSFT", price: "378.91", change: "+2.45", positive: true },
  { symbol: "GOOGL", price: "141.80", change: "-0.89", positive: false },
  { symbol: "AMZN", price: "178.25", change: "+3.12", positive: true },
  { symbol: "NVDA", price: "875.28", change: "+12.45", positive: true },
  { symbol: "TSLA", price: "248.50", change: "-4.32", positive: false },
  { symbol: "META", price: "505.75", change: "+5.67", positive: true },
  { symbol: "SPY", price: "512.34", change: "+1.89", positive: true },
]

export function TickerTape() {
  return (
    <div className="h-8 bg-secondary border-b border-border overflow-hidden shrink-0">
      <div className="flex ticker-animate whitespace-nowrap">
        {[...tickers, ...tickers].map((ticker, i) => (
          <div key={`${ticker.symbol}-${i}`} className="flex items-center gap-1.5 px-4 h-8">
            <span className="text-[12px] font-medium text-foreground">{ticker.symbol}</span>
            <span className="text-[12px] font-mono text-foreground">${ticker.price}</span>
            <span
              className={`flex items-center gap-0.5 text-[11px] font-mono ${
                ticker.positive ? "text-success" : "text-destructive"
              }`}
            >
              {ticker.positive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {ticker.change}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

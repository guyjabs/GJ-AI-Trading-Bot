import { Maximize2, TrendingUp, TrendingDown, AlertCircle, CheckCircle, Search, Bot } from "lucide-react"

const activities = [
  {
    id: 1,
    type: "buy",
    symbol: "NVDA",
    action: "Bought 10 shares",
    price: "$875.28",
    time: "2 min ago",
    progress: 100,
  },
  {
    id: 2,
    type: "analysis",
    symbol: "AAPL",
    action: "Analyzing momentum",
    time: "5 min ago",
    progress: 75,
    steps: ["Data collected", "Pattern detected", "Calculating entry..."],
  },
  {
    id: 3,
    type: "sell",
    symbol: "TSLA",
    action: "Sold 5 shares",
    price: "$248.50",
    time: "12 min ago",
    progress: 100,
    pnl: "+$124.50",
  },
  {
    id: 4,
    type: "alert",
    symbol: "META",
    action: "Stop loss triggered",
    time: "18 min ago",
    progress: 100,
  },
  {
    id: 5,
    type: "scan",
    symbol: "Market",
    action: "Scanning for opportunities",
    time: "25 min ago",
    progress: 45,
    steps: ["Scanning gappers", "Checking momentum"],
  },
]

function getActivityIcon(type: string) {
  switch (type) {
    case "buy":
      return <TrendingUp className="w-4 h-4 text-success" />
    case "sell":
      return <TrendingDown className="w-4 h-4 text-destructive" />
    case "alert":
      return <AlertCircle className="w-4 h-4 text-amber-500" />
    case "analysis":
      return <Bot className="w-4 h-4 text-primary" />
    case "scan":
      return <Search className="w-4 h-4 text-primary" />
    default:
      return <CheckCircle className="w-4 h-4 text-muted-foreground" />
  }
}

export function ActivitySidebar() {
  return (
    <aside className="w-[280px] bg-card border-l border-border flex flex-col">
      {/* Header */}
      <div className="h-14 px-4 border-b border-border flex items-center justify-between shrink-0">
        <h2 className="font-semibold text-[13px] text-foreground">Activity Log</h2>
        <button className="p-1.5 hover:bg-muted rounded-md transition-colors">
          <Maximize2 className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Activity List */}
      <div className="flex-1 overflow-auto custom-scrollbar p-3 space-y-2">
        {activities.map((activity) => (
          <div key={activity.id} className="p-3 bg-muted/50 rounded-md border border-border/50">
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5">{getActivityIcon(activity.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-[12px] text-foreground">{activity.symbol}</span>
                  <span className="text-[10px] text-muted-foreground">{activity.time}</span>
                </div>
                <p className="text-[12px] text-muted-foreground mt-0.5">{activity.action}</p>
                {activity.price && (
                  <p className="text-[11px] font-mono text-foreground mt-1">
                    @ {activity.price}
                    {activity.pnl && <span className="ml-2 text-success">{activity.pnl}</span>}
                  </p>
                )}
                {activity.steps && (
                  <div className="mt-2 space-y-1">
                    {activity.steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-1.5">
                        <CheckCircle className="w-3 h-3 text-success" />
                        <span className="text-[10px] text-muted-foreground">{step}</span>
                      </div>
                    ))}
                  </div>
                )}
                {activity.progress < 100 && (
                  <div className="mt-2 h-1 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${activity.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}

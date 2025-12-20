import { Circle, Settings } from "lucide-react"

export function ContentHeader() {
  return (
    <header className="h-14 bg-card border-b border-border px-4 flex items-center justify-between shrink-0">
      {/* Left: Market Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Circle className="w-2.5 h-2.5 fill-success text-success" />
          <span className="text-[13px] font-medium text-foreground">Market Open</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <span className="text-[12px] text-muted-foreground">NYSE · NASDAQ</span>
      </div>

      {/* Center: Balance & P&L */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Balance</p>
          <p className="text-sm font-semibold font-mono text-foreground">$124,582.45</p>
        </div>
        <div className="text-center">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Day P&L</p>
          <p className="text-sm font-semibold font-mono text-success">+$1,234.56</p>
        </div>
        <div className="text-center">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Total P&L</p>
          <p className="text-sm font-semibold font-mono text-success">+$8,921.30</p>
        </div>
      </div>

      {/* Right: Bot Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-success/10 rounded-full">
          <Circle className="w-2 h-2 fill-success text-success animate-pulse" />
          <span className="text-[12px] font-medium text-success">Bot Running</span>
        </div>
        <select className="text-[12px] px-2 py-1.5 bg-muted border border-border rounded-md text-foreground">
          <option>Swing Mode</option>
          <option>Day Mode</option>
        </select>
        <button className="p-1.5 hover:bg-muted rounded-md transition-colors">
          <Settings className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </header>
  )
}

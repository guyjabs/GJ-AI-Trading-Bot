"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Shield, AlertTriangle, Lock, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

const riskMetrics = [
  { label: "Portfolio Risk Score", value: 34, max: 100, status: "low", color: "bg-primary" },
  { label: "Daily VaR (95%)", value: 2.4, max: 10, status: "safe", color: "bg-primary" },
  { label: "Max Drawdown", value: 8.2, max: 25, status: "safe", color: "bg-accent" },
  { label: "Sharpe Ratio", value: 1.82, max: 3, status: "good", color: "bg-primary" },
]

const protectionRules = [
  { rule: "Stop-Loss Protection", status: "active", detail: "-5% per position", icon: Shield },
  { rule: "Daily Loss Limit", status: "active", detail: "-3% portfolio max", icon: Lock },
  { rule: "Position Size Limit", status: "active", detail: "10% max per asset", icon: CheckCircle2 },
  { rule: "Sector Concentration", status: "warning", detail: "Tech at 45%", icon: AlertTriangle },
]

const recentAlerts = [
  { time: "14:23", type: "info", message: "Stop-loss adjusted for TSLA (-5.2%)" },
  { time: "13:45", type: "success", message: "Risk rebalancing completed" },
  { time: "11:12", type: "warning", message: "High volatility detected in crypto" },
  { time: "09:30", type: "info", message: "Market open - all systems nominal" },
]

export function RiskManagement() {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "text-primary"
      case "warning":
        return "text-warning"
      case "danger":
        return "text-destructive"
      default:
        return "text-muted-foreground"
    }
  }

  const getAlertColor = (type: string) => {
    switch (type) {
      case "success":
        return "text-primary border-l-primary"
      case "warning":
        return "text-warning border-l-warning"
      case "danger":
        return "text-destructive border-l-destructive"
      default:
        return "text-accent border-l-accent"
    }
  }

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium flex items-center gap-2">
            <span className="text-accent">{">>"}</span>
            Risk Management
          </CardTitle>
          <Badge variant="outline" className="text-xs border-primary/50 text-primary">
            <Shield className="h-3 w-3 mr-1" />
            Protected
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Risk Metrics */}
        <div className="grid grid-cols-2 gap-3">
          {riskMetrics.map((metric) => (
            <div key={metric.label} className="p-3 rounded-md bg-secondary/30 border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">{metric.label}</span>
                <span
                  className={cn(
                    "text-xs px-1.5 py-0.5 rounded",
                    metric.status === "low" || metric.status === "safe" || metric.status === "good"
                      ? "bg-primary/20 text-primary"
                      : "bg-warning/20 text-warning",
                  )}
                >
                  {metric.status.toUpperCase()}
                </span>
              </div>
              <div className="text-xl font-bold text-foreground mb-1">
                {metric.value}
                {metric.label.includes("Ratio") ? "" : "%"}
              </div>
              <Progress value={(metric.value / metric.max) * 100} className={cn("h-1.5", metric.color)} />
            </div>
          ))}
        </div>

        {/* Protection Rules */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Lock className="h-3.5 w-3.5" />
            Capital Protection Rules
          </div>
          <div className="space-y-1.5">
            {protectionRules.map((rule) => (
              <div
                key={rule.rule}
                className="flex items-center justify-between p-2.5 rounded-md bg-secondary/20 border border-border"
              >
                <div className="flex items-center gap-2">
                  <rule.icon className={cn("h-4 w-4", getStatusColor(rule.status))} />
                  <div>
                    <div className="text-xs font-medium text-foreground">{rule.rule}</div>
                    <div className="text-xs text-muted-foreground">{rule.detail}</div>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    rule.status === "active" ? "border-primary/50 text-primary" : "border-warning/50 text-warning",
                  )}
                >
                  {rule.status === "active" ? "ACTIVE" : "WARNING"}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <AlertTriangle className="h-3.5 w-3.5" />
            Recent Alerts
          </div>
          <div className="space-y-1 max-h-[120px] overflow-y-auto">
            {recentAlerts.map((alert, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-start gap-2 p-2 rounded-r-md bg-secondary/20 border-l-2 text-xs",
                  getAlertColor(alert.type),
                )}
              >
                <span className="text-muted-foreground whitespace-nowrap">{alert.time}</span>
                <span className="text-foreground">{alert.message}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

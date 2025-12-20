"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts"
import { TrendingUp, Clock, Brain } from "lucide-react"

const allocationData = [
  { date: "Mon", tech: 40, finance: 25, health: 20, energy: 15 },
  { date: "Tue", tech: 45, finance: 22, health: 18, energy: 15 },
  { date: "Wed", tech: 42, finance: 28, health: 17, energy: 13 },
  { date: "Thu", tech: 48, finance: 24, health: 16, energy: 12 },
  { date: "Fri", tech: 50, finance: 22, health: 15, energy: 13 },
]

const pieData = [
  { name: "Technology", value: 50, color: "#0066cc" },
  { name: "Finance", value: 22, color: "#28a745" },
  { name: "Healthcare", value: 15, color: "#6366f1" },
  { name: "Energy", value: 13, color: "#f59e0b" },
]

const timeline = [
  {
    time: "09:32 AM",
    title: "Increased Tech Allocation",
    reason: "Strong earnings from NVDA and AAPL driving sector momentum. AI sentiment analysis shows 78% positive.",
  },
  {
    time: "10:15 AM",
    title: "Reduced Energy Exposure",
    reason: "Oil futures declining. Reallocated 5% from XOM to semiconductor positions.",
  },
  {
    time: "11:45 AM",
    title: "Added Healthcare Hedge",
    reason: "Market volatility increasing. Added defensive JNJ position for portfolio balance.",
  },
]

export function StrategyView() {
  return (
    <div className="space-y-4">
      {/* Top Row: Chart + Allocation */}
      <div className="grid grid-cols-3 gap-4">
        {/* Allocation Over Time Chart */}
        <Card className="col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Strategy Allocation Over Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={allocationData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#6b7280" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#6b7280" unit="%" />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      backgroundColor: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: 6,
                    }}
                  />
                  <Line type="monotone" dataKey="tech" stroke="#0066cc" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="finance" stroke="#28a745" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="health" stroke="#6366f1" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="energy" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Current Allocation Pie */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Current Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[160px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={65}
                    dataKey="value"
                    paddingAngle={2}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      backgroundColor: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: 6,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1.5">
              {pieData.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: item.color }} />
                  <span className="text-[11px] text-muted-foreground truncate">
                    {item.name} ({item.value}%)
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy Timeline */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary" />
            AI Strategy Decisions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {timeline.map((item, i) => (
              <div key={i} className="flex gap-3 p-3 bg-muted/50 rounded-md border border-border/50">
                <div className="flex items-center gap-1.5 text-muted-foreground shrink-0">
                  <Clock className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-mono">{item.time}</span>
                </div>
                <div>
                  <h4 className="text-[13px] font-medium text-foreground">{item.title}</h4>
                  <p className="text-[12px] text-muted-foreground mt-0.5">{item.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

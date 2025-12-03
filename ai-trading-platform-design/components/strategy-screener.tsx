"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TrendingUp, BarChart3, DollarSign, Brain, ArrowRight, Sparkles, Target, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

const strategies = {
  momentum: [
    { symbol: "NVDA", score: 94, signal: "STRONG BUY", rsi: 68, macd: "Bullish", volume: "+145%" },
    { symbol: "AMD", score: 87, signal: "BUY", rsi: 62, macd: "Bullish", volume: "+89%" },
    { symbol: "SMCI", score: 82, signal: "BUY", rsi: 58, macd: "Neutral", volume: "+234%" },
    { symbol: "ARM", score: 78, signal: "BUY", rsi: 55, macd: "Bullish", volume: "+67%" },
  ],
  growth: [
    { symbol: "META", score: 91, peRatio: 25.4, revenue: "+23%", eps: "+42%", guidance: "Raised" },
    { symbol: "GOOGL", score: 88, peRatio: 23.1, revenue: "+15%", eps: "+31%", guidance: "Maintained" },
    { symbol: "AMZN", score: 85, peRatio: 45.2, revenue: "+12%", eps: "+28%", guidance: "Raised" },
    { symbol: "CRM", score: 79, peRatio: 52.3, revenue: "+11%", eps: "+19%", guidance: "Maintained" },
  ],
  value: [
    { symbol: "BRK.B", score: 89, pbRatio: 1.4, dividend: "0%", fcf: "+8%", moat: "Wide" },
    { symbol: "JPM", score: 84, pbRatio: 1.7, dividend: "2.4%", fcf: "+12%", moat: "Wide" },
    { symbol: "JNJ", score: 81, pbRatio: 4.2, dividend: "3.1%", fcf: "+6%", moat: "Wide" },
    { symbol: "PG", score: 77, pbRatio: 7.8, dividend: "2.5%", fcf: "+4%", moat: "Wide" },
  ],
}

const strategyMeta = {
  momentum: { icon: TrendingUp, color: "text-primary", description: "High velocity price movement" },
  growth: { icon: BarChart3, color: "text-accent", description: "Strong earnings expansion" },
  value: { icon: DollarSign, color: "text-chart-3", description: "Undervalued fundamentals" },
}

export function StrategyScreener() {
  const [activeStrategy, setActiveStrategy] = useState("momentum")

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-primary"
    if (score >= 80) return "text-accent"
    if (score >= 70) return "text-chart-3"
    return "text-muted-foreground"
  }

  const getSignalBadge = (signal: string) => {
    if (signal === "STRONG BUY") return "bg-primary/20 text-primary border-primary/30"
    if (signal === "BUY") return "bg-accent/20 text-accent border-accent/30"
    return "bg-secondary text-muted-foreground"
  }

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium flex items-center gap-2">
            <span className="text-primary">{">>"}</span>
            Strategy Screener
            <Badge variant="outline" className="text-xs border-accent/50 text-accent ml-2">
              <Brain className="h-3 w-3 mr-1" />
              ML Powered
            </Badge>
          </CardTitle>
          <Button variant="ghost" size="sm" className="text-xs text-muted-foreground hover:text-foreground">
            View All <ArrowRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs value={activeStrategy} onValueChange={setActiveStrategy}>
          <TabsList className="w-full bg-secondary/50 border border-border">
            {Object.entries(strategyMeta).map(([key, meta]) => (
              <TabsTrigger
                key={key}
                value={key}
                className="flex-1 text-xs data-[state=active]:bg-card data-[state=active]:text-foreground gap-1"
              >
                <meta.icon className={cn("h-3 w-3", meta.color)} />
                <span className="capitalize hidden sm:inline">{key}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {Object.entries(strategies).map(([strategyKey, stocks]) => (
            <TabsContent key={strategyKey} value={strategyKey} className="mt-4">
              <div className="mb-3 p-2 rounded bg-secondary/30 border border-border">
                <div className="flex items-center gap-2 text-xs">
                  <Sparkles className="h-3 w-3 text-primary" />
                  <span className="text-muted-foreground">
                    {strategyMeta[strategyKey as keyof typeof strategyMeta].description}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                {stocks.map((stock, i) => (
                  <div
                    key={stock.symbol}
                    className="p-3 rounded-md bg-secondary/20 border border-border hover:border-primary/30 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          <Target className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-foreground">{stock.symbol}</span>
                        </div>
                        {"signal" in stock && (
                          <Badge variant="outline" className={cn("text-xs", getSignalBadge(stock.signal))}>
                            {stock.signal}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={cn("text-lg font-bold", getScoreColor(stock.score))}>{stock.score}</span>
                        <span className="text-xs text-muted-foreground">/100</span>
                      </div>
                    </div>

                    <Progress value={stock.score} className="h-1.5 mb-2" />

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      {strategyKey === "momentum" && "rsi" in stock && (
                        <>
                          <div>
                            <span className="text-muted-foreground">RSI: </span>
                            <span className="text-foreground">{stock.rsi}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">MACD: </span>
                            <span className="text-primary">{stock.macd}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Vol: </span>
                            <span className="text-primary">{stock.volume}</span>
                          </div>
                        </>
                      )}
                      {strategyKey === "growth" && "revenue" in stock && (
                        <>
                          <div>
                            <span className="text-muted-foreground">P/E: </span>
                            <span className="text-foreground">{stock.peRatio}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Rev: </span>
                            <span className="text-primary">{stock.revenue}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">EPS: </span>
                            <span className="text-primary">{stock.eps}</span>
                          </div>
                        </>
                      )}
                      {strategyKey === "value" && "pbRatio" in stock && (
                        <>
                          <div>
                            <span className="text-muted-foreground">P/B: </span>
                            <span className="text-foreground">{stock.pbRatio}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Div: </span>
                            <span className="text-accent">{stock.dividend}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">FCF: </span>
                            <span className="text-primary">{stock.fcf}</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>

        {/* AI Recommendation */}
        <div className="p-3 rounded-md bg-primary/10 border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium text-primary">AI Recommendation</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Based on current market conditions and your portfolio, consider adding{" "}
            <span className="text-primary font-medium">NVDA</span> to capture momentum in the AI sector.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

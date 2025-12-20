"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Brain, TrendingUp, TrendingDown, Newspaper, ThumbsUp, ThumbsDown, Minus, ExternalLink } from "lucide-react"

const sentimentData = {
  positive: 62,
  neutral: 24,
  negative: 14,
}

const predictions = [
  { symbol: "NVDA", sentiment: "bullish", confidence: 85, reason: "Strong AI chip demand, datacenter growth" },
  { symbol: "AAPL", sentiment: "bullish", confidence: 72, reason: "iPhone 16 sales exceeding expectations" },
  { symbol: "TSLA", sentiment: "bearish", confidence: 68, reason: "EV market slowdown, margin pressure" },
  { symbol: "META", sentiment: "bullish", confidence: 78, reason: "Ad revenue growth, Threads momentum" },
  { symbol: "GOOGL", sentiment: "neutral", confidence: 55, reason: "Mixed signals on AI integration" },
]

const news = [
  {
    title: "NVIDIA Reports Record Q3 Revenue on AI Chip Demand",
    source: "Reuters",
    time: "2h ago",
    sentiment: "positive",
  },
  {
    title: "Federal Reserve Signals Potential Rate Cut in December",
    source: "Bloomberg",
    time: "3h ago",
    sentiment: "positive",
  },
  {
    title: "Tesla Faces Increased Competition in Chinese EV Market",
    source: "WSJ",
    time: "4h ago",
    sentiment: "negative",
  },
  {
    title: "Apple Expands AI Features Across Product Lineup",
    source: "TechCrunch",
    time: "5h ago",
    sentiment: "positive",
  },
  {
    title: "Oil Prices Decline on Demand Concerns",
    source: "CNBC",
    time: "6h ago",
    sentiment: "negative",
  },
]

function getSentimentIcon(sentiment: string) {
  switch (sentiment) {
    case "bullish":
    case "positive":
      return <TrendingUp className="w-4 h-4 text-success" />
    case "bearish":
    case "negative":
      return <TrendingDown className="w-4 h-4 text-destructive" />
    default:
      return <Minus className="w-4 h-4 text-amber-500" />
  }
}

function getSentimentColor(sentiment: string) {
  switch (sentiment) {
    case "bullish":
    case "positive":
      return "text-success"
    case "bearish":
    case "negative":
      return "text-destructive"
    default:
      return "text-amber-500"
  }
}

export function ResearchView() {
  return (
    <div className="space-y-4">
      {/* Sentiment + Predictions Row */}
      <div className="grid grid-cols-3 gap-4">
        {/* Sentiment Gauge */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" />
              Market Sentiment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* Sentiment Bar */}
              <div className="h-3 flex rounded-full overflow-hidden">
                <div className="bg-success" style={{ width: `${sentimentData.positive}%` }} />
                <div className="bg-amber-400" style={{ width: `${sentimentData.neutral}%` }} />
                <div className="bg-destructive" style={{ width: `${sentimentData.negative}%` }} />
              </div>

              {/* Legend */}
              <div className="flex justify-between text-[11px]">
                <div className="flex items-center gap-1.5">
                  <ThumbsUp className="w-3.5 h-3.5 text-success" />
                  <span className="text-muted-foreground">Positive</span>
                  <span className="font-semibold text-foreground">{sentimentData.positive}%</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Minus className="w-3.5 h-3.5 text-amber-500" />
                  <span className="text-muted-foreground">Neutral</span>
                  <span className="font-semibold text-foreground">{sentimentData.neutral}%</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <ThumbsDown className="w-3.5 h-3.5 text-destructive" />
                  <span className="text-muted-foreground">Negative</span>
                  <span className="font-semibold text-foreground">{sentimentData.negative}%</span>
                </div>
              </div>

              {/* Overall */}
              <div className="pt-2 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-muted-foreground">Overall Outlook</span>
                  <span className="flex items-center gap-1.5 text-[13px] font-semibold text-success">
                    <TrendingUp className="w-4 h-4" />
                    Bullish
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Predictions */}
        <Card className="col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" />
              AI Predictions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {predictions.map((pred) => (
                <div
                  key={pred.symbol}
                  className="flex items-center gap-3 p-2 bg-muted/50 rounded-md border border-border/50"
                >
                  <div className="w-14 shrink-0">
                    <span className="font-semibold text-[13px] text-foreground">{pred.symbol}</span>
                  </div>
                  <div className="flex items-center gap-1.5 w-20 shrink-0">
                    {getSentimentIcon(pred.sentiment)}
                    <span className={`text-[12px] font-medium capitalize ${getSentimentColor(pred.sentiment)}`}>
                      {pred.sentiment}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            pred.sentiment === "bullish"
                              ? "bg-success"
                              : pred.sentiment === "bearish"
                                ? "bg-destructive"
                                : "bg-amber-500"
                          }`}
                          style={{ width: `${pred.confidence}%` }}
                        />
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground w-8">{pred.confidence}%</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-muted-foreground flex-1 truncate">{pred.reason}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* News Feed */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-primary" />
            AI-Analyzed News Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {news.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 bg-muted/50 rounded-md border border-border/50 hover:bg-muted transition-colors cursor-pointer group"
              >
                <div className="shrink-0">{getSentimentIcon(item.sentiment)}</div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-[13px] font-medium text-foreground group-hover:text-primary transition-colors">
                    {item.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-muted-foreground">{item.source}</span>
                    <span className="text-[11px] text-muted-foreground">•</span>
                    <span className="text-[11px] text-muted-foreground">{item.time}</span>
                  </div>
                </div>
                <ExternalLink className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

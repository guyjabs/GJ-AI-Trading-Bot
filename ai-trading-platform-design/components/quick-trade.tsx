"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { ArrowUpDown, Zap, ShieldCheck, AlertTriangle } from "lucide-react"

const popularAssets = [
  { symbol: "NVDA", price: 875.28 },
  { symbol: "AAPL", price: 178.42 },
  { symbol: "BTC", price: 67842.5 },
  { symbol: "ETH", price: 3456.78 },
]

export function QuickTrade() {
  const [orderType, setOrderType] = useState("market")
  const [selectedAsset, setSelectedAsset] = useState("")
  const [quantity, setQuantity] = useState("")
  const [limitPrice, setLimitPrice] = useState("")

  return (
    <Card className="border-border bg-card h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium flex items-center gap-2">
            <span className="text-accent">{">>"}</span>
            Quick Trade
          </CardTitle>
          <Badge variant="outline" className="text-xs border-primary/50 text-primary">
            <Zap className="h-3 w-3 mr-1" />
            AI Optimized
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="buy" className="w-full">
          <TabsList className="w-full bg-secondary/50 border border-border">
            <TabsTrigger
              value="buy"
              className="flex-1 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              BUY
            </TabsTrigger>
            <TabsTrigger
              value="sell"
              className="flex-1 text-xs data-[state=active]:bg-destructive data-[state=active]:text-destructive-foreground"
            >
              SELL
            </TabsTrigger>
          </TabsList>

          <TabsContent value="buy" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Asset</Label>
              <Select value={selectedAsset} onValueChange={setSelectedAsset}>
                <SelectTrigger className="bg-secondary/50 border-border">
                  <SelectValue placeholder="Select asset..." />
                </SelectTrigger>
                <SelectContent>
                  {popularAssets.map((asset) => (
                    <SelectItem key={asset.symbol} value={asset.symbol}>
                      <div className="flex items-center justify-between w-full gap-4">
                        <span>{asset.symbol}</span>
                        <span className="text-muted-foreground">${asset.price.toLocaleString()}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Order Type</Label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={orderType === "market" ? "default" : "outline"}
                  size="sm"
                  className="text-xs"
                  onClick={() => setOrderType("market")}
                >
                  Market
                </Button>
                <Button
                  variant={orderType === "limit" ? "default" : "outline"}
                  size="sm"
                  className="text-xs"
                  onClick={() => setOrderType("limit")}
                >
                  Limit
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Quantity</Label>
                <Input
                  type="number"
                  placeholder="0"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="bg-secondary/50 border-border"
                />
              </div>
              {orderType === "limit" && (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Limit Price</Label>
                  <Input
                    type="number"
                    placeholder="$0.00"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(e.target.value)}
                    className="bg-secondary/50 border-border"
                  />
                </div>
              )}
            </div>

            {/* Risk Assessment */}
            <div className="p-3 rounded-md bg-primary/10 border border-primary/20">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <span className="text-xs font-medium text-primary">Risk Assessment</span>
              </div>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Position Size</span>
                  <span className="text-foreground">2.3% of portfolio</span>
                </div>
                <div className="flex justify-between">
                  <span>Stop Loss</span>
                  <span className="text-primary">-5% (Auto)</span>
                </div>
                <div className="flex justify-between">
                  <span>Risk Level</span>
                  <span className="text-primary">LOW</span>
                </div>
              </div>
            </div>

            <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground">
              <ArrowUpDown className="h-4 w-4 mr-2" />
              Execute Buy Order
            </Button>
          </TabsContent>

          <TabsContent value="sell" className="space-y-4 mt-4">
            <div className="p-4 rounded-md bg-secondary/30 border border-border text-center">
              <AlertTriangle className="h-8 w-8 text-warning mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Select a position from your portfolio to sell</p>
            </div>
          </TabsContent>
        </Tabs>

        {/* Quick Actions */}
        <div className="pt-3 border-t border-border">
          <div className="text-xs text-muted-foreground mb-2">Popular Assets</div>
          <div className="grid grid-cols-4 gap-2">
            {popularAssets.map((asset) => (
              <Button
                key={asset.symbol}
                variant="outline"
                size="sm"
                className="text-xs p-2 h-auto bg-transparent"
                onClick={() => setSelectedAsset(asset.symbol)}
              >
                {asset.symbol}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

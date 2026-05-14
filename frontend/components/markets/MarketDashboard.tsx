"use client"

import { useEffect, useState } from "react"
import { MarketDataPoint } from "@/types/story"
import { fetchMarketData } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, TrendingDown, BarChart3, RefreshCw } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"

export function MarketDashboard() {
  const [data, setData] = useState<{
    all: MarketDataPoint[]
    gainers: MarketDataPoint[]
    losers: MarketDataPoint[]
    indices: MarketDataPoint[]
  }>({ all: [], gainers: [], losers: [], indices: [] })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setLoading(true)
      const marketData = await fetchMarketData()
      setData(marketData)
      setError(null)
    } catch {
      setError("Failed to load market data")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001"}/markets/refresh`, {
        method: "POST",
      })
      await load()
    } catch {
      // ignore
    } finally {
      setRefreshing(false)
    }
  }

  if (loading && data.all.length === 0) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5" />
            Markets
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error && data.all.length === 0) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5" />
            Markets
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-4">{error}</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.gainers.slice(0, 5).concat(data.losers.slice(0, 5)).map((m) => ({
    name: m.ticker,
    fullName: m.name,
    change: m.change_pct,
  }))

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <BarChart3 className="h-5 w-5 text-emerald-400" />
          Markets Dashboard
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Indices */}
        {data.indices.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Indices
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {data.indices.map((idx, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border/50 bg-muted/20 p-3"
                >
                  <p className="text-xs text-muted-foreground">{idx.ticker}</p>
                  <p className="text-lg font-bold">${idx.price.toFixed(2)}</p>
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-medium ${
                      idx.change_pct >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {idx.change_pct >= 0 ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {idx.change_pct >= 0 ? "+" : ""}
                    {idx.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Movers Chart */}
        {chartData.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Notable Movers (% Change)
            </h4>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 20 }}>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={50} />
                  <Tooltip
                    formatter={(value: any) => {
                      const num = Number(value)
                      return [`${num >= 0 ? '+' : ''}${num.toFixed(2)}%`, 'Change']
                    }}
                    labelFormatter={(label: any) => {
                      const item = chartData.find((d) => d.name === label)
                      return item?.fullName || label
                    }}
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="change" radius={[0, 4, 4, 0]} maxBarSize={20}>
                    {chartData.map((entry, index) => (
                      <Cell key={index} fill={entry.change >= 0 ? "#22c55e" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Top Gainers */}
        {data.gainers.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3">
              Top Gainers
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {data.gainers.slice(0, 6).map((m, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-3">
                  <div>
                    <p className="text-sm font-medium">{m.ticker}</p>
                    <p className="text-xs text-muted-foreground">{m.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">${m.price.toFixed(2)}</p>
                    <span className="text-xs text-emerald-400 font-medium">
                      +{m.change_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Losers */}
        {data.losers.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-3">
              Top Losers
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {data.losers.slice(0, 6).map((m, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-red-500/5 border border-red-500/20 p-3">
                  <div>
                    <p className="text-sm font-medium">{m.ticker}</p>
                    <p className="text-xs text-muted-foreground">{m.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">${m.price.toFixed(2)}</p>
                    <span className="text-xs text-red-400 font-medium">
                      {m.change_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

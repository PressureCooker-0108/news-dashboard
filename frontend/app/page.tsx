"use client"

import { useEffect, useState } from "react"
import { Story, MarketDataPoint, SourceDiversity } from "@/types/story"
import { fetchStories, fetchMarketData, fetchSourceDiversity, fetchTrending } from "@/lib/api"
import { Header } from "@/components/header"
import { BigStory } from "@/components/news/BigStory"
import { TopStories } from "@/components/news/TopStories"
import { SectorSection } from "@/components/news/SectorSection"
import { MarketDashboard } from "@/components/markets/MarketDashboard"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Activity,
  Globe,
  TrendingUp,
  RefreshCw,
  FileText,
  Download,
  FileDown,
  BarChart3,
  Search,
  Clock,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { downloadMarkdown, downloadJson, downloadPdf } from "@/lib/api"
import { toast } from "sonner"

const SCOLORS: Record<string, string> = {
  Markets: "emerald",
  Tech: "blue",
  Geopolitics: "red",
  Energy: "amber",
  India: "orange",
  General: "slate",
}

export default function Dashboard() {
  const [stories, setStories] = useState<Story[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [trendingData, setTrendingData] = useState<{ title: string; score: number }[]>([])
  const [now, setNow] = useState(Date.now())
  const [lastFetchedAt, setLastFetchedAt] = useState(Date.now())

  async function load() {
    try {
      setLoading(true)
      const [s, t] = await Promise.all([
        fetchStories(),
        fetchTrending(48),
      ])
      setStories(s)
      setTrendingData(t.slice(0, 10))
      setLastFetchedAt(Date.now())
      setError(null)
    } catch {
      setError("Failed to load stories")
    } finally {
      setLoading(false)
    }
  }

  // Tick clock every second for auto-refresh indicator
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(tick)
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 120000) // Refresh every 2 mins
    return () => clearInterval(interval)
  }, [])

  // Search filter
  const query = searchQuery.toLowerCase()
  const filteredStories = query
    ? stories.filter(
        (s) =>
          s.headline.toLowerCase().includes(query) ||
          s.summary.toLowerCase().includes(query) ||
          (s.sectors && s.sectors.some((sec) => sec.toLowerCase().includes(query)))
      )
    : stories

  // Sector grouping (using filtered stories for display)
  const sectorGroups: Record<string, Story[]> = {}
  const seenSectors = new Set<string>()

  for (const story of filteredStories) {
    for (const sector of story.sectors || ["General"]) {
      if (!sectorGroups[sector]) sectorGroups[sector] = []
      sectorGroups[sector].push(story)
      seenSectors.add(sector)
    }
  }

  const displayOrder = ["Markets", "Tech", "Geopolitics", "Energy", "India", "General"]
  const activeSectors = displayOrder.filter((s) => seenSectors.has(s))

  // Calculate relative time for last update
  function relativeTime(ms: number): string {
    const secs = Math.floor((Date.now() - ms) / 1000)
    if (secs < 5) return "just now"
    if (secs < 60) return `${secs}s ago`
    const mins = Math.floor(secs / 60)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    return `${hrs}h ago`
  }

  if (loading && stories.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground animate-pulse">Syncing Intel...</p>
          </div>
        </main>
      </div>
    )
  }

  if (error && stories.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <p className="text-red-400">{error}</p>
            <Button variant="outline" onClick={load}>
              <RefreshCw className="h-4 w-4 mr-2" /> Retry
            </Button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
        {stories.length === 0 && !searchQuery ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="rounded-full bg-muted p-6">
              <Activity className="h-10 w-10 text-muted-foreground" />
            </div>
            <h2 className="text-xl font-semibold">Station Idle</h2>
            <p className="text-sm text-muted-foreground max-w-md text-center">
              The pipeline is warming up. Intelligence will appear here once the first
              processing cycle completes.
            </p>
          </div>
        ) : (
          <>
            {/* Top Bar: Search + Refresh Indicator */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search stories by headline, summary, or sector..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-10 text-sm"
                />
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                <Clock className="h-3.5 w-3.5" />
                <span>Updated {relativeTime(lastFetchedAt)}</span>
              </div>
            </div>

            {/* Trending Topics Bar */}
            {trendingData.length > 0 && (
              <div className="animate-fade-in">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                    Trending Now
                  </span>
                  <div className="h-px flex-1 bg-border/60" />
                </div>
                <div className="flex flex-wrap gap-2">
                  {trendingData.slice(0, 6).map((item, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/5 border border-primary/10 text-xs font-medium text-foreground/80 hover:bg-primary/10 hover:text-primary transition-colors cursor-default"
                    >
                      <span className="text-[10px] font-bold text-primary/60">
                        {String.fromCharCode(65 + i)}
                      </span>
                      {item.title.length > 40 ? item.title.slice(0, 40) + "…" : item.title}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Filter notice */}
            {searchQuery && filteredStories.length === 0 && (
              <div className="text-center py-12">
                <Search className="h-8 w-8 mx-auto mb-3 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">
                  No stories match &ldquo;{searchQuery}&rdquo;
                </p>
                <Button variant="link" size="sm" onClick={() => setSearchQuery("")}>
                  Clear filter
                </Button>
              </div>
            )}

            {/* Big Story */}
            {filteredStories[0] && <BigStory story={filteredStories[0]} />}

            {/* Markets Dashboard */}
            <MarketDashboard />

            {/* Sector Navigation */}
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Globe className="h-5 w-5" />
                  Sector Intelligence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                  {activeSectors.map((sector) => (
                    <Link
                      key={sector}
                      href={`/sectors/${sector.toLowerCase()}`}
                      className="group relative overflow-hidden rounded-xl border border-border/50 bg-card p-4 transition-all duration-300 hover:shadow-lg hover:border-primary/30 hover:-translate-y-0.5"
                    >
                      <p className="text-2xl mb-1">
                        {sector === "Markets" && "📊"}
                        {sector === "Tech" && "💻"}
                        {sector === "Geopolitics" && "🌍"}
                        {sector === "Energy" && "⚡"}
                        {sector === "India" && "🇮🇳"}
                        {sector === "General" && "📰"}
                      </p>
                      <p className="font-semibold text-sm group-hover:text-primary transition-colors">
                        {sector}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {sectorGroups[sector]?.length || 0} stories
                      </p>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Intelligence Feed */}
            <TopStories stories={filteredStories.slice(1, 7)} />

            {/* Sector Breakdown */}
            <SectorSection stories={filteredStories} />

            {/* Export Buttons */}
            <div className="flex flex-wrap gap-3 justify-center pt-4 border-t border-border/50">
              <Button variant="outline" size="sm" onClick={() => { downloadMarkdown().catch(() => toast.error("Failed to download Markdown brief")); }}>
                <FileText className="h-4 w-4 mr-2" />
                Export Markdown Brief
              </Button>
              <Button variant="outline" size="sm" onClick={() => { downloadJson().catch(() => toast.error("Failed to download JSON export")); }}>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => { downloadPdf().catch(() => toast.error("Failed to download PDF briefing")); }}>
                <FileDown className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
            </div>
          </>
        )}
      </main>

      <footer className="border-t border-border mt-12 py-8 text-center text-xs text-muted-foreground">
        <p className="mb-2">Serious Operator News Dashboard &mdash; Intelligence Grade: Reliable</p>
        <p>Data aggregated from 16+ global news sources across 6 intelligence sectors</p>
      </footer>
    </div>
  )
}

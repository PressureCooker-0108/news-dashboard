"use client"

import { useEffect, useState } from "react"
import { Story } from "@/types/story"
import { fetchStories } from "@/lib/api"
import { Header } from "@/components/header"
import { BigStory } from "@/components/news/BigStory"
import { TopStories } from "@/components/news/TopStories"
import { SectorSection } from "@/components/news/SectorSection"

export default function Home() {
  const [stories, setStories] = useState<Story[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadStories() {
      const data = await fetchStories()
      setStories(data)
      setLoading(false)
    }

    loadStories()
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 bg-background">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <div className="text-sm font-medium text-muted-foreground tracking-widest uppercase">Syncing Intel...</div>
        </div>
      </div>
    )
  }

  if (!stories || stories.length === 0) {
    return (
      <div className="min-h-screen p-8 md:p-12 lg:p-20 max-w-7xl mx-auto space-y-12 bg-background">
        <Header />
        <div className="rounded-2xl border-2 border-dashed border-border bg-card/50 p-20 text-center">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Station Idle</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            The data pipeline is currently warming up. Check back in approximately 60 seconds for the latest global brief.
          </p>
        </div>
      </div>
    )
  }

  const bigStory = stories[0]
  const intelligenceFeed = stories.slice(1)

  return (
    <main className="min-h-screen p-8 md:p-12 lg:p-20 max-w-7xl mx-auto space-y-20 bg-background transition-colors duration-500">
      <Header />
      
      <div className="space-y-12">
        <BigStory story={bigStory} />
        
        <TopStories stories={intelligenceFeed} />

        {intelligenceFeed.length > 6 && (
          <SectorSection stories={intelligenceFeed.slice(6)} />
        )}
      </div>
      
      <footer className="pt-20 pb-10 border-t border-border/40 text-center">
        <p className="text-xs font-medium text-muted-foreground/50 tracking-widest uppercase">
          Serious Operator News Dashboard &copy; 2026
        </p>
      </footer>
    </main>
  )
}

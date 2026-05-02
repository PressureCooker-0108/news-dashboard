import { Story } from "@/types/story"

interface SectorSectionProps {
  stories: Story[]
}

export function SectorSection({ stories }: SectorSectionProps) {
  // Simple keyword-based categorization for the MVP
  const categorize = (items: Story[]) => {
    const sectors = {
      Markets: [] as Story[],
      Tech: [] as Story[],
      Geopolitics: [] as Story[],
      General: [] as Story[]
    }

    const techKeywords = ['tech', 'ai', 'semiconductor', 'chip', 'apple', 'google', 'microsoft', 'software', 'digital', 'cyber']
    const marketKeywords = ['market', 'stock', 'invest', 'economy', 'fed', 'rate', 'inflation', 'bank', 'finance', 'trading', 'oil']
    const geoKeywords = ['war', 'conflict', 'diplomacy', 'election', 'minister', 'president', 'china', 'russia', 'ukraine', 'israel', 'lebanon', 'nato', 'un']

    items.forEach(story => {
      const text = (story.headline + ' ' + story.summary).toLowerCase()
      if (techKeywords.some(k => text.includes(k))) sectors.Tech.push(story)
      else if (marketKeywords.some(k => text.includes(k))) sectors.Markets.push(story)
      else if (geoKeywords.some(k => text.includes(k))) sectors.Geopolitics.push(story)
      else sectors.General.push(story)
    })

    // Fallback: If sectors are empty, fill them with General stories to ensure UI is populated
    if (sectors.Markets.length === 0) sectors.Markets = sectors.General.splice(0, 3)
    if (sectors.Tech.length === 0) sectors.Tech = sectors.General.splice(0, 3)
    if (sectors.Geopolitics.length === 0) sectors.Geopolitics = sectors.General.splice(0, 3)

    return [
      { name: "Markets", items: sectors.Markets.slice(0, 4) },
      { name: "Tech", items: sectors.Tech.slice(0, 4) },
      { name: "Geopolitics", items: sectors.Geopolitics.slice(0, 4) }
    ]
  }

  const sections = categorize(stories)

  return (
    <section className="space-y-8">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
          Sector Breakdown
        </h3>
        <div className="h-px flex-1 ml-4 bg-border/60" />
      </div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map((sector) => (
          <div 
            key={sector.name}
            className="rounded-2xl border border-border bg-card p-8 transition-all duration-300 hover:shadow-lg"
          >
            <h4 className="mb-6 text-[10px] font-bold uppercase tracking-[0.25em] text-primary/70">
              {sector.name}
            </h4>
            {sector.items.length > 0 ? (
              <ul className="space-y-5">
                {sector.items.map((item, idx) => (
                  <li key={idx}>
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-sm leading-relaxed text-foreground/80 hover:text-primary transition-colors duration-150 font-medium line-clamp-2"
                    >
                      {item.headline}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground italic">No specific reports in this sector today.</p>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

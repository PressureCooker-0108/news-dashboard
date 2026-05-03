import { Story } from "@/types/story"

interface SectorSectionProps {
  stories: Story[]
}

export function SectorSection({ stories }: SectorSectionProps) {
  // Use backend-provided sectors instead of keyword guessing
  const categorize = (items: Story[]) => {
    const sectorMap: Record<string, Story[]> = {}

    items.forEach(story => {
      const sectors = story.sectors || ["General"]
      sectors.forEach(sector => {
        if (!sectorMap[sector]) sectorMap[sector] = []
        sectorMap[sector].push(story)
      })
    })

    // Priority order for display
    const displayOrder = ["Markets", "Tech", "Geopolitics", "Energy", "India", "General"]
    
    return displayOrder
      .filter(name => sectorMap[name] && sectorMap[name].length > 0)
      .map(name => ({
        name,
        items: sectorMap[name].slice(0, 4)
      }))
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

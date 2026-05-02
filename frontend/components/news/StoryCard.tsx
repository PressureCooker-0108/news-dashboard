import { Story } from "@/types/story"

interface StoryCardProps {
  story: Story
  className?: string
}

export function StoryCard({ story, className }: StoryCardProps) {
  const CardContent = (
    <article className={`h-full rounded-xl border border-border bg-card p-6 transition-all duration-300 hover:shadow-lg hover:border-primary/30 group ${className}`}>
      <div className="flex flex-col h-full justify-between space-y-4">
        <div className="space-y-3">
          {/* Headline */}
          <h4 className="font-semibold leading-tight text-foreground text-lg group-hover:text-primary transition-colors">
            {story.headline}
          </h4>
          
          {/* Summary */}
          <p className="text-sm leading-relaxed text-muted-foreground line-clamp-3">
            {story.summary}
          </p>
        </div>
        
        {/* Why it matters */}
        {story.why_it_matters && (
          <div className="pt-4 border-t border-border/50">
            <p className="text-xs leading-relaxed text-muted-foreground italic font-light line-clamp-2">
              <span className="font-medium not-italic text-foreground/80">Context:</span> {story.why_it_matters}
            </p>
          </div>
        )}
      </div>
    </article>
  )

  if (story.url) {
    return (
      <a href={story.url} target="_blank" rel="noopener noreferrer" className="block h-full">
        {CardContent}
      </a>
    )
  }

  return CardContent
}

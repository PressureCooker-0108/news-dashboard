import { Story } from "@/types/story"

interface BigStoryProps {
  story?: Story
}

export function BigStory({ story }: BigStoryProps) {
  if (!story) {
    return (
      <article className="rounded-xl border border-border bg-card p-8">
        <p className="text-sm text-muted-foreground">No story available</p>
      </article>
    )
  }

  const Content = (
    <article className="rounded-2xl border border-border bg-gradient-to-br from-secondary/50 to-background p-12 transition-all hover:shadow-xl hover:border-primary/20 group cursor-pointer">
      <div className="space-y-8">
        {/* Label */}
        <div className="flex items-center space-x-3">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
          </span>
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-primary">
            Critical Intelligence
          </div>
        </div>

        {/* Headline */}
        <h2 className="text-6xl font-bold leading-[1.1] text-foreground tracking-tight group-hover:text-primary transition-colors">
          {story.headline}
        </h2>

        {/* Summary */}
        <p className="text-xl leading-relaxed text-muted-foreground max-w-4xl">
          {story.summary}
        </p>

        {/* Why it matters */}
        {story.why_it_matters && (
          <div className="rounded-xl bg-background border border-border p-8 shadow-sm">
            <div className="flex flex-col space-y-2">
              <span className="text-xs font-bold uppercase tracking-widest text-foreground/40">Implication</span>
              <p className="text-lg leading-relaxed text-foreground/80 font-medium">
                {story.why_it_matters}
              </p>
            </div>
          </div>
        )}
      </div>
    </article>
  )

  if (story.url) {
    return (
      <a href={story.url} target="_blank" rel="noopener noreferrer" className="block">
        {Content}
      </a>
    )
  }

  return Content
}

import { Story } from "@/types/story"

export async function fetchStories(): Promise<Story[]> {
  try {
    const response = await fetch("http://127.0.0.1:8000/news")
    if (!response.ok) {
      throw new Error(`Failed to fetch stories: ${response.status}`)
    }
    const data = await response.json()
    return (data.stories || []).map((s: any) => ({
      headline: s.headline,
      summary: s.summary,
      why_it_matters: s.why_it_matters,
      url: s.url
    }))
  } catch (error) {
    console.error("Error fetching stories:", error)
    return []
  }
}

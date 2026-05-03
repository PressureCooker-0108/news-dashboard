import { Story } from "@/types/story"

export async function fetchStories(): Promise<Story[]> {
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001"
    const response = await fetch(`${API_URL}/news`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch stories: ${response.status}`)
    }
    
    const data = await response.json()
    
    if (!data.top_stories || data.top_stories.length === 0) {
      // Fallback if API returns empty
      return []
    }

    return data.top_stories.map((s: any) => ({
      headline: s.headline || "Details are still emerging.",
      summary: s.summary || "Details are still emerging.",
      why_it_matters: s.why_it_matters || "This is a developing story worth monitoring.",
      url: s.url,
      sectors: s.sectors || ["General"]
    }))
  } catch (error) {
    console.error("Error fetching stories:", error)
    // Return empty array to prevent UI crash
    return []
  }
}

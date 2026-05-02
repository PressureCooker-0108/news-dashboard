# Project Context: Serious Operator News Dashboard

## What this project is

This is a backend system that aggregates global news, filters noise, and presents only the most important stories in a clean, structured format.

It is NOT a traditional news website.

It is a decision-support tool that answers:

* What are the most important things happening today?
* Why do they matter?

## Target user

* Founders
* Investors
* Analysts
* Curious high-agency individuals

Users want:

* Speed
* Clarity
* Signal over noise

## Core principles

* Less is more (top 5–10 stories max)
* No clickbait
* No fluff
* High signal density

## System pipeline

1. Fetch news from RSS feeds
2. Clean and normalize articles
3. Cluster similar news into single "stories"
4. Rank stories by importance
5. Generate short summaries
6. Serve via API

## Definitions

### Article

A single news item from a source (title, link, date)

### Cluster

A group of articles covering the same story

### Story

A processed cluster with:

* One clean headline
* Summary
* Why it matters

## MVP Scope

* No authentication
* No frontend complexity
* No personalization
* No real-time streaming

## Success Criteria

* API returns top 5–10 meaningful stories
* Duplicate news is grouped
* Output is clean and readable

## Non-goals (for now)

* Perfect accuracy
* Advanced AI summarization
* Personalization
* Monetization

## Future scope

* Better ranking algorithms
* LLM-powered summaries
* Sector-based filtering
* India-specific relevance layer

## Tone of output

* Clear
* Direct
* Insightful
* No jargon

---
name: seo-audit
description: >
  Full website SEO audit for Next.js sites — covers metadata API, generateMetadata,
  dynamic OG images (@vercel/og), sitemap.ts, robots.ts, next/image, JSON-LD structured
  data, Core Web Vitals, semantic HTML, and App Router SEO patterns. Use when user says
  "audit", "SEO check", "analyze my site", "website health check", "meta tags", "SEO",
  "Open Graph", "structured data", "sitemap", "robots.txt", "canonical", "page speed",
  "core web vitals", "heading hierarchy", "alt text", or anything SEO-related. Also
  triggers on "not ranking", "traffic dropped", "not showing up in Google", or "SEO issues".
user-invokable: true
argument-hint: "[url]"
license: MIT
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Agent
metadata:
  author: AgriciDaniel
  version: "2.0.0"
  category: seo
  filePattern: "**/app/**/layout.{ts,tsx},**/app/**/page.{ts,tsx},**/app/sitemap.{ts,tsx},**/app/robots.{ts,tsx},**/app/opengraph-image.{ts,tsx},**/app/manifest.{ts,tsx}"
  bashPattern: "lighthouse|pagespeed|sitemap|robots"
---

# Full Website SEO Audit

## Process

1. **Fetch homepage**: use `scripts/fetch_page.py` to retrieve HTML (or read source directly for local Next.js projects)
2. **Detect business type**: analyze homepage signals per seo orchestrator
3. **Crawl site**: follow internal links up to 500 pages, respect robots.txt
4. **Delegate to subagents** (if available, otherwise run inline sequentially):
   - `seo-technical` -- robots.txt, sitemaps, canonicals, Core Web Vitals, security headers
   - `seo-content` -- E-E-A-T, readability, thin content, AI citation readiness
   - `seo-schema` -- detection, validation, generation recommendations
   - `seo-sitemap` -- structure analysis, quality gates, missing pages
   - `seo-performance` -- LCP, INP, CLS measurements
   - `seo-visual` -- screenshots, mobile testing, above-fold analysis
   - `seo-geo` -- AI crawler access, llms.txt, citability, brand mention signals
   - `seo-local` -- GBP signals, NAP consistency, reviews, local schema, industry-specific local factors (spawn when Local Service industry detected: brick-and-mortar, SAB, or hybrid business type)
   - `seo-maps` -- Geo-grid rank tracking, GBP audit, review intelligence, competitor radius mapping (spawn when Local Service detected AND DataForSEO MCP available)
   - `seo-google` -- CWV field data (CrUX), URL indexation (GSC), organic traffic (GA4) (spawn when Google API credentials detected via `python scripts/google_auth.py --check`)
5. **Score** -- aggregate into SEO Health Score (0-100)
6. **Report** -- generate prioritized action plan

## Crawl Configuration

```
Max pages: 500
Respect robots.txt: Yes
Follow redirects: Yes (max 3 hops)
Timeout per page: 30 seconds
Concurrent requests: 5
Delay between requests: 1 second
```

## Output Files

- `FULL-AUDIT-REPORT.md`: Comprehensive findings
- `ACTION-PLAN.md`: Prioritized recommendations (Critical > High > Medium > Low)
- `screenshots/`: Desktop + mobile captures (if Playwright available)
- **PDF Report** (recommended): Generate a professional A4 PDF using `scripts/google_report.py --type full`. This produces a white-cover enterprise report with TOC, executive summary, charts (Lighthouse gauges, query bars, index donut), metric cards, threshold tables, prioritized recommendations with effort estimates, and implementation roadmap. Always offer PDF generation after completing an audit.

## Scoring Weights

| Category | Weight |
|----------|--------|
| Technical SEO | 22% |
| Content Quality | 23% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Performance (CWV) | 10% |
| AI Search Readiness | 10% |
| Images | 5% |

## Report Structure

### Executive Summary
- Overall SEO Health Score (0-100)
- Business type detected
- Top 5 critical issues
- Top 5 quick wins

### Technical SEO
- Crawlability issues
- Indexability problems
- Security concerns
- Core Web Vitals status

### Content Quality
- E-E-A-T assessment
- Thin content pages
- Duplicate content issues
- Readability scores

### On-Page SEO
- Title tag issues
- Meta description problems
- Heading structure
- Internal linking gaps

### Schema & Structured Data
- Current implementation
- Validation errors
- Missing opportunities

### Performance
- LCP, INP, CLS scores
- Resource optimization needs
- Third-party script impact

### Images
- Missing alt text
- Oversized images
- Format recommendations

### AI Search Readiness
- Citability score
- Structural improvements
- Authority signals

## Priority Definitions

- **Critical**: Blocks indexing or causes penalties (fix immediately)
- **High**: Significantly impacts rankings (fix within 1 week)
- **Medium**: Optimization opportunity (fix within 1 month)
- **Low**: Nice to have (backlog)

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, spawn the `seo-dataforseo` agent alongside existing subagents to enrich the audit with live data: real SERP positions, backlink profiles with spam scores, on-page analysis (Lighthouse), business listings, and AI visibility checks (ChatGPT scraper, LLM mentions).

## Google API Integration (Optional)

If Google API credentials are configured (`python scripts/google_auth.py --check`), spawn the `seo-google` agent to enrich the audit with real Google field data: CrUX Core Web Vitals (replaces lab-only estimates), GSC URL indexation status, search performance (clicks, impressions, CTR), and GA4 organic traffic trends. The Performance (CWV) category score benefits most from field data.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable (DNS failure, connection refused) | Report the error clearly. Do not guess site content. Suggest the user verify the URL and try again. |
| robots.txt blocks crawling | Report which paths are blocked. Analyze only accessible pages and note the limitation in the report. |
| Rate limiting (429 responses) | Back off and reduce concurrent requests. Report partial results with a note on which sections could not be completed. |
| Timeout on large sites (500+ pages) | Cap the crawl at the timeout limit. Report findings for pages crawled and estimate total site scope. |

---

## Next.js App Router SEO Patterns

This section covers SEO implementation patterns specific to Next.js (App Router). When auditing a Next.js project, check these patterns **in addition to** the general audit framework above.

### Metadata API

Next.js provides a typed `Metadata` object for static metadata and `generateMetadata()` for dynamic metadata. Both are server-only (no `'use client'`).

**Static metadata** — export from `layout.tsx` or `page.tsx`:
```tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Page Title',
  description: 'Page description for SERP snippet',
  metadataBase: new URL('https://yourdomain.com'),
  alternates: {
    canonical: '/current-path',       // Prevents duplicate content
  },
  openGraph: {
    title: 'OG Title',
    description: 'OG Description',
    url: 'https://yourdomain.com/page',
    siteName: 'Site Name',
    locale: 'en_US',
    type: 'website',                  // or 'article' for blog posts
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Twitter Title',
    description: 'Twitter Description',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}
```

**Dynamic metadata** — for pages with dynamic segments:
```tsx
import type { Metadata } from 'next'

type Props = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params  // Next.js 16: params is async
  const post = await getPost(slug)

  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/blog/${slug}` },
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: 'article',
      publishedTime: post.publishedAt,
      authors: [post.author],
    },
  }
}
```

**Audit checklist for metadata:**
- [ ] Every page has unique `title` and `description`
- [ ] `metadataBase` is set in root layout (all relative URLs resolve from this)
- [ ] `alternates.canonical` set on pages accessible via multiple URLs
- [ ] OpenGraph `type` is `'article'` for blog posts, `'website'` for pages
- [ ] Twitter card type is set (`summary_large_image` for visual content)
- [ ] Dynamic pages use `generateMetadata()`, not hardcoded static metadata
- [ ] `robots` is set appropriately (noindex for drafts, auth pages, etc.)
- [ ] Title is 50-60 chars, description is 150-160 chars

### Template Titles

Use `title.template` in the root layout so child pages get consistent branding:
```tsx
// app/layout.tsx
export const metadata: Metadata = {
  title: {
    default: 'Abhinav Ranish',
    template: '%s | Abhinav Ranish',  // Child pages: "Blog | Abhinav Ranish"
  },
}

// app/blog/page.tsx
export const metadata: Metadata = {
  title: 'Blog',  // Renders as "Blog | Abhinav Ranish"
}
```

### Dynamic OG Images with `@vercel/og`

Next.js supports file-based OG image generation using `opengraph-image.tsx`:

```tsx
// app/opengraph-image.tsx (root level — applies to all pages without their own)
// app/blog/[slug]/opengraph-image.tsx (per-route — overrides root)
import { ImageResponse } from 'next/og'

export const runtime = 'edge'
export const alt = 'Description of the image'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image() {
  return new ImageResponse(
    <div style={{ /* JSX layout */ }}>
      {/* Content */}
    </div>,
    { ...size }
  )
}
```

For dynamic routes, accept `params`:
```tsx
export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const post = await getPost(slug)
  return new ImageResponse(/* render with post data */)
}
```

**Audit checklist for OG images:**
- [ ] Root `opengraph-image.tsx` exists as fallback
- [ ] Dynamic routes have their own `opengraph-image.tsx` with route-specific content
- [ ] Image dimensions are 1200x630 (standard OG size)
- [ ] `alt` export is descriptive (accessibility + SEO)
- [ ] `twitter-image.tsx` exists if Twitter card needs different dimensions
- [ ] Custom fonts loaded via `fetch()` for brand consistency

### Sitemap (`sitemap.ts`)

Next.js generates sitemaps from a `sitemap.ts` file in the app root:

```tsx
import type { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await getAllPosts()

  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: 'https://yourdomain.com',
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 1,
    },
    {
      url: 'https://yourdomain.com/blog',
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
  ]

  const postRoutes: MetadataRoute.Sitemap = posts.map((post) => ({
    url: `https://yourdomain.com/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'monthly',
    priority: 0.6,
  }))

  return [...staticRoutes, ...postRoutes]
}
```

**For large sites (50k+ URLs)**, use `generateSitemaps()`:
```tsx
export async function generateSitemaps() {
  return [{ id: 0 }, { id: 1 }, { id: 2 }]
}

export default async function sitemap({ id }: { id: number }): Promise<MetadataRoute.Sitemap> {
  const start = id * 50000
  const posts = await getPostsBatch(start, 50000)
  return posts.map(/* ... */)
}
```

**Audit checklist for sitemap:**
- [ ] `sitemap.ts` exists in `app/` root
- [ ] All public, indexable pages are included
- [ ] `lastModified` uses real dates, not `new Date()` for static content
- [ ] Auth-gated, draft, and utility pages are excluded
- [ ] Dynamic routes are fetched and included
- [ ] `priority` values reflect actual page importance hierarchy

### Robots (`robots.ts`)

```tsx
import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/admin/'],
      },
    ],
    sitemap: 'https://yourdomain.com/sitemap.xml',
  }
}
```

**Audit checklist for robots:**
- [ ] `robots.ts` exists in `app/` root (preferred over static `robots.txt`)
- [ ] API routes are disallowed
- [ ] Admin/auth pages are disallowed
- [ ] Sitemap URL is referenced
- [ ] No accidental `Disallow: /` blocking the entire site

### JSON-LD Structured Data

Add structured data via a `<script>` tag in your page or layout. Next.js metadata API doesn't have a built-in JSON-LD field, so inject it manually:

```tsx
// Reusable helper
function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  )
}

// In a page component
export default function HomePage() {
  const personSchema = {
    '@context': 'https://schema.org',
    '@type': 'Person',
    name: 'Abhinav Ranish',
    url: 'https://aranish.uk',
    jobTitle: 'Software Engineer',
    sameAs: [
      'https://github.com/aranish-uk',
      'https://linkedin.com/in/aranish',
    ],
  }

  return (
    <>
      <JsonLd data={personSchema} />
      {/* Page content */}
    </>
  )
}
```

**Common schema types for portfolio sites:**
- `Person` — for the homepage (name, jobTitle, sameAs links)
- `WebSite` — for the root (name, url, search action)
- `Article` / `BlogPosting` — for blog posts
- `SoftwareApplication` — for project showcases
- `BreadcrumbList` — for navigation hierarchy

**Audit checklist for structured data:**
- [ ] Homepage has `Person` and/or `WebSite` schema
- [ ] Blog posts have `Article` or `BlogPosting` schema
- [ ] Project pages have `SoftwareApplication` or `CreativeWork` schema
- [ ] All schema validates at https://search.google.com/test/rich-results
- [ ] `sameAs` links point to active social profiles
- [ ] No schema markup on pages where it doesn't make sense

### `next/image` Optimization

```tsx
import Image from 'next/image'

<Image
  src="/photo.jpg"
  alt="Descriptive alt text for SEO and accessibility"
  width={800}
  height={600}
  priority        // Only for above-the-fold images (disables lazy loading)
  sizes="(max-width: 768px) 100vw, 50vw"  // Helps browser pick right size
/>
```

**Audit checklist for images:**
- [ ] All images use `next/image` (automatic WebP/AVIF, responsive srcset)
- [ ] Every image has descriptive `alt` text (not "image1" or empty)
- [ ] Above-the-fold hero/banner images use `priority` prop
- [ ] `sizes` prop is set for responsive images (prevents oversized downloads)
- [ ] No massive unoptimized images in `public/` served via `<img>` tags
- [ ] Decorative images use `alt=""` (empty, not missing)

### Semantic HTML & Heading Hierarchy

**Audit checklist:**
- [ ] Each page has exactly one `<h1>` (usually in the hero/title section)
- [ ] Headings follow logical hierarchy: `h1 > h2 > h3` (no skipping levels)
- [ ] `<main>` wraps primary content, `<nav>` for navigation, `<footer>` for footer
- [ ] `<article>` used for blog posts / standalone content
- [ ] `<section>` used with headings for thematic grouping
- [ ] `lang="en"` set on `<html>` element
- [ ] Links have descriptive text (not "click here" or "read more")

### Internal Linking

- [ ] All pages are reachable within 3 clicks from the homepage
- [ ] Navigation includes links to all key sections
- [ ] Blog posts link to related posts
- [ ] Project pages link back to the projects index
- [ ] No orphan pages (pages with zero internal links pointing to them)
- [ ] Anchor text is descriptive and varied (not all "learn more")

### Core Web Vitals (Next.js-specific)

| Metric | Target | Next.js Levers |
|--------|--------|---------------|
| LCP < 2.5s | `priority` on hero image, `next/font` to eliminate FOIT, streaming SSR | Server Components reduce JS bundle |
| INP < 200ms | Minimize client JS, push `'use client'` boundaries down the tree | Avoid large hydration payloads |
| CLS < 0.1 | `width`/`height` on all images, `next/font` with `display: swap` | Avoid layout shifts from dynamic content |

### Quick SEO Audit Checklist (Next.js)

Run through this when auditing any Next.js page:

```
METADATA
  [ ] Unique title (50-60 chars) with primary keyword
  [ ] Unique description (150-160 chars) with CTA
  [ ] metadataBase set in root layout
  [ ] Canonical URL set
  [ ] OG title, description, image
  [ ] Twitter card configured
  [ ] title.template in root layout

FILE-BASED SEO
  [ ] sitemap.ts includes all public pages
  [ ] robots.ts disallows private routes, references sitemap
  [ ] opengraph-image.tsx generates branded images
  [ ] manifest.ts for PWA (if applicable)

STRUCTURED DATA
  [ ] JSON-LD on homepage (Person/WebSite)
  [ ] JSON-LD on content pages (Article/SoftwareApplication)
  [ ] Validates in Rich Results Test

PERFORMANCE
  [ ] next/image for all images with alt text
  [ ] next/font for web fonts (no layout shift)
  [ ] Hero image has priority prop
  [ ] Server Components by default, minimal 'use client'
  [ ] No unused large JS bundles

SEMANTIC HTML
  [ ] Single h1 per page
  [ ] Logical heading hierarchy
  [ ] Semantic landmarks (main, nav, footer, article)
  [ ] lang attribute on <html>
  [ ] Descriptive link text

INTERNAL LINKING
  [ ] All pages reachable within 3 clicks
  [ ] Descriptive anchor text
  [ ] No broken internal links
  [ ] Blog/project cross-linking
```

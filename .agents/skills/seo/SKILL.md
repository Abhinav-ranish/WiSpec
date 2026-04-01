---
name: SEO
description: >
  Implementation-first SEO audit and fix skill. Inspects the actual codebase,
  identifies what is missing or broken, and implements fixes directly. Covers
  technical SEO (robots.txt, sitemap, canonicals, meta robots, crawlability),
  metadata quality (titles, descriptions, OG/Twitter cards), structured data
  (JSON-LD schema.org), content relevance (headings, copy, keyword targeting),
  internal linking, indexing/discovery, and framework-specific issues (static
  HTML, Next.js, React SPAs). Triggers on: "SEO", "not showing up in Google",
  "not indexed", "improve rankings", "fix SEO", "metadata", "structured data",
  "sitemap", "robots.txt", "Google Search", "search visibility".
user-invokable: true
argument-hint: "[audit|fix|report]"
license: MIT
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit, Agent
metadata:
  author: user
  version: "1.0.0"
  category: seo
  filePattern: "**/index.html,**/sitemap.xml,**/robots.txt,**/*.html,**/app/**/layout.{ts,tsx},**/app/**/page.{ts,tsx},**/app/sitemap.{ts,tsx},**/app/robots.{ts,tsx}"
  bashPattern: "lighthouse|pagespeed|sitemap|robots|seo"
---

# SEO: Implementation-First SEO Audit & Fix

**Invocation:** `/seo [audit|fix|report]`

This skill audits and improves SEO across the project with a practical, implementation-first approach. It inspects the actual codebase, identifies what is missing or weak, and fixes it directly. No generic advice — real changes to real files.

## Core Principles

- **Inspect before advising.** Read the actual files. Never guess what's there.
- **Fix, don't just flag.** Implement changes directly where possible.
- **Prioritize what blocks Google.** Indexing blockers first, then ranking factors.
- **No keyword stuffing.** No fake blog spam. No spammy schema.
- **Production-ready changes only.** Clean, minimal, correct.

---

## Workflow

### Step 0: Detect Framework & Structure

Before anything else, determine what you're working with:

```
1. Check for package.json → framework detection (Next.js, Astro, etc.)
2. Check for plain HTML files (index.html, etc.)
3. Identify the web root (web/, public/, src/, app/, or root)
4. Identify all pages/routes (file-based or directory-based)
5. Find the production domain (check meta tags, og:url, CNAME, config files)
```

**Framework-specific paths:**
| Framework | Metadata approach | Sitemap | Robots |
|-----------|------------------|---------|--------|
| Static HTML | `<head>` meta tags | `sitemap.xml` file | `robots.txt` file |
| Next.js (App Router) | `metadata` export / `generateMetadata()` | `app/sitemap.ts` | `app/robots.ts` |
| Next.js (Pages) | `next/head` or `next-seo` | `next-sitemap` | `public/robots.txt` |
| Astro | frontmatter + `<head>` | `@astrojs/sitemap` | `public/robots.txt` |

---

### Step 1: Technical SEO Audit

Check every item. Mark as PASS, FAIL, or MISSING.

#### 1.1 Crawlability & Indexability

```
[ ] robots.txt exists and is accessible at /robots.txt
[ ] robots.txt does NOT accidentally block important pages (no blanket Disallow: /)
[ ] robots.txt references the sitemap URL
[ ] sitemap.xml exists and is accessible at /sitemap.xml
[ ] sitemap.xml includes ALL public, indexable pages
[ ] sitemap.xml excludes auth-gated, draft, admin, and utility pages
[ ] sitemap.xml has valid XML structure
[ ] No accidental noindex on important pages (check meta robots tags)
[ ] No X-Robots-Tag headers blocking indexing
[ ] Pages return 200 status codes (not soft 404s)
[ ] Redirects resolve correctly (no chains, no loops)
[ ] No duplicate routes serving identical content without canonicals
```

#### 1.2 Canonical Tags

```
[ ] Every page has a <link rel="canonical"> pointing to itself
[ ] Canonical URLs use the production domain (not localhost or staging)
[ ] Canonical URLs use consistent protocol (https, not http)
[ ] Canonical URLs use consistent trailing slash convention
[ ] No canonical pointing to a different page unless intentional dedup
```

#### 1.3 URL Structure

```
[ ] URLs are clean, descriptive, lowercase
[ ] No unnecessary query parameters in indexed URLs
[ ] No hash-based routing for content that should be indexed
[ ] Consistent trailing slash behavior
```

#### 1.4 SSL & Security

```
[ ] Site is served over HTTPS
[ ] HTTP redirects to HTTPS
[ ] No mixed content warnings
```

#### 1.5 Mobile & Rendering

```
[ ] viewport meta tag is set: <meta name="viewport" content="width=device-width, initial-scale=1">
[ ] Content is visible without JavaScript (or SSR/SSG is used)
[ ] Google can see meaningful page content on initial load
[ ] No critical content hidden behind JS-only rendering with no fallback
[ ] Mobile-friendly layout (responsive design)
```

**Critical for SPAs / client-rendered sites:**
- If content only appears after JavaScript executes, Google may not see it
- Check: does the raw HTML response contain the main page content, or is it an empty `<div id="root">`?
- If empty shell: this is likely the #1 SEO blocker — must implement SSR/SSG or prerendering

---

### Step 2: Metadata Audit & Improvements

#### 2.1 Page Titles

```
[ ] Every page has a unique <title>
[ ] Titles are 50-60 characters (Google truncates ~60)
[ ] Primary keyword/topic is near the beginning of the title
[ ] Titles are specific and descriptive (not "Home" or "Page 1")
[ ] Titles are compelling for humans (would you click this in search results?)
[ ] Brand name included where appropriate (usually at end: "Topic | Brand")
```

**Good titles:**
- "WiSpec: Tri-Band Wi-Fi Sensing for Human Activity Recognition"
- "Commodity Wi-Fi Spectroscopy Research | WiSpec Project"

**Bad titles:**
- "Home"
- "WiSpec"
- "Wi-Fi Sensing Research Project Homepage - WiFi - Sensing - Research"

#### 2.2 Meta Descriptions

```
[ ] Every page has a unique <meta name="description">
[ ] Descriptions are 120-160 characters
[ ] Descriptions include a clear value proposition or summary
[ ] Descriptions include a call-to-action where appropriate
[ ] Descriptions match actual page content (not misleading)
```

#### 2.3 Open Graph & Twitter Cards

```
[ ] og:title is set (can differ from <title> for social optimization)
[ ] og:description is set
[ ] og:image is set with a proper 1200x630 image
[ ] og:image:width and og:image:height are specified
[ ] og:url points to the canonical URL
[ ] og:type is set (website, article, etc.)
[ ] og:site_name is set
[ ] twitter:card is set (summary_large_image for visual content)
[ ] twitter:title, twitter:description are set
[ ] og:image URL is absolute (not relative)
```

#### 2.4 Other Head Elements

```
[ ] <html lang="en"> (or appropriate language) is set
[ ] charset is declared: <meta charset="utf-8">
[ ] favicon is present and referenced
```

---

### Step 3: Structured Data (JSON-LD)

Add relevant schema.org markup as JSON-LD `<script type="application/ld+json">` blocks.

#### Choose Schema Types Based on Page Content

| Page Type | Schema Types |
|-----------|-------------|
| Homepage (personal/research) | Person, WebSite, WebPage |
| Homepage (organization) | Organization, WebSite, WebPage |
| Research/academic project | ScholarlyArticle, SoftwareSourceCode, Dataset |
| Blog post | Article, BlogPosting, BreadcrumbList |
| Product page | Product, Offer, BreadcrumbList |
| FAQ page | FAQPage (gov/health only for Google rich results) |
| Software project | SoftwareApplication, SoftwareSourceCode |
| About page | Person or Organization, WebPage |

#### Schema Quality Rules

- `@context` must be `https://schema.org`
- All URLs must be absolute
- `sameAs` should link to real, active profiles
- Don't add schema types that don't match the page content
- Don't duplicate the same schema type multiple times on one page
- Validate at https://search.google.com/test/rich-results
- **Never use HowTo schema** (deprecated Sept 2023)
- **FAQPage** only benefits Google rich results for gov/health sites (Aug 2023 restriction)

---

### Step 4: Content Relevance

#### 4.1 Heading Structure

```
[ ] Each page has exactly ONE <h1>
[ ] h1 clearly describes the page topic
[ ] Headings follow logical hierarchy: h1 > h2 > h3 (no skipping)
[ ] Headings are descriptive, not decorative ("Our Research" not "Section 2")
[ ] Key topics and terms appear naturally in headings
```

#### 4.2 Content Quality

```
[ ] Main page content is substantive (not a thin placeholder)
[ ] Content clearly communicates what the page/project is about
[ ] Key terms a user would search for appear naturally in the copy
[ ] First 100 words contain the primary topic/keyword
[ ] Content is structured with clear sections and hierarchy
[ ] No walls of text — use paragraphs, lists, subheadings
```

#### 4.3 Content Relevance for Search Intent

For each important page, identify:
1. **What would someone search to find this page?** (target queries)
2. **Does the page content clearly answer those queries?**
3. **Is the page more relevant than competing results for those queries?**

If a page is too vague or generic, improve the copy to be more specific and targeted — without keyword stuffing.

---

### Step 5: Internal Linking

```
[ ] All important pages are linked from the main navigation or footer
[ ] No orphan pages (pages with zero internal links pointing to them)
[ ] Anchor text is descriptive (not "click here" or bare URLs)
[ ] Important pages receive more internal links
[ ] All pages are reachable within 3 clicks from the homepage
[ ] No broken internal links (404s)
```

For single-page sites with anchor navigation:
```
[ ] Navigation links to all major sections via anchors
[ ] Section IDs are descriptive and URL-friendly
[ ] Footer includes links to key sections
```

---

### Step 6: Indexing & Discovery

```
[ ] sitemap.xml is submitted to Google Search Console
[ ] robots.txt allows Googlebot access to all important pages
[ ] Important pages are discoverable from the homepage within 2-3 clicks
[ ] No important content hidden behind JavaScript-only interactions
[ ] Google Search Console is set up and verified
[ ] Domain is configured correctly (www vs non-www, HTTPS)
```

**Manual follow-up items** (cannot be automated in code):
- Submit sitemap to Google Search Console
- Request indexing for important pages via URL Inspection tool
- Verify domain ownership in Google Search Console
- Check for manual actions or security issues in GSC
- Monitor indexing status over 2-4 weeks after fixes

---

### Step 7: Framework-Specific Checks

#### Static HTML Sites

```
[ ] All meta tags are in the <head>, not <body>
[ ] No JavaScript-only content that Google can't see
[ ] Images use proper <img> tags with alt attributes (not CSS backgrounds for content images)
[ ] External CSS/JS files are not blocking rendering unnecessarily
[ ] No inline styles overriding semantic structure
```

#### Next.js (App Router)

```
[ ] metadataBase is set in root layout
[ ] Each page exports metadata or generateMetadata()
[ ] title.template is set in root layout for consistent branding
[ ] sitemap.ts exists in app/ root with all public routes
[ ] robots.ts exists in app/ root
[ ] opengraph-image.tsx provides dynamic OG images
[ ] Server Components are default (no unnecessary 'use client')
[ ] Dynamic routes use generateMetadata() with actual data
[ ] next/image used for all images (automatic optimization)
[ ] next/font used for web fonts (no layout shift)
[ ] No important content rendered only on the client side
```

#### React SPAs (Create React App, Vite, etc.)

```
[ ] Pre-rendering or SSR is configured for SEO-critical pages
[ ] react-helmet or similar is used for page-level meta tags
[ ] Content is in the initial HTML, not loaded after mount
[ ] Hash routing (#/) is NOT used for indexable pages (use path routing)
```

---

## Step 8: Implement Fixes

For each issue found, implement the fix directly in the codebase. Prioritize in this order:

### Priority 1: Critical (Blocks Indexing)
- Missing or broken robots.txt
- Accidental noindex on important pages
- Content invisible to Google (JS-only rendering)
- Missing sitemap.xml
- Broken canonical tags pointing to wrong URLs
- 4xx/5xx status codes on important pages

### Priority 2: High (Hurts Rankings)
- Missing or poor page titles
- Missing meta descriptions
- Missing canonical tags
- Poor heading structure (no h1, wrong hierarchy)
- Missing structured data
- Thin content on important pages

### Priority 3: Medium (Missed Opportunities)
- Missing or incomplete OG/Twitter metadata
- Missing alt text on images
- Weak internal linking
- Non-descriptive anchor text
- Missing lang attribute
- Missing schema.org types that would add context

### Priority 4: Low (Polish)
- Suboptimal title length
- Meta description length tweaks
- Additional schema types (BreadcrumbList, etc.)
- Minor content improvements

---

## Step 9: Generate Report

After implementing fixes, produce a concise report:

```markdown
# SEO Audit & Fixes Report

## Summary
- Issues found: X
- Issues fixed: X
- Issues requiring manual follow-up: X

## What Was Hurting SEO
[List the specific issues that were blocking or hurting search visibility]

## What Was Changed
[List each change made, with file paths]

## Manual Follow-Up Required
[Things that can't be fixed in code:]
- [ ] Submit sitemap to Google Search Console
- [ ] Request indexing for key pages
- [ ] Set up Google Search Console if not already done
- [ ] Monitor indexing status after 2-4 weeks
- [ ] [Any domain/DNS/hosting items]
- [ ] [Any backlink/authority items]

## Before/After
[Key metadata comparisons showing the improvement]
```

---

## Reference Files

Load on-demand as needed (do NOT load all at startup):
- `references/eeat-framework.md`: E-E-A-T evaluation criteria (Dec 2025 core update)
- `references/quality-gates.md`: Content length minimums, title/description requirements
- `references/cwv-thresholds.md`: Core Web Vitals thresholds (Feb 2026)

---

## What NOT To Do

- Do NOT keyword-stuff titles, descriptions, or content
- Do NOT generate fake blog posts or filler pages just for SEO
- Do NOT add schema markup that doesn't match the actual page content
- Do NOT add excessive or spammy structured data
- Do NOT use HowTo schema (deprecated Sept 2023)
- Do NOT recommend FAQPage schema for commercial sites (restricted Aug 2023)
- Do NOT add hidden text or cloaked content
- Do NOT create doorway pages
- Do NOT guess at what the site contains — read the actual files first
- Do NOT make changes that break the site's design or functionality
- Do NOT add SEO "hacks" that violate Google's guidelines

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Can't determine framework | Ask user. Default to static HTML checks. |
| No production domain found | Check og:url, CNAME, config files. Ask user if unclear. |
| Site is entirely client-rendered | Flag as Critical P1 issue. Recommend SSR/SSG/prerendering. |
| Multiple pages with identical content | Add canonical tags pointing to the preferred version. |
| Can't access live site (no URL) | Audit source code only. Note that live testing is needed for full audit. |

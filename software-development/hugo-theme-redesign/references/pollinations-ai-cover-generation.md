# Cover Image Generation via Pollinations.ai Free API

## Overview

Pollinations.ai provides free image generation via HTTP GET — no API key, no registration, no rate limits for moderate use. This is an ideal fallback when paid image generation APIs (Agnes, FAL, Midjourney, etc.) return 401, exceed budget, or are unavailable.

**Proven in production:** Used to generate 6 cover images for angelife Hugo articles after Agnes API returned 401 ("无效的令牌") despite a valid 50-character key format.

## API URL Format

```
https://image.pollinations.ai/prompt/{prompt}?width=1200&height=630&nologo=true
```

Parameters:
- **width=1200** and **height=630** — Standard Hugo cover image aspect ratio (1.91:1, matches Open Graph / Twitter card)
- **nologo=true** — Suppresses Pollinations watermark
- No API key, no headers, no POST body needed — just a curl GET

## Prompt Strategy by Article Category

For Hugo articles with consistent visual identity:

| Category | Prompt Theme | Example Prompt |
|----------|-------------|---------------|
| AI/Technology | Abstract circuit/neural patterns, dark blue/cyan palette | "abstract neural network digital art, dark blue cyan circuit patterns, ethereal atmosphere" |
| Philosophy/Classics | Minimalist Chinese ink wash, monochrome | "minimalist Chinese ink wash painting style, empty space, thin mist, philosophical contemplation" |
| Life/Growth | Soft warm gradient, organic shapes | "soft warm gradient abstract art, organic flowing shapes, peaceful harmony" |
| Work/Reports | Clean geometric patterns, professional | "clean geometric pattern, professional modern business style, minimal" |
| Society/Critique | Stark high-contrast, grunge texture | "stark high contrast grunge texture abstract, urban decay feeling, dramatic shadows" |
| Default | Subtle gradient with geometric elements | "subtle gradient with geometric elements, calm sophisticated, modern minimalist" |

## Batch Generation Workflow

### Step 1: Identify Articles Missing Covers

```bash
# Published articles without cover frontmatter
grep -rl '^draft: false' content/posts/ | xargs grep -L '^cover:'
```

### Step 2: Generate Covers Batch

Each cover needs:
1. A target directory: `static/images/posts/<slug>/` (must exist)
2. A prompt based on the article's category/tags

```python
import urllib.request, urllib.parse, os, time

articles = [
    {"slug": "ai-mind-labor-colonial", "prompt": "abstract neural network digital art, dark blue cyan circuit patterns, ethereal atmosphere"},
    # ... add all missing articles
]

base = "https://image.pollinations.ai/prompt"
for a in articles:
    url = f"{base}/{urllib.parse.quote(a['prompt'])}?width=1200&height=630&nologo=true"
    out = f"static/images/posts/{a['slug']}/cover.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    urllib.request.urlretrieve(url, out)
    time.sleep(0.5)  # pace to avoid rate limiting
```

### Step 3: Add Cover Frontmatter

For each generated cover, add to the article's `index.md`:

```yaml
cover:
  image: /images/posts/<slug>/cover.png
  alt: "<article title>"
```

**Insertion point:** After the `categories:` line (or `tags:` if no categories). Use `patch` tool with unique context strings.

### Step 4: Verify

```bash
# Check cover files on disk
ls -la static/images/posts/<slug>/cover.png
file static/images/posts/<slug>/cover.png  # should say "JPEG image data"

# Check frontmatter has cover reference
grep -A2 '^cover:' content/posts/<slug>/index.md

# Build and check for YAML errors
hugo --gc --minify 2>&1 | grep -E '(ERROR|WARN)'
```

## Known Issues

### YAML `---` delimiter conflict

If any article body uses `---` as a Markdown section separator, the YAML frontmatter parser will interpret it as the closing delimiter of the frontmatter block. **Always check for `---` in the article body before adding YAML `cover:` frontmatter.** The fix: ensure the frontmatter has a proper closing `---` before any body `---`. See the "YAML frontmatter delimiter conflict" pitfall in the main SKILL.md.

### Rate limiting

Pollinations.ai has no documented rate limit for moderate use, but very rapid sequential requests (>1 per second for extended periods) may return 503. Pace batch generation with a short delay (0.5s) between requests.

### Image quality

Pollinations.ai uses free-tier models (likely FLUX.1-schnell or SDXL). Results are adequate for cover images at 1200×630 (25-97 KB per image) but not suitable for high-resolution print or detailed illustration. For production-quality covers, use a paid API when available.

### No content moderation bypass

Prompt injection or explicit content prompts are filtered server-side. Keep prompts descriptive and non-violative.

## Comparison: Pollinations.ai vs Paid APIs

| Aspect | Pollinations.ai (Free) | Paid APIs (Agnes, FAL, etc.) |
|--------|----------------------|------------------------------|
| API Key | None needed | Required |
| Cost | Free | Per-generation billing |
| Quality | Adequate for 1200×630 covers | Higher resolution, more control |
| Rate Limits | Soft (pace 0.5s apart) | Varies by plan |
| Reliability | Generally reliable | Depends on key validity |
| Best For | Fallback, prototyping, budget projects | Production, high-resolution, consistent branding |

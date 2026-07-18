# Cover Image Gap Detection — Orphaned cover.png on Disk

## The Problem

After restoring historical articles (e.g. from git history or Blogger migration), **cover.png files may exist on disk in `static/images/posts/` while the articles' frontmatter has no `cover:` field**. This creates a silent gap: the images are deployed with every build but never rendered.

**Symptom:** `find static/images/posts/ -name 'cover.png' | wc -l` returns 110, but `grep -r '^cover:' content/posts/` shows only 0-2 matches for old articles.

## Root Cause

During restoration/cleanup, the `cover:` field was removed to avoid build warnings about missing images. But the cover.png files (which were generated or preserved from the original site) remained on disk. They are deployed but invisible — a waste of bandwidth and a missed visual opportunity.

## Detection Script

```bash
# List all cover.png directories (one per article topic)
find static/images/posts/ -name 'cover.png' | sed 's|/static/images/posts/||' | sed 's|/cover.png||' | sort > /tmp/covers_on_disk.txt

# List all article bundle directories
find content/posts/ -mindepth 1 -maxdepth 1 -type d | sed 's|content/posts/||' | sort > /tmp/articles_on_disk.txt

# Covers that exist but have no matching article at all (orphaned images)
comm -23 /tmp/covers_on_disk.txt /tmp/articles_on_disk.txt

# Articles that exist but have no cover reference in frontmatter (missed opportunity)
comm -12 /tmp/covers_on_disk.txt /tmp/articles_on_disk.txt | while read dir; do
  if ! grep -q '^cover:' "content/posts/$dir/index.md" 2>/dev/null; then
    echo "MISSING_COVER: $dir"
  fi
done
```

## Fix: Reconnect Cover to Article

For each article whose directory name matches a cover.png directory, add a cover reference to its frontmatter:

```bash
find static/images/posts/ -name 'cover.png' | while read img; do
  dir=$(basename "$(dirname "$img")")
  article="content/posts/$dir/index.md"
  if [ -f "$article" ] && ! grep -q '^cover:' "$article"; then
    # Add cover before first category line
    sed -i '' "/^categories:/i\\
cover:\\
  image: /images/posts/$dir/cover.png\\
  alt: \"$(head -1 "$article" | sed 's/title: \"//;s/\"//' | xargs)\"\\
" "$article"
    echo "Fixed: $dir"
  fi
done
```

**Note:** This pattern assumes `static/images/posts/<dir>/cover.png` maps to `content/posts/<dir>/index.md` by directory name. This only works for page-bundle style articles (each article is a directory with `index.md`). Flat-style articles (`content/posts/2026-06-20-foo.md` without a subdirectory) need a different mapping.

## Verification

After applying:

```bash
# Before
find static/images/posts/ -name 'cover.png' | wc -l
# → 110

grep -r '^cover:' content/posts/ | wc -l
# → 2 (only recent articles)

# After
grep -r '^cover:' content/posts/ | wc -l
# → 112 (110 old + 2 recent)

hugo --gc --minify 2>&1 | tail -3
# → 0 errors, no missing-image warnings
```

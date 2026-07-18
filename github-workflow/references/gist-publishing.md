# Gist Publishing Workflow

Quick publishing of articles and reference documents as public GitHub Gists via `gh` CLI.

## Basic Usage

```bash
# Create public gist from file
gh gist create --desc "Title" -p -f filename.md /path/to/file.md

# Multiple files
gh gist create --desc "Multi-file gist" -p file1.md file2.md /other/dir/file3.md

# From stdin (pipe)
cat file.md | gh gist create --desc "Title" -p -f file.md -
```

## When to Use

- Quick code snippets or reference docs for sharing
- Articles that don't belong in the main Hugo site
- Fallback when Hugo site is temporarily unavailable
- Quick reference materials that need public URL

## Pitfalls

1. **Anonymous Gist API requires authentication** — `curl` to `api.github.com/gists` returns 401 without a token. Always use `gh` CLI which uses the configured auth.
2. **`gh gist create` has `--desc` not `--description`** — wrong flag name causes error.
3. **Gists are public by default** — don't publish sensitive data. Use `-p` flag explicitly.
4. **Content size limit** — Gists cap at 10MB total. For large documents, prefer Hugo site or S3/R2.
5. **Gist URLs don't support custom domains** — URL is `https://gist.github.com/<user>/<id>`. No redirect to custom domain.
6. **Gist updates create new versions** — `gh gist edit` creates a new version. The original URL stays the same but history is versioned.

## Alternative: Hugo Site

For articles meant for the public site, ALWAYS prefer Hugo + GitHub Pages (`angelife.github.io`) over Gist. Gist is for quick/auxiliary content only.

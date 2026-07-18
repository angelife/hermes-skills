# Hugo Cover Parameter Map Handling

## The Problem

Articles in the frontmatter may define `cover` as a map:
```yaml
cover:
  image: /images/cover.png
  alt: "Cover text"
  caption: "Caption"
```

Or as a plain string URL:
```yaml
cover: /images/cover.png
```

Templates that assume `cover` is always a string break on map-style covers.

## Detection

```go-template
{{ $cover := .Params.cover }}
{{ printf "type=%T value=%v" (printf "%T" $cover) $cover }}
```

Output for map: `type=map[string]interface {} value=map[image:/images/cover.png alt:Text]`
Output for string: `type=string value=/images/cover.png`

## Safe Template Pattern

```go-template
{{ $cover := .Params.cover }}
{{ if reflect.IsMap $cover }}
  {{ $cover = $cover.image }}
{{ end }}
{{ with $cover }}
  <figure>
    <img src="{{ . | absURL }}" alt="{{ with ($.Params.cover.alt) }}{{ . }}{{ end }}" />
    {{ with ($.Params.cover.caption) }}<figcaption>{{ . }}</figcaption>{{ end }}
  </figure>
{{ end }}
```

## Files Affected in angelife

- `hugo-site/layouts/_default/single.html` — article cover image rendering
- Any template that reads `.Params.cover` or `.Params.cover.image`

## How Many Articles Use Map Covers

Run from hugo-site root:
```bash
grep -r "cover:" content/ --include="*.md" | grep "image:" | wc -l
# vs plain URL style:
grep -r "^cover: /" content/ --include="*.md" | wc -l
```

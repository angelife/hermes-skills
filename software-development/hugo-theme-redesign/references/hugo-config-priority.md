# Hugo Config File Priority

## Key Rule

When **both `hugo.toml` and `hugo.yaml`** exist in the same directory, Hugo uses `hugo.toml` and silently ignores `hugo.yaml`. This means any settings added to YAML (menus, params, taxonomies, etc.) will not take effect.

## How to Diagnose

1. Check if both files exist: `ls hugo.toml hugo.yaml`
2. Search for the config key in TOML: `grep "menu" hugo.toml`
3. Compare: if a key exists in TOML but not YAML, TOML wins
4. If a key exists in YAML but not TOML, it is **ignored**

## Symptoms

- Menu items defined in YAML don't appear on the site (`.Site.Menus.main` is empty)
- New params added to YAML don't show up in templates
- Build works fine but the site looks wrong — no errors because YAML is silently skipped

## Fix

**Option 1:** Remove `hugo.toml`, keep `hugo.yaml` as the only config file.

**Option 2:** Add the missing config to `hugo.toml` using TOML syntax:

```toml
# YAML equivalent:
# menu:
#   main:
#     - name: "金"
#       url: "/series/information-judgment/"
#       weight: 1

# TOML format:
[[menu.main]]
  name = "金"
  url = "/series/information-judgment/"
  weight = 1
```

**Option 3:** Explicitly specify which config to load: `hugo --config hugo.yaml` (but this breaks CI/CD if not also updated).

## Best Practice

Pick one format and stick with it. Don't maintain two config files in the same directory.

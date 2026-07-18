# Duplicate `providers:` Block Overwrites Custom Provider (Session 2026-06-26)

## Problem
After writing a `providers: freellmapi:` block with 71 models to `config.yaml`, `/model` command still only lists 2 built-in nvidia models. All 71 models disappear.

## Root Cause
The file had **two** `providers:` keys:
1. `providers:` + `freellmapi:` with full definition (correct)
2. `providers: {}` empty block at a later position

Python's `yaml.safe_load()` silently takes the LAST duplicate key — so the empty `{}` overwrote the full definition.

## How It Happened
When a Python script wrote 71 model IDs into the file, it appended them after `providers: freellmapi:` but the file already contained an empty `providers: {}` from a prior template/edit. The `sed`/write didn't remove the old empty block.

## Fix
```bash
# 1. Find all duplicate providers: lines
grep -n '^providers:' ~/.hermes/config.yaml

# 2. Remove empty providers: {} lines
sed -i 's/^providers: {}$//g' config.yaml

# 3. Verify YAML parses correctly
python3 -c "
import yaml
with open(config) as f:
    cfg = yaml.safe_load(f)
p = cfg.get('providers', {})
print(f'providers count: {len(p)}')
for k, v in p.items():
    print(f'  {k}: models={len(v.get(\"models\", []))}')
"

# 4. Restart gateway
hermes gateway restart
```

## Prevention
Before writing any new `providers:` block:
1. First delete all existing empty `providers: {}` lines
2. Write the block from scratch
3. Verify with the Python check above before restarting

---
name: gmail-cleanup-workflow
description: Bulk cleanup Gmail inboxes using Gmail API - archiving GitHub notifications, finding unsubscribe links, managing marketing emails. Covers token refresh, batch limits, and unsubscribe link extraction.
version: 1.0.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [Gmail, email, OAuth, Google API, batch processing]
    related_skills: [google-workspace]
---

# Gmail Cleanup Workflow

Bulk clean up Gmail inboxes using the Gmail API with OAuth2.

## Gmail API Token Format

The `google_token.json` file needs specific fields for `google-api-python-client` to work:

```json
{
  "access_token": "ya29...",
  "refresh_token": "1//0e...",
  "token_type": "Bearer",
  "expiry": "2026-04-28T...",
  "client_id": "<from google_client_secret.json>",
  "client_secret": "<from google_client_secret.json>"
}
```

The `setup.py` script does NOT add `client_id` and `client_secret` automatically. Manually add them from `google_client_secret.json` → `installed.client_id` and `installed.client_secret`.

## Token Refresh

When token expires (SSL errors), refresh with:

```python
import urllib.request, urllib.parse, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('~/.hermes/google_token.json') as f:
    token = json.load(f)

data = urllib.parse.urlencode({
    'client_id': token['client_id'],
    'client_secret': token['client_secret'],
    'refresh_token': token['refresh_token'],
    'grant_type': 'refresh_token'
}).encode()

req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    new_token = json.loads(resp.read())
    token['access_token'] = new_token['access_token']
    with open('~/.hermes/google_token.json', 'w') as f:
        json.dump(token, f, indent=2)
```

## Gmail API Batch Request Limit

**CRITICAL**: Gmail batch requests support MAX 100 requests per batch, NOT 1000.

```python
# WRONG - will fail with "Inner request count exceeds the limit"
batch_size = 1000

# CORRECT
batch_size = 100
```

## Finding Unsubscribe Links

Marketing email unsubscribe links are often in headers, NOT in the body. Check these headers:

1. `List-Unsubscribe` - may contain mailto: or https: URLs
2. `List-Unsubscribe-Post` - indicates one-click unsubscribe
3. Raw email body - may contain tracked unsubscribe links

Many unsubscribe URLs from headers are:
- Tracked/encoded (e.g., `etrack05.com`, `clicks.mlsend2.com`)
- Short-lived (expire quickly)
- SSL-incompatible (some fail with `net::ERR_SSL_VERSION_OR_CIPHER_MISMATCH`)

**Reliable approach**: Open the actual email in Gmail web UI and find the unsubscribe link there, or use browser to navigate through the email directly.

## Python Gmail API Pattern

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('~/.hermes/google_token.json', 
    ['https://www.googleapis.com/auth/gmail.modify'])
service = build('gmail', 'v1', credentials=creds)

# List messages with query
result = service.users().messages().list(
    userId='me', q='from:github.com in:inbox', maxResults=500, pageToken=page_token
).execute()

# Batch modify (max 100 per batch)
batch = service.new_batch_http_request()
for msg_id in batch_ids:
    batch.add(service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'addLabelIds': ['Label_19'], 'removeLabelIds': ['INBOX']}
    ))
batch.execute()
```

## Himalaya TLS Issue

`himalaya` (v1.1.0) has a TLS/SSL bug with Gmail IMAP. It fails with:
- `tls handshake eof`
- `Application-specific password required` (even with valid App Password)

Use Python `imaplib` directly for Gmail access instead when himalaya fails.

## Key Commands

```python
# Get profile/total emails
service.users().getProfile(userId='me').execute()

# List labels
service.users().labels().list(userId='me').execute()

# Search with queries (Gmail search syntax)
# q='in:inbox from:github.com'
# q='in:inbox -from:github.com'
# q='in:inbox after:2024-01-01 before:2025-01-01'
```

## OAuth Setup Gotchas

1. `setup.py` needs `PYTHONPATH=~/.hermes/hermes-agent` to find `hermes_constants`
2. OAuth client secret JSON must contain `installed` key (not `web`)
3. When app is in "Testing" mode, add test users at: https://console.cloud.google.com/auth/audience
4. Token file path: `~/.hermes/google_token.json`
5. Client secret path: `~/.hermes/google_client_secret.json`
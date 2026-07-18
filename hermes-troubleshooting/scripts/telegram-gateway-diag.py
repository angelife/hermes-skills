#!/usr/bin/env python3
"""Quick diagnostic check for Telegram Gateway status."""
import urllib.request
import json
import sys

def main():
    # Read token from .env
    try:
        with open('/Users/macos/.hermes/.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    token = line.split('=', 1)[1].strip('"\'')
                    break
            else:
                print("ERROR: TELEGRAM_BOT_TOKEN not found in ~/.hermes/.env", file=sys.stderr)
                sys.exit(1)
    except FileNotFoundError:
        print("ERROR: ~/.hermes/.env not found", file=sys.stderr)
        sys.exit(1)

    def tg_api(method):
        url = f"https://api.telegram.org/bot{token}/{method}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    print("=" * 60)
    print("TELEGRAM GATEWAY DIAGNOSTIC")
    print("=" * 60)

    # 1. Bot identity
    me = tg_api("getMe")
    if me.get("ok"):
        bot = me["result"]
        print(f"\nBot: {bot['first_name']} (@{bot['username']})")
        print(f"ID: {bot['id']}")
    else:
        print(f"\nBot check FAILED: {me.get('error_description', me)}")
        sys.exit(1)

    # 2. Webhook/Polling status
    wh = tg_api("getWebhookInfo")
    print(f"\n--- Connection ---")
    if wh.get("ok"):
        r = wh["result"]
        if r.get("url"):
            print(f"Mode: Webhook ({r['url']})")
            print(f"Custom cert: {r.get('has_custom_certificate', False)}")
            print(f"Last error: {r.get('last_error_message', 'none')}")
        else:
            print("Mode: Polling (no webhook)")
        print(f"Pending updates: {r.get('pending_update_count', 0)}")

    # 3. Our bot's group read capability
    print(f"\n--- Our Bot Permissions ---")
    if me.get("ok"):
        can_read = me["result"].get("can_read_all_group_messages", "N/A")
        print(f"Can read all group messages: {can_read}")

    # 4. Forum topics
    print(f"\n--- Forum Topics ---")
    group_chat_id = "-1003926068725"
    topics = tg_api(f"getForumTopicThreads?chat_id={group_chat_id}")
    if topics.get("ok"):
        print(f"Group: {topics['result'][0]['chat']['title'] if topics['result'] else 'N/A'}")
        for t in topics["result"]:
            print(f"  Topic #{t['message_thread_id']}: {t['name']}")
    else:
        print(f"Could not list topics: {topics.get('description', topics)}")

    # 5. Recent updates
    print(f"\n--- Recent Updates ---")
    updates = tg_api(f"getUpdates?offset=-1&limit=5&timeout=0")
    if updates.get("ok"):
        result = updates["result"]
        if not result:
            print("  No recent updates")
        else:
            for u in result:
                msg = u.get("message", u.get("edited_message", {}))
                if msg:
                    user = msg.get("from", {})
                    text = msg.get("text", "")[:80]
                    date = msg.get("date", "?")
                    is_bot = user.get("is_bot", False)
                    print(f"  [{date}] {user.get('first_name', '?')} (@{user.get('username', '?')}) bot={is_bot}: {text}")
    else:
        print(f"Error: {updates}")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()

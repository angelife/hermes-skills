# WeChat iLink Bot Pairing Flow

When setting up Hermes WeChat (Weixin) adapter via `hermes gateway setup`, the following flow is required:

## QR Login

1. Select `Weixin / WeChat` (#3) from the platform menu
2. Answer `Y` to "Start QR login now?"
3. A QR code URL is displayed: `https://liteapp.weixin.qq.com/q/7GiQu1?qrcode=<hash>&bot_type=3`
4. **User must scan from mobile WeChat quickly** — QR expires in ~2 minutes
5. After scanning, the terminal logs: `微信连接成功，account_id=<id>@im.bot`

## DM Authorization (Pairing)

The bot uses iLink bot identity (`...@im.bot`). First-time DM users are unauthorized:

```
WARNING  Unauthorized user: <user_id>@im.wechat on weixin
```

The bot sends a pairing code in the chat. Run:
```
hermes pairing approve weixin <PAIRING_CODE>
```

After approval, future messages are recognized automatically.

## Known Limitations

- iLink bot can only receive DMs (not group messages)
- Pairing persists across gateway restarts
- The QR code session must not be killed until credentials are saved to `~/.hermes/weixin/accounts/<id>.json`

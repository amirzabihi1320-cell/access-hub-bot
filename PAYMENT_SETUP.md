# Tronado automatic payment setup

Access Hub now contains a provider adapter for the documented Tronado Public API v5.
The integration does **not** automate the Telegram UI of `@tronadorobot`; it uses
Tronado's server API and signed IPN webhook.

## Required environment variables

```env
TRONADO_API_KEY=
TRONADO_IPN_SIGNING_KEY=
TRONADO_WALLET_ADDRESS=T...
TRONADO_BASE_URL=https://bot.tronado.cloud
TRONADO_WAGE_FROM_BUSINESS_PERCENTAGE=0
TRONADO_CALLBACK_URL=https://YOUR-DOMAIN.example/payments/tronado/webhook
```

If `TRONADO_CALLBACK_URL` is empty, Access Hub builds it from `WEBHOOK_BASE_URL`.
The callback must be publicly reachable over HTTPS in production.

## Flow

1. User opens Wallet.
2. User chooses `⚡️ پرداخت خودکار`.
3. Access Hub creates a unique `PaymentID`.
4. Tronado returns a payment URL and TRX quote.
5. User pays through the Tronado payment page.
6. Tronado sends a signed IPN to `/payments/tronado/webhook`.
7. Access Hub verifies `X-Tronado-Sig` against the raw body.
8. Only a settled payment (`IsPaid=true` / status `30`) is accepted.
9. The user's Toman wallet is credited once using an idempotent payment reference.
10. The business receives the TRX according to the Tronado account/wallet configuration.

## Important

- Never put the Tronado API key or IPN signing key in Git.
- Never trust the client-side "payment successful" message.
- Do not credit the wallet from an unverified webhook.
- `TRONADO_WALLET_ADDRESS` is the destination configured for the business integration.
- The current code intentionally does not invent a TRX→TON or Fragment purchasing API.
  Those must be added as separate adapters only after the exact official API/flow is
  available.

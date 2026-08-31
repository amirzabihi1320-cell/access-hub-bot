import hashlib
import hmac
import json
from decimal import Decimal

import httpx
import pytest

from app.providers.payment.tronado import TronadoProvider


@pytest.mark.asyncio
async def test_tronado_create_payment_and_price(monkeypatch):
    provider = TronadoProvider(
        api_key="key",
        ipn_signing_key="signing",
        wallet_address="TXYZ",
    )
    calls = []

    async def fake_post(path, payload):
        calls.append((path, payload))
        if path == "/Tron/GetPriceToToman":
            return {"Data": {"TronPriceToman": 100_000}}
        return {"Data": {"FullPaymentUrl": "https://pay.example/1", "OrderID": "TrndOrderID_1"}}

    monkeypatch.setattr(provider, "_post", fake_post)
    quote = await provider.create_payment(
        payment_id="AH-T-1",
        amount_toman=500_000,
        callback_url="https://example.com/payments/tronado/webhook",
    )
    assert quote.asset == "TRX"
    assert quote.asset_amount == Decimal("5.000000")
    assert quote.provider_reference == "TrndOrderID_1"
    assert quote.payment_url.startswith("https://")
    assert calls[1][0] == "/api/v5/GetOrderToken"
    await provider.close()


def test_tronado_webhook_signature():
    provider = TronadoProvider(
        api_key="key",
        ipn_signing_key="secret",
        wallet_address="TXYZ",
    )
    raw = json.dumps({"PaymentID": "AH-T-1", "IsPaid": True}).encode()
    signature = hmac.new(b"secret", raw, hashlib.sha512).hexdigest()
    assert provider.verify_webhook(raw, signature)["PaymentID"] == "AH-T-1"
    with pytest.raises(Exception):
        provider.verify_webhook(raw, "bad")

    import asyncio
    asyncio.run(provider.close())

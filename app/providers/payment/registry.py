from __future__ import annotations

from app.config.settings import get_settings
from app.providers.payment.base import BasePaymentProvider
from app.providers.payment.tronado import TronadoProvider

PAYMENT_PROVIDERS: dict[str, type[BasePaymentProvider]] = {
    "TRONADO": TronadoProvider,
}


def build_payment_provider(provider_type: str) -> BasePaymentProvider:
    settings = get_settings()
    provider_cls = PAYMENT_PROVIDERS.get(provider_type.upper())
    if provider_cls is None:
        raise ValueError(f"Payment provider not supported: {provider_type}")
    if provider_cls is TronadoProvider:
        return provider_cls(
            api_key=settings.tronado_api_key,
            ipn_signing_key=settings.tronado_ipn_signing_key,
            wallet_address=settings.tronado_wallet_address,
            base_url=settings.tronado_base_url,
            wage_from_business_percentage=settings.tronado_wage_from_business_percentage,
        )
    raise ValueError(f"Provider configuration missing: {provider_type}")

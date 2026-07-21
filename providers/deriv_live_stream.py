"""Application singleton for shared live Deriv subscriptions."""
from providers.provider_router import get_provider
from providers.deriv_subscription_manager import DerivSubscriptionManager
_manager=None
def get_deriv_live_manager():
    global _manager
    if _manager is None:
        provider=get_provider(provider="deriv",asset_class="derived_index")
        from analysis.derived_intelligence_service import get_derived_intelligence_service
        _manager=DerivSubscriptionManager(provider,analysis_callback=get_derived_intelligence_service(provider).completed_m5)
    return _manager

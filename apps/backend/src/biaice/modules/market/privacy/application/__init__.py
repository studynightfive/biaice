"""Application services for FR-12 privacy resources."""

from biaice.modules.market.privacy.application.services import (
    MarketResourceService,
    configure_market_privacy_services,
    get_market_resource_service,
)

__all__ = [
    "MarketResourceService",
    "configure_market_privacy_services",
    "get_market_resource_service",
]

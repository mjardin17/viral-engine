"""
storyforge2.merch.connectors -- POD vendor connectors.

Only Printful is implemented. Printify and Gooten have real APIs and are the
next candidates; Redbubble, Spring and Amazon Merch have no usable submission
API and will never get a connector here -- they get an upload package instead.
"""

from .base import (
    MerchConnector,
    MerchPublishRequest,
    MerchVariant,
    PublishingConnectorResult,
)
from .printful import PrintfulConnector

__all__ = [
    "MerchConnector",
    "MerchPublishRequest",
    "MerchVariant",
    "PublishingConnectorResult",
    "PrintfulConnector",
]

"""
connector_core -- vocabulary shared by every publishing pipeline.

Extracted because books and merch both need to answer the same question --
does this platform expose a real submission API, a gated one, or only a web
form? -- and neither should have to import the other to ask it.

Before this package existed, `merch` imported `storyforge2.publishing`, which
made a physical-goods pipeline depend on a book module for a concept that has
nothing to do with books. The dependency now points at neutral ground:

    storyforge2.publishing ---> connector_core <--- merch

Nothing product-specific belongs here. Book platforms live in
`storyforge2/publishing/registry.py`; POD channels live in
`merch/channels.py`. This package holds only the shape they share.
"""

from .registry import (
    CapabilityRegistry,
    ConnectorStatus,
    PlatformCapability,
)
from .result import ConnectorResult

__all__ = [
    "CapabilityRegistry",
    "ConnectorStatus",
    "PlatformCapability",
    "ConnectorResult",
]

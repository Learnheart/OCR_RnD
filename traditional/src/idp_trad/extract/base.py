"""★ CONTRACT — ParseEngine ABC (mirrors hybrid's interface).

Every extraction engine implements `parse(page) -> list[Block]` so engines are
swappable and A/B-comparable on the same OmniDocBench harness.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from idp_trad.ingest.loader import LoadedPage
from idp_trad.schemas import Block


class ParseEngine(ABC):
    """Extract one loaded page → list of Blocks (with reading_order set)."""

    #: name written into DocumentResult.engines_used
    name: str = "base"

    @abstractmethod
    def parse(self, page: LoadedPage) -> list[Block]:
        """Return list[Block] for one page. Engine assigns reading_order."""
        raise NotImplementedError

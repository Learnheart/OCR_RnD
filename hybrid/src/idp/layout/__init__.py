"""S2 — Layout detection (định tuyến region)."""

from idp.layout.base import LABEL_TO_GROUP, LayoutDetector, label_to_group
from idp.layout.ppstructure_layout import PPStructureLayoutDetector

__all__ = [
    "LayoutDetector",
    "LABEL_TO_GROUP",
    "label_to_group",
    "PPStructureLayoutDetector",
]

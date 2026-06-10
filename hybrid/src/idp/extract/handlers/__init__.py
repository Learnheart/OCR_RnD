"""S3 — Fan-out handlers (text/table/formula/chart/seal)."""

from idp.extract.handlers.base import RegionHandler, build_registry, crop_region
from idp.extract.handlers.registry import default_handlers

__all__ = ["RegionHandler", "crop_region", "build_registry", "default_handlers"]

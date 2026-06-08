"""idp_trad — traditional (non-VLM) OCR pipeline for OmniDocBench.

Self-contained sibling of `hybrid/`'s `idp` package. Same output contract
(Block/PageResult/DocumentResult → Markdown) so eval numbers are comparable,
but the extraction engine is classic OCR (PaddleOCR PP-OCRv4 + PP-Structure),
not a VLM.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"

"""heavycon_analyzer.

Offline, CPU-only toolkit for extracting BIMCO HEAVYCON 2007 (Standard Heavy
Lift Charter Party) PART I Box 1-30 fields from scanned PDFs.

Importing this package pulls in ZERO third-party libraries. All OCR/PDF/imaging
dependencies live behind lazy-import adapters in later modules so that the core
data model, box definitions, and exporters remain fully usable and testable
offline with only the Python standard library.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]

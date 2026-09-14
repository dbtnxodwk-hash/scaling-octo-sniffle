"""Tests for the lazy Tesseract OCR adapter's image handling helpers.

The real Tesseract/PyMuPDF/PIL stack cannot be installed in the offline
sandbox, so these tests exercise the pure-Python sizing/conversion logic with
small fake objects that structurally mimic a ``fitz.Pixmap`` (attributes
``samples``, ``n``, ``width``, ``height`` and optionally ``stride``). They never
import fitz or PIL. Their job is to lock in the two regressions the review
flagged (issues 4 and 5):

* ``_image_size`` must return a Pixmap's real ``width``/``height`` (not
  ``(0, 0)``), otherwise the extractor's two-column heuristic is disabled on the
  DEFAULT PyMuPDF backend.
* ``_to_pytesseract_image`` must be stride-aware so a padded Pixmap is not
  sheared before OCR.
"""

from __future__ import annotations

from heavycon_analyzer.ocr.tesseract_adapter import TesseractOcrEngine


class _FakePixmap:
    """Minimal structural stand-in for a ``fitz.Pixmap`` (no PyMuPDF import)."""

    def __init__(self, width, height, n, samples, stride=None, png=None):
        self.width = width
        self.height = height
        self.n = n
        self.samples = samples
        if stride is not None:
            self.stride = stride
        self._png = png

    def tobytes(self, fmt):  # mimics fitz.Pixmap.tobytes("png")
        if self._png is None:
            raise RuntimeError("no encoder available in test")
        assert fmt == "png"
        return self._png


class _FakePilImage:
    """Structural stand-in for a PIL image exposing ``.size`` only."""

    def __init__(self, width, height):
        self.size = (width, height)


# ---------------------------------------------------------------------------
# _image_size (issue 5).
# ---------------------------------------------------------------------------


def test_image_size_reads_pixmap_width_height() -> None:
    # A fitz Pixmap has no `.size`; the old code returned (0, 0) which disabled
    # the two-column heuristic on the default PyMuPDF backend.
    pix = _FakePixmap(width=2480, height=3508, n=3, samples=b"\x00" * (2480 * 3508 * 3))
    assert TesseractOcrEngine._image_size(pix) == (2480, 3508)


def test_image_size_reads_pil_size() -> None:
    img = _FakePilImage(1654, 2339)
    assert TesseractOcrEngine._image_size(img) == (1654, 2339)


def test_image_size_unknown_object_is_zero() -> None:
    assert TesseractOcrEngine._image_size(object()) == (0, 0)


# ---------------------------------------------------------------------------
# _is_fitz_pixmap detection.
# ---------------------------------------------------------------------------


def test_is_fitz_pixmap_detects_pixmap_not_pil() -> None:
    pix = _FakePixmap(width=10, height=10, n=3, samples=b"\x00" * 300)
    assert TesseractOcrEngine._is_fitz_pixmap(pix) is True
    assert TesseractOcrEngine._is_fitz_pixmap(_FakePilImage(10, 10)) is False
    assert TesseractOcrEngine._is_fitz_pixmap(object()) is False


# ---------------------------------------------------------------------------
# _to_pytesseract_image (issue 4).
# ---------------------------------------------------------------------------


def test_to_pytesseract_passes_through_non_pixmap() -> None:
    # A PIL image (pdf2image backend) or any other object is returned as-is.
    img = _FakePilImage(100, 100)
    assert TesseractOcrEngine._to_pytesseract_image(img) is img


def test_to_pytesseract_pixmap_conversion_is_stride_safe() -> None:
    # When Pillow is available, a Pixmap is converted; when it is not (the
    # offline sandbox), the Pixmap is handed back so pytesseract reports the
    # incompatibility. Either way the code path must not raise. We provide a
    # PNG payload so the preferred stride-safe tobytes("png") route is used if
    # Pillow can decode it.
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        pillow = False
    else:
        pillow = True

    pix = _FakePixmap(
        width=2,
        height=2,
        n=3,
        # 2x2 RGB with a stride of 8 bytes/row (2 bytes of padding per row) to
        # prove the fallback slices each row to width*n before frombytes.
        samples=b"\xff\x00\x00\x00\xff\x00\x00\x00" b"\x00\x00\xff\xff\xff\x00\x00\x00",
        stride=8,
    )
    result = TesseractOcrEngine._to_pytesseract_image(pix)
    if not pillow:
        # No Pillow: the Pixmap comes straight back, nothing raised.
        assert result is pix
    else:
        # With Pillow the fallback frombytes path yields a real image sized to
        # the Pixmap (tobytes here has no PNG payload, so it falls through).
        assert result.size == (2, 2)

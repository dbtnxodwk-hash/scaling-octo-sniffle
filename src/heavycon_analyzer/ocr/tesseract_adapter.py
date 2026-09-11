"""Real OCR adapter backed by Tesseract via ``pytesseract``.

The third-party dependency (``pytesseract``) and the Tesseract engine itself
are only needed on a real machine. To keep the package importable in a fully
offline environment (no ``pytesseract``, no Tesseract binary), the import is
LAZY: it happens inside :meth:`TesseractOcrEngine.image_to_page`, never at
module import time. When the dependency or engine is missing we raise a clear,
actionable :class:`RuntimeError` pointing the user at the README.
"""

from __future__ import annotations

from typing import Any

from ..model import OcrPage, parse_tesseract_tsv

__all__ = ["TesseractOcrEngine", "MISSING_TESSERACT_MESSAGE"]

# Shown whenever pytesseract or the Tesseract engine cannot be used. Kept as a
# module constant so tests can assert on it and the wording stays consistent.
MISSING_TESSERACT_MESSAGE = (
    "Tesseract OCR engine not found; install it and the `ocr` optional " "dependencies. See README."
)

# Default page dimensions used only when Tesseract does not report them.
_DEFAULT_DPI_NOTE = "eng"


class TesseractOcrEngine:
    """OCR engine that shells out to Tesseract through ``pytesseract``.

    Args:
        language: Tesseract language code(s), e.g. ``"eng"`` (default) or
            ``"eng+deu"``. Passed straight through as the ``lang`` argument.
        tesseract_cmd: Optional absolute path to the ``tesseract`` executable.
            On Windows this is typically
            ``C:\\Program Files\\Tesseract-OCR\\tesseract.exe``. When provided
            it is set on ``pytesseract.pytesseract.tesseract_cmd`` so the engine
            can be found without adjusting the system ``PATH``.
        config: Extra command-line config string passed to Tesseract
            (e.g. ``"--psm 6"``).

    The engine satisfies the :class:`~heavycon_analyzer.ocr.port.OcrEngine`
    Protocol structurally.
    """

    def __init__(
        self,
        language: str = "eng",
        tesseract_cmd: str | None = None,
        config: str = "",
    ) -> None:
        self.language = language or _DEFAULT_DPI_NOTE
        self.tesseract_cmd = tesseract_cmd
        self.config = config

    def _load_pytesseract(self) -> Any:
        """Import ``pytesseract`` lazily, translating failure into guidance."""
        try:
            import pytesseract  # noqa: PLC0415  (intentional lazy import)
        except Exception as exc:  # ImportError and any transitive failure.
            raise RuntimeError(MISSING_TESSERACT_MESSAGE) from exc

        if self.tesseract_cmd:
            # ``pytesseract.pytesseract`` is the internal module holding the
            # configurable command path.
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        return pytesseract

    def image_to_page(self, image: Any, page_index: int) -> OcrPage:
        """Run Tesseract on ``image`` and return the recognised tokens.

        Uses Tesseract's TSV output (``image_to_data``) and reuses
        :func:`heavycon_analyzer.model.parse_tesseract_tsv` so the token model
        is identical to the one exercised by the fixture-driven tests.

        Raises:
            RuntimeError: if ``pytesseract`` is not installed or the Tesseract
                engine/binary cannot be invoked.
        """
        pytesseract = self._load_pytesseract()

        # pytesseract expects a PIL.Image (or a path). The PDF rasterizer's
        # PyMuPDF backend hands us fitz Pixmap objects, which pytesseract cannot
        # consume directly, so normalise to a PIL image first. Kept lazy (only
        # runs on a real machine where Pillow/PyMuPDF are installed) so offline
        # import safety is preserved.
        ocr_image = self._to_pytesseract_image(image)

        try:
            # Output.STRING gives us the raw TSV text that our parser expects.
            tsv_text = pytesseract.image_to_data(
                ocr_image,
                lang=self.language,
                config=self.config,
                output_type=pytesseract.Output.STRING,
            )
        except Exception as exc:
            # Covers TesseractNotFoundError and any runtime engine failure.
            raise RuntimeError(MISSING_TESSERACT_MESSAGE) from exc

        width, height = self._image_size(ocr_image)
        return parse_tesseract_tsv(
            tsv_text,
            page_index=page_index,
            page_width=width,
            page_height=height,
        )

    @staticmethod
    def _is_fitz_pixmap(image: Any) -> bool:
        """Structurally detect a ``fitz.Pixmap`` without importing fitz.

        A Pixmap exposes raw ``.samples`` bytes plus channel count ``.n`` and
        integer ``.width``/``.height``. PIL images have ``.size`` but no
        ``.samples``/``.n``, so this reliably distinguishes the two backends.
        """
        samples = getattr(image, "samples", None)
        n_channels = getattr(image, "n", None)
        width = getattr(image, "width", None)
        height = getattr(image, "height", None)
        return samples is not None and bool(n_channels) and bool(width) and bool(height)

    @staticmethod
    def _to_pytesseract_image(image: Any) -> Any:
        """Return an image object pytesseract accepts.

        The PyMuPDF rasterizer yields ``fitz.Pixmap`` objects; pytesseract only
        handles PIL images or file paths, so we convert a Pixmap to a PIL image.

        Stride-safety (issue 4): a Pixmap's ``.samples`` buffer can carry per-row
        padding (``.stride`` > ``width * n``) and, for RGBA pages, premultiplied
        alpha. Feeding that raw buffer straight to ``Image.frombytes`` (the old
        approach) would shear the image or mishandle alpha and silently degrade
        OCR. We therefore prefer ``pixmap.tobytes("png")`` -- PyMuPDF encodes a
        correct, stride-normalised PNG which we hand to ``Image.open``. Only if
        ``tobytes`` is unavailable do we fall back to a stride-aware
        ``frombytes`` (slicing each row to ``width * n`` bytes when a stride is
        reported). This path only runs on a real machine with Pillow + PyMuPDF
        installed; imports stay lazy so offline import safety is preserved. It
        cannot execute in the offline sandbox, hence the defensive structure.
        """
        if not TesseractOcrEngine._is_fitz_pixmap(image):
            # PIL images (pdf2image backend) and anything else: pass through.
            return image

        try:
            from PIL import Image  # noqa: PLC0415  (intentional lazy import)
        except Exception:
            # No Pillow available: hand the object back and let pytesseract
            # report the incompatibility itself.
            return image

        # Preferred, stride-safe route: let PyMuPDF encode a proper PNG.
        tobytes = getattr(image, "tobytes", None)
        if callable(tobytes):
            try:
                import io  # noqa: PLC0415  (stdlib; kept local for symmetry)

                png_bytes = tobytes("png")
                return Image.open(io.BytesIO(png_bytes))
            except Exception:
                # Fall through to the manual conversion below.
                pass

        # Fallback: manual frombytes, but honour the row stride so any padding
        # does not shear the image. Attributes are guaranteed present because
        # _is_fitz_pixmap already verified them.
        width = int(image.width)
        height = int(image.height)
        n_channels = int(image.n)
        samples = image.samples
        mode = "RGBA" if n_channels >= 4 else "RGB" if n_channels == 3 else "L"
        stride = getattr(image, "stride", None)
        row_bytes = width * n_channels
        if stride and int(stride) != row_bytes:
            stride = int(stride)
            packed = bytearray()
            mv = memoryview(samples)
            for row in range(height):
                start = row * stride
                packed += mv[start : start + row_bytes]
            samples = bytes(packed)
        return Image.frombytes(mode, (width, height), samples)

    @staticmethod
    def _image_size(image: Any) -> tuple[int, int]:
        """Best-effort (width, height) for ``image`` without hard dependencies.

        Issue 5: a ``fitz.Pixmap`` has no ``.size`` attribute, so the previous
        implementation returned ``(0, 0)`` for the DEFAULT PyMuPDF backend. Page
        width 0 then disabled the extractor's two-column heuristic, collapsing
        every PyMuPDF-rendered page to single-column. We now read ``.width`` /
        ``.height`` off a Pixmap directly (and still honour PIL ``.size``), so
        the two-column split engages in production. Unknown objects fall back to
        ``(0, 0)`` (single-column), matching the extractor's contract.
        """
        # fitz Pixmap: integer width/height attributes.
        if TesseractOcrEngine._is_fitz_pixmap(image):
            try:
                return int(image.width), int(image.height)
            except (TypeError, ValueError):
                return 0, 0

        # PIL image: a (width, height) tuple.
        size = getattr(image, "size", None)
        if isinstance(size, (tuple, list)) and len(size) == 2:
            try:
                return int(size[0]), int(size[1])
            except (TypeError, ValueError):
                return 0, 0
        return 0, 0

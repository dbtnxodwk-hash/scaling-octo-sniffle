# Test fixtures

Synthetic OCR fixtures used to drive extraction/export tests offline, without a
real Tesseract engine. Files here mimic Tesseract's TSV (`image_to_data`)
output so tests can exercise the pure-stdlib core with zero third-party deps.

# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building the HEAVYCON 2007 analyzer Windows .exe.

Build (on a Windows host WITH network access to install PyInstaller):

    py -m pip install pyinstaller
    py -m pip install .[ocr]          # pytesseract, Pillow, PyMuPDF
    py -m PyInstaller --noconfirm packaging/heavycon_analyzer.spec

The resulting single-window executable appears at:

    dist/HeavyconAnalyzer/HeavyconAnalyzer.exe   (onedir, default below)

ENTRY POINT: PyInstaller runs the Analysis entry-point script as a nameless
top-level ``__main__`` module, NOT as a submodule of a package. Pointing it at
``src/heavycon_analyzer/__main__.py`` (which uses relative imports meant for
``python -m heavycon_analyzer``) crashes at runtime with
"attempted relative import with no known parent package". We therefore use the
dedicated ``launcher.py`` top-level script, which imports the package
*absolutely* and delegates to its ``main()``. ``collect_submodules`` makes sure
the whole ``heavycon_analyzer`` package (gui/ocr/pdf/export subpackages) is
bundled even though the launcher only imports it indirectly.

IMPORTANT: this .exe bundles only the Python code and its Python dependencies.
It does NOT bundle the Tesseract OCR *engine*. The Tesseract engine must be
installed separately on the target machine (see README.md), and its path set
via the app / TESSERACT path configuration. The build itself is NOT runnable in
the offline sandbox because PyInstaller cannot be installed there.
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Bundle the entire package (including gui/ocr/pdf/export subpackages) so the
# lazily/relatively imported submodules are all present in the frozen app.
hidden_imports = collect_submodules("heavycon_analyzer")
# PyMuPDF (fitz) and pytesseract are imported lazily; list them so
# PyInstaller's static analysis does not miss them.
hidden_imports += ["fitz", "pytesseract", "PIL"]


a = Analysis(
    ["launcher.py"],
    pathex=["../src"],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HeavyconAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # --windowed: no console window for a desktop GUI app.
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HeavyconAnalyzer",
)

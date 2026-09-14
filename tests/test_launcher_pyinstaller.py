"""Regression tests for the PyInstaller entry-point (relative-import) bug.

The user's ``HeavyconAnalyzer.exe`` crashed on launch with::

    ImportError: attempted relative import with no known parent package

Root cause: PyInstaller ran ``src/heavycon_analyzer/__main__.py`` as a nameless
top-level ``__main__`` module, so ``from .gui.app import run`` had no parent
package. The fix is a dedicated top-level ``packaging/launcher.py`` that imports
the package *absolutely*.

We cannot build a real ``.exe`` in the sandbox (PyInstaller is not installable
offline), so we reproduce the exact failure mode instead: execute a script as a
nameless top level (``runpy.run_path``) with only ``src/`` on ``sys.path`` and
assert it does NOT raise the relative-import ImportError and DOES reach the
package ``main()``. tkinter/mainloop is stubbed so the test stays headless.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
_LAUNCHER = _ROOT / "packaging" / "launcher.py"


def _run_as_top_level_script(script: Path) -> subprocess.CompletedProcess[str]:
    """Run *script* the way PyInstaller runs its entry point: as top-level.

    ``runpy.run_path(script)`` executes the file under the module name
    ``__main__`` with NO parent package -- exactly the context that broke the
    relative imports. We stub ``gui.app.run`` so nothing tries to open a window.
    """
    driver = (
        "import runpy, sys\n"
        f"sys.path.insert(0, {str(_SRC)!r})\n"
        # Prevent a real window: replace the GUI entry with a marker.
        "import heavycon_analyzer.gui.app as app\n"
        "app.run = lambda: print('REACHED_MAIN')\n"
        f"runpy.run_path({str(script)!r}, run_name='__main__')\n"
    )
    return subprocess.run(
        [sys.executable, "-c", driver],
        capture_output=True,
        text=True,
    )


def test_launcher_runs_as_top_level_script_without_relative_import_error() -> None:
    result = _run_as_top_level_script(_LAUNCHER)

    assert "attempted relative import" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr
    assert "REACHED_MAIN" in result.stdout


def test_package_main_as_top_level_reproduces_original_crash() -> None:
    """Sanity check that the OLD approach (package __main__ as top level) fails.

    This proves the launcher is doing real work: running the package's own
    ``__main__.py`` as a nameless top-level script still triggers the exact
    ImportError the user reported. If this ever stops failing, the regression
    guard above may be testing nothing.
    """
    pkg_main = _SRC / "heavycon_analyzer" / "__main__.py"
    result = _run_as_top_level_script(pkg_main)

    assert result.returncode != 0
    assert "attempted relative import with no known parent package" in result.stderr


def test_launcher_uses_absolute_import() -> None:
    """The launcher must NOT rely on relative imports."""
    text = _LAUNCHER.read_text(encoding="utf-8")
    assert "from heavycon_analyzer" in text
    # No line should be a relative import statement (docstring prose is fine).
    for line in text.splitlines():
        assert not line.lstrip().startswith("from ."), line

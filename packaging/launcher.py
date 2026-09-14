"""Top-level launcher script for the PyInstaller build.

PyInstaller runs its Analysis *entry-point script* as a nameless top-level
``__main__`` module -- it is NOT imported as a submodule of a package. That
means a script using **relative** imports (``from .gui.app import run``) fails
at runtime with::

    ImportError: attempted relative import with no known parent package

``src/heavycon_analyzer/__main__.py`` is exactly such a file (it is designed to
be run via ``python -m heavycon_analyzer``, where Python *does* set the parent
package). Pointing PyInstaller at it directly reproduces the crash the user
saw when double-clicking ``HeavyconAnalyzer.exe``.

This launcher exists solely to be that top-level entry point. It uses an
**absolute** import of the installed package, so no parent-package context is
required, and then delegates to the package's own ``main()``. The bundled
``heavycon_analyzer`` package keeps working with its normal (relative) imports
because it is imported here as a proper package.
"""

from __future__ import annotations

from heavycon_analyzer.__main__ import main

if __name__ == "__main__":
    main()

"""Desktop GUI for heavycon_analyzer.

Split into two modules:

* :mod:`heavycon_analyzer.gui.controller` -- pure, headless logic (row
  formatting + export triggers). No tkinter imports, so it is fully
  unit-testable without a display.
* :mod:`heavycon_analyzer.gui.app` -- the tkinter widgets that call into the
  controller. Importing it requires tkinter (stdlib) but not a display.
"""

__all__: list[str] = []

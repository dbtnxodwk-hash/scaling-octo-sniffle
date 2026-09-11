"""Package entry point: ``python -m heavycon_analyzer`` launches the GUI.

Matches the ``[project.scripts]`` entry in ``pyproject.toml``
(``heavycon-analyzer = heavycon_analyzer.__main__:main``). The tkinter import
is deferred into :func:`main` so that merely importing this module (e.g. for
introspection) does not require a display or the tkinter runtime.
"""

from __future__ import annotations


def main() -> None:
    """Launch the HEAVYCON analyzer desktop window."""
    from .gui.app import run

    run()


if __name__ == "__main__":
    main()

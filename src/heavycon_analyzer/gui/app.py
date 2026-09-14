"""tkinter desktop window for heavycon_analyzer.

This module wires the analysis pipeline to a simple desktop UI:

* **분석할 PDF 열기** (Open PDF) -- pick a scanned HEAVYCON 2007 PDF.
* **분석 실행** (Analyze) -- run OCR + extraction on a background thread so the
  window stays responsive, updating a status/progress indicator.
* A ``ttk.Treeview`` table with columns 「Box 번호 / 항목(영문) / 항목(한글) / 값」
  populated from the extracted fields.
* **CSV 내보내기 / XLSX 내보내기** -- save the table to file.

All non-widget logic lives in :mod:`heavycon_analyzer.gui.controller` so it can
be unit-tested without a display. tkinter is a standard-library module, so
importing this file is safe offline; only *running* the analysis needs the
Tesseract engine and PDF/imaging libraries. If those are missing, the adapters
raise ``RuntimeError`` and we surface a clear message box pointing at the
README.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..model import ExtractedField
from ..pipeline import analyze_pdf, build_default_pipeline
from . import controller

__all__ = ["HeavyconAnalyzerApp", "run"]

_WINDOW_TITLE = "HEAVYCON 2007 계약서 분석기"


class HeavyconAnalyzerApp:
    """The main application window.

    Widget construction happens in ``__init__``; the analysis runs on a worker
    thread and results are marshalled back to the Tk main loop through a
    :class:`queue.Queue` polled by :meth:`_poll_result`. This keeps every Tk
    call on the main thread (tkinter is not thread-safe).
    """

    def __init__(self, master: tk.Misc) -> None:
        self.master = master
        master.title(_WINDOW_TITLE)

        self._pdf_path: str | None = None
        self._fields: list[ExtractedField] = []
        self._result_queue: queue.Queue = queue.Queue()
        self._running = False

        self._build_widgets()

    # -- widget construction -------------------------------------------------
    def _build_widgets(self) -> None:
        toolbar = ttk.Frame(self.master, padding=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.open_button = ttk.Button(toolbar, text="분석할 PDF 열기", command=self.on_open_pdf)
        self.open_button.pack(side=tk.LEFT)

        self.analyze_button = ttk.Button(
            toolbar, text="분석 실행", command=self.on_analyze, state=tk.DISABLED
        )
        self.analyze_button.pack(side=tk.LEFT, padx=(8, 0))

        self.csv_button = ttk.Button(
            toolbar, text="CSV 내보내기", command=self.on_export_csv, state=tk.DISABLED
        )
        self.csv_button.pack(side=tk.LEFT, padx=(8, 0))

        self.xlsx_button = ttk.Button(
            toolbar, text="XLSX 내보내기", command=self.on_export_xlsx, state=tk.DISABLED
        )
        self.xlsx_button.pack(side=tk.LEFT, padx=(8, 0))

        # Table.
        table_frame = ttk.Frame(self.master, padding=(8, 0))
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = tuple(f"c{i}" for i in range(len(controller.TABLE_COLUMNS)))
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        widths = (80, 320, 200, 420)
        for col_id, heading, width in zip(columns, controller.TABLE_COLUMNS, widths, strict=True):
            self.tree.heading(col_id, text=heading)
            anchor = tk.CENTER if heading == controller.TABLE_COLUMNS[0] else tk.W
            self.tree.column(col_id, width=width, anchor=anchor, stretch=True)

        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar + progress.
        status_frame = ttk.Frame(self.master, padding=8)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="PDF 파일을 열어 주세요.")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=160)
        self.progress.pack(side=tk.RIGHT)

    # -- button handlers -----------------------------------------------------
    def on_open_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="분석할 PDF 열기",
            filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        self._pdf_path = path
        self.analyze_button.configure(state=tk.NORMAL)
        self.status_var.set(f"선택한 파일: {path}")

    def on_analyze(self) -> None:
        if self._running or not self._pdf_path:
            return
        self._running = True
        self._set_busy(True)
        self.status_var.set("분석 중입니다... (OCR 실행)")

        worker = threading.Thread(target=self._run_analysis, args=(self._pdf_path,), daemon=True)
        worker.start()
        self.master.after(100, self._poll_result)

    def on_export_csv(self) -> None:
        self._export(controller.export_fields_csv, ".csv", "CSV 파일", "*.csv")

    def on_export_xlsx(self) -> None:
        self._export(controller.export_fields_xlsx, ".xlsx", "XLSX 파일", "*.xlsx")

    # -- background analysis -------------------------------------------------
    def _run_analysis(self, pdf_path: str) -> None:
        """Run on a worker thread; push a (ok, payload) tuple onto the queue."""
        try:
            fields = analyze_pdf(pdf_path, **build_default_pipeline())
            self._result_queue.put((True, fields))
        except Exception as exc:  # RuntimeError from adapters + anything else.
            self._result_queue.put((False, exc))

    def _poll_result(self) -> None:
        """Poll the worker queue on the Tk main thread and finish up."""
        try:
            ok, payload = self._result_queue.get_nowait()
        except queue.Empty:
            self.master.after(100, self._poll_result)
            return

        self._running = False
        self._set_busy(False)

        if ok:
            self._fields = list(payload)
            self._populate_table(self._fields)
            has_rows = bool(self._fields)
            state = tk.NORMAL if has_rows else tk.DISABLED
            self.csv_button.configure(state=state)
            self.xlsx_button.configure(state=state)
            self.status_var.set(f"분석 완료: {len(self._fields)}개 항목을 추출했습니다.")
        else:
            self.status_var.set("분석에 실패했습니다.")
            self._show_error(payload)

    # -- helpers -------------------------------------------------------------
    def _populate_table(self, fields: list[ExtractedField]) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in controller.fields_to_rows(fields):
            self.tree.insert("", tk.END, values=row)

    def _export(self, export_fn, default_ext: str, label: str, pattern: str) -> None:
        if not self._fields:
            messagebox.showinfo("내보내기", "먼저 PDF를 분석해 주세요.")
            return
        path = filedialog.asksaveasfilename(
            title=f"{label} 내보내기",
            defaultextension=default_ext,
            filetypes=[(label, pattern), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            export_fn(self._fields, path)
        except Exception as exc:
            messagebox.showerror("내보내기 오류", f"파일을 저장하지 못했습니다:\n{exc}")
            return
        self.status_var.set(f"저장 완료: {path}")
        messagebox.showinfo("내보내기", f"저장을 완료했습니다:\n{path}")

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.open_button.configure(state=state)
        self.analyze_button.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _show_error(self, exc: BaseException) -> None:
        """Show an actionable dialog for a failed analysis.

        Missing Tesseract/PDF backends surface as ``RuntimeError`` from the
        adapters; we relay their message (which already points at the README)
        so a non-developer knows to install the OCR engine.
        """
        messagebox.showerror(
            "분석 오류",
            "분석 중 오류가 발생했습니다.\n\n"
            f"{exc}\n\n"
            "Tesseract OCR 엔진과 PDF 관련 구성요소가 설치되어 있는지 "
            "README의 설치 안내를 확인해 주세요.",
        )


def run() -> None:
    """Create the Tk root window and start the event loop."""
    root = tk.Tk()
    HeavyconAnalyzerApp(root)
    root.mainloop()

#!/usr/bin/env python3
"""HTML → PDF converter — ⚠ THE LOW-LEVEL ESCAPE-HATCH EXAMPLE. READ THE OTHER NINE FIRST.

This file is deliberately written a level *below* the rest of examples/: it subclasses
raw `App` (not `TuiApp`), builds views by hand, and does its own geometry — `WindowColumn`,
`stack_beside`/`stack_below`, raw `Button(x, y, ...)` coordinates, and responsive math like
`browser_h = max(5, min(12, H - 17))`. None of that is how you normally write a cookieui
app; it exists to show what the high-level helpers (`TuiApp`, `page()`, `columns()`,
`win.layout()`, `fill_with()`, auto-quit/status/resize) are doing for you, and what's
available when you genuinely need manual control.

If you're learning the library, start with demo.py / quickdialogs.py / todo.py and come
back here last. If you're copying patterns into a new app, copy from those files — not
this one.

Extra dependencies (the only example that has any):  pip install playwright pillow
Usage:  python html2pdf.py [start_dir]
"""
import io
import sys
import argparse
import threading
from pathlib import Path
from typing import Optional

from PIL import Image
from playwright.sync_api import sync_playwright

from cookieui import (App, View, Label, TextInput, Button,
                      Widget, DEFAULT, FileBrowser,
                      WindowColumn, stack_below, stack_beside, bind_quit)

# ── Data ──────────────────────────────────────────────────────────────────────

PDF_SIZES = [
    ("A4       (210x297mm)",  {"width": "210mm", "height": "297mm"}),
    ("A3       (297x420mm)",  {"width": "297mm", "height": "420mm"}),
    ("A5       (148x210mm)",  {"width": "148mm", "height": "210mm"}),
    ("Letter   (8.5x11in)",   {"width": "8.5in", "height": "11in"}),
    ("Legal    (8.5x14in)",   {"width": "8.5in", "height": "14in"}),
    ("Tabloid  (11x17in)",    {"width": "11in",  "height": "17in"}),
]

MARGINS = [
    ("Default  (10 mm)",  {"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}),
    ("Narrow   (5 mm)",   {"top": "5mm",  "bottom": "5mm",  "left": "5mm",  "right": "5mm"}),
    ("No Border (0 mm)",  {"top": "0",    "bottom": "0",    "left": "0",    "right": "0"}),
]

_PAGE_PX = {
    "210mm": 794, "297mm": 1123, "148mm": 559,
    "8.5in": 816, "11in": 1056,
}

_HI_FI_SCALE = 2

_PDF_FIX_CSS = "* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }"

# ── Custom widgets ─────────────────────────────────────────────────────────────

class StatusBar(Widget):
    """Reads status text from the app on every draw frame — thread-safe.

    Lives inside a Window, so it inherits the window surface via write_over.
    """
    focusable = False

    def __init__(self, x: int, y: int, width: int, app: 'Html2PdfApp'):
        super().__init__(x, y, width, 1)
        self._app = app

    def draw(self, screen, theme) -> None:
        s = self._app._status
        if   s.startswith("Saved"): fg = theme.success
        elif s.startswith("Error"): fg = theme.error
        elif "wait" in s:           fg = theme.warning
        else:                       fg = theme.text
        screen.write_over(self.x, self.y, s[:self.width].ljust(self.width), fg=fg)


# ── PDF rendering ─────────────────────────────────────────────────────────────

def _do_convert(html_path: Path, output_path: Path, page_size: dict,
                margin: dict, landscape: bool, hifi: bool) -> None:
    key = page_size["height"] if landscape else page_size["width"]
    vp  = _PAGE_PX.get(key, 1440)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": vp, "height": 900},
            device_scale_factor=_HI_FI_SCALE if hifi else 1,
        )
        page = context.new_page()
        page.emulate_media(media="screen")
        page.goto(html_path.resolve().as_uri(),
                  wait_until="networkidle", timeout=60_000)
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('style'))"
            "      .some(s => s.textContent.length > 50)",
            timeout=10_000,
        )
        page.wait_for_timeout(500)

        if hifi:
            img = Image.open(io.BytesIO(page.screenshot(full_page=True, type="png")))
            img.save(str(output_path), "PDF", resolution=96 * _HI_FI_SCALE)
        else:
            page.evaluate(
                f"() => {{ const s = document.createElement('style');"
                f" s.textContent = `{_PDF_FIX_CSS}`;"
                f" document.head.appendChild(s); }}"
            )
            page.pdf(
                path=str(output_path),
                width=page_size["width"],
                height=page_size["height"],
                landscape=landscape,
                print_background=True,
                margin=margin,
            )
        browser.close()


# ── App ───────────────────────────────────────────────────────────────────────

class Html2PdfApp(App):
    """Built on the lower-level App/View API rather than TuiApp — the example of going
    below the convenience layer. It owns its construction (`_build_view`), runs a
    background conversion thread, and uses a custom thread-safe StatusBar, so it wires
    quit (and would wire status) itself instead of relying on TuiApp's auto-behaviour.
    """

    def __init__(self, start_dir: Path):
        super().__init__(theme=DEFAULT)
        self._start_dir  = start_dir
        self._html_path: Optional[Path] = None
        self._status     = "Select an HTML file to begin"
        self._converting = False
        self._build_view()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_view(self) -> None:
        H = self._terminal.height
        t = self.theme

        lx  = 2
        top = 1

        # WindowColumn stacks windows vertically, auto-reserving each drop shadow
        # plus one gap row (gap=1) — no manual SHADOW/VGAP math. stack_beside() gives
        # the right column's X (shadow column + clear columns). Tab order follows the
        # order focusable children are added below.
        view = View()

        # ── Left column: file browser (floating widget) then stacked windows ──
        browser_w = 60
        browser_h = max(5, min(12, H - 17))
        self._browser = FileBrowser(lx, top, browser_w, browser_h, self._start_dir,
                                    on_select=self._on_file_selected,
                                    extensions={'.html', '.htm'})
        view.add(self._browser)                       # focusable: browser

        left = WindowColumn(view, x=lx, y=stack_below(top, browser_h),
                            width=browser_w, gap=1)

        out_win = left.window(3, title="Output File")
        lay = out_win.layout()                        # content anchor — no x/y/width math
        inp_w = lay.width - 6                          # leave room for " .pdf"
        self._out_input = TextInput(lay.x, lay.y, inp_w, placeholder="filename")
        ext_lbl = Label(lay.x + inp_w + 1, lay.y, ".pdf", color=t.title_fg)
        out_win.add(self._out_input, ext_lbl)         # focusable: output input

        # ── Right column: page size / margins / options ──
        right = WindowColumn(view, x=stack_beside(lx, browser_w), y=top, gap=1)

        size_win = right.window(len(PDF_SIZES) + 2, title="Page Size", width=29)
        self._size_radio = size_win.layout().radio_group(PDF_SIZES)    # rows carry size dict (auto-added)

        margin_win = right.window(len(MARGINS) + 2, title="Margins", width=25)
        self._margin_radio = margin_win.layout().radio_group(MARGINS)  # rows carry margin dict (auto-added)

        opt_win = right.window(4, title="Options", width=25)  # border + 2 checkboxes + border
        opt = opt_win.layout(spacing=0)               # two adjacent checkbox rows (auto-added)
        self._landscape = opt.checkbox("Landscape")
        self._hifi      = opt.checkbox("High Fidelity")

        # ── Status window + convert button (bottom of the left column) ──
        status_win = left.window(3, title="Status")
        slay = status_win.layout()
        status_bar = StatusBar(slay.x, slay.y, slay.width, self)

        btn_w = 20
        btn_x = lx + (browser_w - btn_w) // 2
        self._conv_btn = Button(btn_x, left.y, "Convert to PDF", on_click=self._on_convert)
        view.add(self._conv_btn)                      # focusable: convert button

        status_win.add(status_bar)                    # non-focusable status text

        # q / Esc quits (ignored while typing in the filename field)
        bind_quit(view, self.quit)
        self.push_view(view)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_file_selected(self, path: Path) -> None:
        self._html_path = path
        self._out_input.set_value(path.stem)     # value + cursor at end, no private poke
        self._status    = f"Selected: {path.name}"

    def _on_convert(self) -> None:
        if self._converting:
            return
        if self._html_path is None:
            self._status = "Error: select an HTML file first"
            return
        name = self._out_input.value.strip()
        if not name:
            self._status = "Error: enter an output filename"
            return

        output_path      = self._html_path.parent / (name + ".pdf")
        page_size        = self._size_radio.selected_value
        margin           = self._margin_radio.selected_value
        landscape        = self._landscape.checked
        hifi             = self._hifi.checked
        self._converting = True
        self._status     = "Rendering — please wait…"

        def _run():
            try:
                _do_convert(self._html_path, output_path,
                            page_size, margin, landscape, hifi)
                self._status = f"Saved: {output_path.resolve()}"
            except Exception as exc:
                self._status = f"Error: {exc}"
            finally:
                self._converting = False

        threading.Thread(target=_run, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert HTML to PDF (CDN-aware).")
    parser.add_argument("start_dir", nargs="?", default=str(Path.cwd()),
                        help="Directory to open (default: current directory)")
    args = parser.parse_args()

    start_dir = Path(args.start_dir)
    if not start_dir.is_dir():
        print(f"Error: '{start_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    Html2PdfApp(start_dir).run()


if __name__ == "__main__":
    main()

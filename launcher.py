"""
launcher.py — Point-and-click front end for the lead-gen pipeline.

Run this instead of main.py directly:

    python launcher.py

It shows two buttons (Villas/Farmhouses/Bungalows, Hotels), updates
config.py automatically for the chosen category's search terms and
price range, runs main.py, streams progress, and then lets you browse
the resulting leads in a simple table — no command line, no editing
config.py by hand, no Excel required to check the results.
"""

import os
import re
import sys
import csv
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.py")
MAIN_PATH = os.path.join(SCRIPT_DIR, "main.py")

sys.path.insert(0, SCRIPT_DIR)
import config  # noqa: E402  (local config.py — read for presets/paths)

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SUBTITLE = ("Segoe UI", 11)
FONT_BODY = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 13, "bold")
COLOR_BG = "#f5f6fa"
COLOR_CARD = "#ffffff"
COLOR_ACCENT = "#2d6cdf"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#666666"


# ─────────────────────────────────────────────────────────────────────────
# config.py rewriting
# ─────────────────────────────────────────────────────────────────────────

def apply_category_to_config(category_key):
    """Rewrite SEARCH_QUERIES / PRICE_FILTER_MIN/MAX / PRICE_BAND_EDGES in
    config.py to match the chosen category preset. main.py is run as a
    fresh subprocess afterward, so it always reads the updated file."""
    preset = config.PROPERTY_TYPES[category_key]
    city = config.CITY
    price_min = min(lo for lo, _ in preset["default_bands"])
    price_max = max(hi for _, hi in preset["default_bands"])

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    queries_block = "SEARCH_QUERIES = [\n" + "".join(
        f'    f"{term} in {{CITY}}",\n' for term in preset["search_terms"]
    ) + "]"
    text = re.sub(r"SEARCH_QUERIES = \[.*?\]", queries_block, text, flags=re.DOTALL)

    text = re.sub(r"PRICE_FILTER_MIN = \d[\d_]*", f'PRICE_FILTER_MIN = {price_min}', text)
    text = re.sub(r"PRICE_FILTER_MAX = \d[\d_]*", f'PRICE_FILTER_MAX = {price_max}', text)

    bands_repr = "[" + ", ".join(f"({lo}, {hi})" for lo, hi in preset["default_bands"]) + "]"
    text = re.sub(r"PRICE_BAND_EDGES = \[.*?\]", f"PRICE_BAND_EDGES = {bands_repr}", text, flags=re.DOTALL)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    return preset, city


# ─────────────────────────────────────────────────────────────────────────
# Main application
# ─────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hospitality Lead Generator")
        self.geometry("760x560")
        self.configure(bg=COLOR_BG)
        self.minsize(680, 480)

        self.selected_category = None
        self.log_queue = queue.Queue()
        self.proc = None

        self.container = tk.Frame(self, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True)

        self.show_home()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── Screen 1: choose category ──────────────────────────────────────
    def show_home(self):
        self.clear()
        tk.Label(self.container, text=f"Hospitality Leads — {config.CITY}",
                  font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(30, 4))
        tk.Label(self.container, text="Choose what you want to collect leads for:",
                  font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_MUTED).pack(pady=(0, 24))

        cards = tk.Frame(self.container, bg=COLOR_BG)
        cards.pack(pady=10)

        for key, preset in config.PROPERTY_TYPES.items():
            self._build_category_card(cards, key, preset)

        tk.Label(self.container,
                  text="Each category searches Google Places + Booking.com and\n"
                       "saves contact-ready leads split into price ranges.",
                  font=FONT_BODY, bg=COLOR_BG, fg=COLOR_MUTED, justify="center").pack(pady=20)

    def _build_category_card(self, parent, key, preset):
        card = tk.Frame(parent, bg=COLOR_CARD, highlightbackground="#ddd",
                          highlightthickness=1, bd=0)
        card.pack(side="left", padx=14, pady=6, ipadx=16, ipady=16)

        icon = "🏡" if key == "villas" else "🏨"
        tk.Label(card, text=icon, font=("Segoe UI", 28), bg=COLOR_CARD).pack(pady=(4, 6))
        tk.Label(card, text=preset["label"], font=FONT_BUTTON, bg=COLOR_CARD,
                  fg=COLOR_TEXT, wraplength=200, justify="center").pack()
        p_min = min(lo for lo, _ in preset["default_bands"])
        p_max = max(hi for _, hi in preset["default_bands"])
        tk.Label(card, text=f'₹{p_min:,} – ₹{p_max:,} / night',
                  font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=(4, 2))

        bands_text = "\n".join(f"₹{lo:,} – ₹{hi:,}" for lo, hi in preset["default_bands"])
        tk.Label(card, text=bands_text, font=("Segoe UI", 9), bg=COLOR_CARD,
                  fg=COLOR_MUTED, justify="center").pack(pady=(2, 10))

        tk.Button(card, text="Select", font=FONT_BODY, bg=COLOR_ACCENT, fg="white",
                   activebackground="#1e54b7", relief="flat", padx=20, pady=6,
                   command=lambda k=key: self.show_confirm(k)).pack()

    # ── Screen 2: confirm & run ─────────────────────────────────────────
    def show_confirm(self, category_key):
        self.selected_category = category_key
        preset = config.PROPERTY_TYPES[category_key]
        p_min = min(lo for lo, _ in preset["default_bands"])
        p_max = max(hi for _, hi in preset["default_bands"])
        self.clear()

        tk.Label(self.container, text=preset["label"], font=FONT_TITLE,
                  bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(30, 6))
        tk.Label(self.container,
                  text=f'Searching for: {", ".join(preset["search_terms"])}\n'
                       f'Price range: ₹{p_min:,} – ₹{p_max:,} / night',
                  font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_MUTED, justify="center").pack(pady=(0, 20))

        btn_row = tk.Frame(self.container, bg=COLOR_BG)
        btn_row.pack(pady=10)
        tk.Button(btn_row, text="⬅ Back", font=FONT_BODY, relief="flat", padx=14, pady=6,
                   command=self.show_home).pack(side="left", padx=6)
        tk.Button(btn_row, text="▶ Start Collecting Leads", font=FONT_BUTTON,
                   bg=COLOR_ACCENT, fg="white", relief="flat", padx=18, pady=8,
                   command=self.start_run).pack(side="left", padx=6)

    # ── Screen 3: running ────────────────────────────────────────────────
    def start_run(self):
        preset, city = apply_category_to_config(self.selected_category)
        self.clear()

        tk.Label(self.container, text=f'Collecting: {preset["label"]}', font=FONT_TITLE,
                  bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(20, 4))
        self.status_label = tk.Label(self.container, text="Starting…", font=FONT_SUBTITLE,
                                       bg=COLOR_BG, fg=COLOR_MUTED)
        self.status_label.pack(pady=(0, 10))

        log_frame = tk.Frame(self.container, bg=COLOR_BG)
        log_frame.pack(fill="both", expand=True, padx=20, pady=6)
        self.log_text = tk.Text(log_frame, bg="#111111", fg="#c7f7c7",
                                  font=("Consolas", 9), wrap="word")
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btn_row = tk.Frame(self.container, bg=COLOR_BG)
        btn_row.pack(pady=10)
        self.cancel_btn = tk.Button(btn_row, text="Cancel", font=FONT_BODY, relief="flat",
                                      padx=14, pady=6, command=self.cancel_run)
        self.cancel_btn.pack(side="left", padx=6)

        env = os.environ.copy()
        env["LEADGEN_CATEGORY_LABEL"] = preset["label"]
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        self.proc = subprocess.Popen(
            [sys.executable, "-u", MAIN_PATH],
            cwd=SCRIPT_DIR, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        threading.Thread(target=self._read_output, daemon=True).start()
        self.after(150, self._poll_log_queue)

    def _read_output(self):
        for line in self.proc.stdout:
            self.log_queue.put(line)
        self.proc.wait()
        self.log_queue.put(None)  # sentinel: process finished

    def _poll_log_queue(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                if line is None:
                    self._on_run_finished()
                    return
                self.log_text.insert("end", line)
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    def cancel_run(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.status_label.config(text="Cancelled.")
        self.cancel_btn.config(state="disabled")

    def _on_run_finished(self):
        rc = self.proc.returncode if self.proc else -1
        if rc == 0:
            self.status_label.config(text="✅ Done!")
            self.cancel_btn.destroy()
            tk.Button(self.container, text="View Leads ➜", font=FONT_BUTTON, bg=COLOR_ACCENT,
                       fg="white", relief="flat", padx=18, pady=8,
                       command=self.show_results).pack(pady=6)
            tk.Button(self.container, text="Run Another Category", font=FONT_BODY, relief="flat",
                       padx=14, pady=6, command=self.show_home).pack(pady=4)
        else:
            self.status_label.config(text=f"⚠ Stopped (exit code {rc}). See log above.")
            self.cancel_btn.config(text="Back", command=self.show_home)

    # ── Screen 4: browse results ────────────────────────────────────────
    def show_results(self):
        self.clear()
        preset = config.PROPERTY_TYPES[self.selected_category]

        tk.Label(self.container, text="Your Leads", font=FONT_TITLE,
                  bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(16, 6))

        top = tk.Frame(self.container, bg=COLOR_BG)
        top.pack(fill="x", padx=20)

        band_files = [("All leads (this city)", config.OUTPUT_ALL_FILE)]
        for lo, hi in preset["default_bands"]:
            label = f"{lo}-{hi}"
            band_files.append((f"₹{lo:,} – ₹{hi:,}", config.OUTPUT_BAND_TEMPLATE.format(band=label)))

        tk.Label(top, text="Show:", font=FONT_BODY, bg=COLOR_BG).pack(side="left")
        choice_var = tk.StringVar(value=band_files[1][0] if len(band_files) > 1 else band_files[0][0])
        dropdown = ttk.Combobox(top, textvariable=choice_var, state="readonly",
                                  values=[b[0] for b in band_files], width=28)
        dropdown.pack(side="left", padx=8)

        tk.Label(top, text="Search name:", font=FONT_BODY, bg=COLOR_BG).pack(side="left", padx=(16, 4))
        search_var = tk.StringVar()
        tk.Entry(top, textvariable=search_var, width=24).pack(side="left")

        open_btn = tk.Button(top, text="Open in Excel/Spreadsheet App", font=FONT_BODY,
                               relief="flat", padx=10, pady=4)
        open_btn.pack(side="right")

        tree_frame = tk.Frame(self.container, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tree = ttk.Treeview(tree_frame, show="headings")
        vsb = tk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = tk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        count_label = tk.Label(self.container, text="", font=FONT_BODY, bg=COLOR_BG, fg=COLOR_MUTED)
        count_label.pack(pady=(0, 6))

        current_path = {"path": None}

        def load(*_):
            label = choice_var.get()
            path = dict(band_files)[label]
            current_path["path"] = path
            tree.delete(*tree.get_children())
            if not os.path.exists(path):
                tree["columns"] = ["Message"]
                tree.heading("Message", text="Message")
                tree.insert("", "end", values=(f"No file yet: {os.path.basename(path)}",))
                count_label.config(text="0 rows")
                return
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                count_label.config(text="0 rows")
                return
            header, data = rows[0], rows[1:]
            tree["columns"] = header
            for col in header:
                tree.heading(col, text=col)
                tree.column(col, width=110, anchor="w")

            q = search_var.get().strip().lower()
            if q and "NAME" in header:
                name_idx = header.index("NAME")
                data = [r for r in data if q in r[name_idx].lower()]

            for row in data:
                tree.insert("", "end", values=row)
            count_label.config(text=f"{len(data)} rows")

        def open_file():
            path = current_path["path"]
            if not path or not os.path.exists(path):
                messagebox.showinfo("Not found", "This file hasn't been created yet.")
                return
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path)  # noqa
                elif sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("Could not open file", str(e))

        dropdown.bind("<<ComboboxSelected>>", load)
        search_var.trace_add("write", lambda *_: load())
        open_btn.config(command=open_file)
        load()

        bottom = tk.Frame(self.container, bg=COLOR_BG)
        bottom.pack(pady=8)
        tk.Button(bottom, text="⬅ Run Another Category", font=FONT_BODY, relief="flat",
                   padx=14, pady=6, command=self.show_home).pack()


if __name__ == "__main__":
    App().mainloop()
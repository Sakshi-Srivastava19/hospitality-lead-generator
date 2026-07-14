"""
app.py — Local web server behind the HTML/CSS/JS UI.

Run:
    python app.py

Then open http://127.0.0.1:5000 in a browser. Pick a city, property type,
and price band(s), click Start — it rewrites config.py, runs main.py as a
subprocess, streams the log to the page, and lets you browse the resulting
leads in a searchable table once it's done.
"""

import os
import re
import sys
import csv
import glob
import uuid
import threading
import subprocess

from flask import Flask, jsonify, request, send_from_directory, abort

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.py")
MAIN_PATH = os.path.join(SCRIPT_DIR, "main.py")

sys.path.insert(0, SCRIPT_DIR)
import config  # noqa: E402  (local config.py — read for presets/paths)

app = Flask(__name__, static_folder="static", static_url_path="")

# In-memory run registry: run_id -> {"proc", "lines", "status", "returncode", "lock"}
RUNS = {}


# ─────────────────────────────────────────────────────────────────────────
# config.py rewriting
# ─────────────────────────────────────────────────────────────────────────

def rewrite_config(city, property_type_key, bands):
    """Rewrite CITY / SEARCH_QUERIES / PRICE_FILTER_MIN/MAX / PRICE_BAND_EDGES
    in config.py to match what the user picked. main.py is run as a fresh
    subprocess afterward, so it always reads the updated file."""
    ptype = config.PROPERTY_TYPES[property_type_key]

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    text = re.sub(r'CITY = ".*?"', f'CITY = "{city}"', text, count=1)

    queries_block = "SEARCH_QUERIES = [\n" + "".join(
        f'    f"{term} in {{CITY}}",\n' for term in ptype["search_terms"]
    ) + "]"
    text = re.sub(r"SEARCH_QUERIES = \[.*?\]", queries_block, text, flags=re.DOTALL)

    price_min = min(lo for lo, _ in bands)
    price_max = max(hi for _, hi in bands)
    text = re.sub(r"PRICE_FILTER_MIN = \d[\d_]*", f"PRICE_FILTER_MIN = {price_min}", text)
    text = re.sub(r"PRICE_FILTER_MAX = \d[\d_]*", f"PRICE_FILTER_MAX = {price_max}", text)

    bands_repr = "[" + ", ".join(f"({lo}, {hi})" for lo, hi in bands) + "]"
    text = re.sub(r"PRICE_BAND_EDGES = \[.*?\]", f"PRICE_BAND_EDGES = {bands_repr}", text, flags=re.DOTALL)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def band_file_path(city, low, high):
    label = f"{low}-{high}"
    return os.path.join(SCRIPT_DIR, config.OUTPUT_DIR, f"{city.lower()}_hospitality_leads_{label}.csv")


def all_file_path(city):
    return os.path.join(SCRIPT_DIR, config.OUTPUT_DIR, f"{city.lower()}_hospitality_leads_all.csv")


# ─────────────────────────────────────────────────────────────────────────
# API: metadata
# ─────────────────────────────────────────────────────────────────────────

@app.route("/api/meta")
def api_meta():
    property_types = {
        key: {
            "label": p["label"],
            "default_bands": [list(b) for b in p["default_bands"]],
        }
        for key, p in config.PROPERTY_TYPES.items()
    }
    return jsonify({
        "default_city": config.CITY,
        "property_types": property_types,
        "known_cities": _known_cities(),
    })


def _known_cities():
    out_dir = os.path.join(SCRIPT_DIR, config.OUTPUT_DIR)
    if not os.path.isdir(out_dir):
        return []
    cities = set()
    for path in glob.glob(os.path.join(out_dir, "*_hospitality_leads_all.csv")):
        name = os.path.basename(path).replace("_hospitality_leads_all.csv", "")
        cities.add(name.replace("_", " ").title())
    return sorted(cities)


# ─────────────────────────────────────────────────────────────────────────
# API: run the pipeline
# ─────────────────────────────────────────────────────────────────────────

@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json(force=True) or {}
    city = (data.get("city") or "").strip()
    property_type_key = data.get("property_type")
    bands = data.get("bands") or []

    if not city:
        return jsonify({"error": "City is required."}), 400
    if property_type_key not in config.PROPERTY_TYPES:
        return jsonify({"error": "Unknown property type."}), 400
    if not bands:
        return jsonify({"error": "Select at least one price band."}), 400
    try:
        bands = [(int(b[0]), int(b[1])) for b in bands]
    except (ValueError, TypeError, IndexError):
        return jsonify({"error": "Invalid price band."}), 400
    for lo, hi in bands:
        if lo < 0 or hi <= lo:
            return jsonify({"error": f"Invalid price band {lo}-{hi}."}), 400

    rewrite_config(city, property_type_key, bands)

    run_id = uuid.uuid4().hex
    label = config.PROPERTY_TYPES[property_type_key]["label"]

    env = os.environ.copy()
    env["LEADGEN_CATEGORY_LABEL"] = f"{label} — {city}"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-u", MAIN_PATH],
        cwd=SCRIPT_DIR, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    run_state = {"proc": proc, "lines": [], "status": "running",
                 "returncode": None, "lock": threading.Lock(),
                 "city": city, "bands": bands}
    RUNS[run_id] = run_state

    def _pump():
        for line in proc.stdout:
            with run_state["lock"]:
                run_state["lines"].append(line.rstrip("\n"))
        proc.wait()
        with run_state["lock"]:
            run_state["status"] = "done" if proc.returncode == 0 else "error"
            run_state["returncode"] = proc.returncode

    threading.Thread(target=_pump, daemon=True).start()

    return jsonify({"run_id": run_id, "city": city, "bands": bands})


@app.route("/api/run/<run_id>/log")
def api_run_log(run_id):
    run_state = RUNS.get(run_id)
    if not run_state:
        return jsonify({"error": "Unknown run_id."}), 404
    since = int(request.args.get("since", 0))
    with run_state["lock"]:
        new_lines = run_state["lines"][since:]
        total = len(run_state["lines"])
        status = run_state["status"]
        returncode = run_state["returncode"]
    return jsonify({
        "lines": new_lines, "next": total,
        "status": status, "returncode": returncode,
        "city": run_state["city"], "bands": run_state["bands"],
    })


@app.route("/api/run/<run_id>/cancel", methods=["POST"])
def api_run_cancel(run_id):
    run_state = RUNS.get(run_id)
    if not run_state:
        return jsonify({"error": "Unknown run_id."}), 404
    proc = run_state["proc"]
    if proc.poll() is None:
        proc.terminate()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# API: leads
# ─────────────────────────────────────────────────────────────────────────

def _read_csv(path, search=""):
    if not os.path.exists(path):
        return {"columns": [], "rows": [], "exists": False}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return {"columns": [], "rows": [], "exists": True}
    header, data = rows[0], rows[1:]
    if search:
        q = search.strip().lower()
        if "NAME" in header:
            idx = header.index("NAME")
            data = [r for r in data if q in (r[idx].lower() if idx < len(r) else "")]
    return {"columns": header, "rows": data, "exists": True}


@app.route("/api/leads")
def api_leads():
    city = request.args.get("city", "")
    band = request.args.get("band", "all")
    search = request.args.get("q", "")
    if not city:
        return jsonify({"error": "city is required"}), 400

    if band == "all":
        path = all_file_path(city)
    else:
        try:
            lo, hi = (int(x) for x in band.split("-"))
        except ValueError:
            return jsonify({"error": "invalid band"}), 400
        path = band_file_path(city, lo, hi)

    result = _read_csv(path, search)
    result["file"] = os.path.basename(path)
    return jsonify(result)


@app.route("/api/leads/download")
def api_leads_download():
    city = request.args.get("city", "")
    band = request.args.get("band", "all")
    if not city:
        abort(400)
    if band == "all":
        path = all_file_path(city)
    else:
        try:
            lo, hi = (int(x) for x in band.split("-"))
        except ValueError:
            abort(400)
        path = band_file_path(city, lo, hi)
    if not os.path.exists(path):
        abort(404)
    directory, filename = os.path.split(path)
    return send_from_directory(directory, filename, as_attachment=True)


# ─────────────────────────────────────────────────────────────────────────
# Static frontend
# ─────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
(() => {
  "use strict";

  const el = (id) => document.getElementById(id);
  const fmtMoney = (n) => "₹" + Number(n).toLocaleString("en-IN");

  const state = {
    meta: null,
    selectedPropertyType: null,
    selectedBands: [],   // array of [lo, hi]
    customBands: [],     // user-added custom bands, same shape
    runId: null,
    pollTimer: null,
    logCursor: 0,
    lastCity: null,
    activeBand: "all",
  };

  el("todayDate").textContent = new Date().toLocaleDateString("en-IN", {
    year: "numeric", month: "long", day: "numeric",
  });

  // ── Load metadata (cities seen so far, property types) ───────────────
  fetch("/api/meta")
    .then((r) => r.json())
    .then((meta) => {
      state.meta = meta;
      el("cityInput").value = meta.default_city || "";
      renderCityList(meta.known_cities || []);
      renderPropertyTypes(meta.property_types || {});
    })
    .catch(() => {
      el("formError").textContent = "Could not reach the server. Is app.py running?";
    });

  function renderCityList(cities) {
    const list = el("cityList");
    list.innerHTML = "";
    cities.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      list.appendChild(opt);
    });
  }

  function renderPropertyTypes(types) {
    const row = el("propertyTypeRow");
    row.innerHTML = "";
    const keys = Object.keys(types);
    keys.forEach((key, i) => {
      const t = types[key];
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = t.label;
      chip.dataset.key = key;
      chip.addEventListener("click", () => selectPropertyType(key));
      row.appendChild(chip);
      if (i === 0) selectPropertyType(key); // default to first
    });
  }

  function selectPropertyType(key) {
    state.selectedPropertyType = key;
    state.customBands = [];
    [...el("propertyTypeRow").children].forEach((c) => {
      c.classList.toggle("is-selected", c.dataset.key === key);
    });
    const defaults = state.meta.property_types[key].default_bands || [];
    state.selectedBands = defaults.map((b) => [...b]);
    renderBands();
  }

  function renderBands() {
    const row = el("bandRow");
    row.innerHTML = "";
    const defaults = state.meta.property_types[state.selectedPropertyType].default_bands || [];
    const all = [...defaults, ...state.customBands];

    all.forEach(([lo, hi]) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      const isSelected = state.selectedBands.some(([l, h]) => l === lo && h === hi);
      chip.classList.toggle("is-selected", isSelected);
      chip.innerHTML = `${fmtMoney(lo)} – ${fmtMoney(hi)}<span class="chip-sub">per night</span>`;
      chip.addEventListener("click", () => toggleBand(lo, hi));
      row.appendChild(chip);
    });
  }

  function toggleBand(lo, hi) {
    const idx = state.selectedBands.findIndex(([l, h]) => l === lo && h === hi);
    if (idx >= 0) {
      state.selectedBands.splice(idx, 1);
    } else {
      state.selectedBands.push([lo, hi]);
    }
    renderBands();
  }

  el("customBandToggle").addEventListener("click", () => {
    el("customBandForm").hidden = !el("customBandForm").hidden;
  });

  el("customBandAdd").addEventListener("click", () => {
    const lo = parseInt(el("customLow").value, 10);
    const hi = parseInt(el("customHigh").value, 10);
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi <= lo || lo < 0) {
      el("formError").textContent = "Enter a valid custom range (max must be greater than min).";
      return;
    }
    el("formError").textContent = "";
    state.customBands.push([lo, hi]);
    state.selectedBands.push([lo, hi]);
    el("customLow").value = "";
    el("customHigh").value = "";
    el("customBandForm").hidden = true;
    renderBands();
  });

  // ── Start run ──────────────────────────────────────────────────────
  el("startBtn").addEventListener("click", startRun);

  function startRun() {
    const city = el("cityInput").value.trim();
    el("formError").textContent = "";

    if (!city) { el("formError").textContent = "Enter a city."; return; }
    if (!state.selectedPropertyType) { el("formError").textContent = "Pick a property type."; return; }
    if (!state.selectedBands.length) { el("formError").textContent = "Select at least one price band."; return; }

    el("startBtn").disabled = true;

    fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city,
        property_type: state.selectedPropertyType,
        bands: state.selectedBands,
      }),
    })
      .then((r) => r.json().then((body) => ({ ok: r.ok, body })))
      .then(({ ok, body }) => {
        el("startBtn").disabled = false;
        if (!ok) {
          el("formError").textContent = body.error || "Could not start the run.";
          return;
        }
        state.runId = body.run_id;
        state.lastCity = body.city;
        state.logCursor = 0;
        showRunScreen();
        pollLog();
      })
      .catch(() => {
        el("startBtn").disabled = false;
        el("formError").textContent = "Could not reach the server.";
      });
  }

  function showRunScreen() {
    el("entryCard").classList.add("hidden");
    el("runCard").classList.remove("hidden");
    el("resultsCard").classList.add("hidden");
    const label = state.meta.property_types[state.selectedPropertyType].label;
    el("runHeadline").textContent = `${label} — ${state.lastCity}`;
    el("runStatus").textContent = "Starting…";
    el("runLog").textContent = "";
    el("viewResultsBtn").classList.add("hidden");
    el("newSearchBtn").classList.add("hidden");
    el("cancelBtn").classList.remove("hidden");
    el("cancelBtn").disabled = false;
  }

  function pollLog() {
    clearTimeout(state.pollTimer);
    fetch(`/api/run/${state.runId}/log?since=${state.logCursor}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.lines && data.lines.length) {
          const log = el("runLog");
          log.textContent += data.lines.join("\n") + "\n";
          log.scrollTop = log.scrollHeight;
        }
        state.logCursor = data.next;

        if (data.status === "running") {
          el("runStatus").textContent = "Running…";
          state.pollTimer = setTimeout(pollLog, 1000);
        } else if (data.status === "done") {
          el("runStatus").textContent = "✅ Done";
          el("cancelBtn").classList.add("hidden");
          el("viewResultsBtn").classList.remove("hidden");
          el("newSearchBtn").classList.remove("hidden");
        } else {
          el("runStatus").textContent = `⚠ Stopped (exit code ${data.returncode})`;
          el("cancelBtn").classList.add("hidden");
          el("newSearchBtn").classList.remove("hidden");
        }
      })
      .catch(() => {
        state.pollTimer = setTimeout(pollLog, 1500);
      });
  }

  el("cancelBtn").addEventListener("click", () => {
    if (!state.runId) return;
    el("cancelBtn").disabled = true;
    fetch(`/api/run/${state.runId}/cancel`, { method: "POST" });
  });

  el("newSearchBtn").addEventListener("click", resetToForm);
  el("backToFormBtn").addEventListener("click", resetToForm);

  function resetToForm() {
    clearTimeout(state.pollTimer);
    el("resultsCard").classList.add("hidden");
    el("runCard").classList.add("hidden");
    el("entryCard").classList.remove("hidden");
  }

  // ── Results ────────────────────────────────────────────────────────
  el("viewResultsBtn").addEventListener("click", showResults);

  function showResults() {
    el("runCard").classList.add("hidden");
    el("resultsCard").classList.remove("hidden");

    const bands = state.selectedBands;
    const tabs = el("bandTabs");
    tabs.innerHTML = "";

    const allTab = makeTab("All", "all");
    tabs.appendChild(allTab);
    bands.forEach(([lo, hi]) => {
      tabs.appendChild(makeTab(`${fmtMoney(lo)}–${fmtMoney(hi)}`, `${lo}-${hi}`));
    });

    state.activeBand = bands.length ? `${bands[0][0]}-${bands[0][1]}` : "all";
    highlightActiveTab();
    loadLeads();
  }

  function makeTab(label, value) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab";
    btn.textContent = label;
    btn.dataset.value = value;
    btn.addEventListener("click", () => {
      state.activeBand = value;
      highlightActiveTab();
      loadLeads();
    });
    return btn;
  }

  function highlightActiveTab() {
    [...el("bandTabs").children].forEach((t) => {
      t.classList.toggle("is-active", t.dataset.value === state.activeBand);
    });
  }

  let searchDebounce = null;
  el("searchInput").addEventListener("input", () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(loadLeads, 250);
  });

  function loadLeads() {
    const q = el("searchInput").value.trim();
    const params = new URLSearchParams({
      city: state.lastCity, band: state.activeBand, q,
    });
    fetch(`/api/leads?${params.toString()}`)
      .then((r) => r.json())
      .then(renderTable)
      .catch(() => {
        el("resultsCount").textContent = "Could not load leads.";
      });
  }

  function renderTable(data) {
    const head = el("resultsHead");
    const body = el("resultsBody");
    head.innerHTML = "";
    body.innerHTML = "";

    if (!data.exists) {
      el("resultsCount").textContent = `No file yet for this band (it may still be empty).`;
      return;
    }

    data.columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      head.appendChild(th);
    });

    if (!data.rows.length) {
      const tr = document.createElement("tr");
      tr.className = "empty-row";
      const td = document.createElement("td");
      td.colSpan = Math.max(data.columns.length, 1);
      td.textContent = "No leads found.";
      tr.appendChild(td);
      body.appendChild(tr);
    } else {
      data.rows.forEach((row) => {
        const tr = document.createElement("tr");
        row.forEach((cell) => {
          const td = document.createElement("td");
          td.textContent = cell;
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }

    el("resultsCount").textContent = `${data.rows.length} lead${data.rows.length === 1 ? "" : "s"} — ${data.file}`;
  }

  el("downloadBtn").addEventListener("click", () => {
    const params = new URLSearchParams({ city: state.lastCity, band: state.activeBand });
    window.location.href = `/api/leads/download?${params.toString()}`;
  });
})();
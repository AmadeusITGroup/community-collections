/* Review-tab Expectations section.

   Renders one row per expectation with N variant evidence cells underneath
   (2 in baseline mode, 3 in regression). The expectation text itself is
   written once per row — no duplication across variant columns.

     ┌── ✓ EXPECTATIONS ──── [● BASELINE 33%] [● SKILL 83%] ─────────┐
     │ Flips: #2 ✗→✓  #3 ✗→✓  (2 gains · 0 regressions)              │
     │                                                               │
     │ #1  Response identifies record validation failure…            │
     │     ┌─ ● BASELINE ✓ ─────┐  ┌─ ● SKILL ✓ ────────────┐        │
     │     │ ┃ "The failure …"  │  │ ┃ "'Import fails …     │        │
     │     └────────────────────┘  └────────────────────────┘        │
     │ ───────────────────────────────────────────────────────────── │
     │ #2  Confidence is HIGH or >= 80                               │
     │     …                                                         │
     └───────────────────────────────────────────────────────────────┘

   Relies on: esc, getComparisonMode, normalizeExpectationTexts,
   variantLabelForSide, variantLabelFullForSide, plus EV.flipsBetween +
   EV.renderFlipsStrip on window.__EV. */



function buildExpectationCompare(wosRun, wsRun, baselineRun){
  var mode = getComparisonMode();
  var hasBaseline = mode === "regression" && baselineRun && baselineRun.grading;

  var wosExps = (wosRun && wosRun.grading && wosRun.grading.expectations) || [];
  var wsExps  = (wsRun  && wsRun.grading  && wsRun.grading.expectations)  || [];
  var blExps  = (hasBaseline && baselineRun.grading.expectations) || [];
  if(!wosExps.length && !wsExps.length && !blExps.length) return "";

  /* Canonical order comes from the eval definition on any available run;
     fall back to whichever grading list has entries if the definition
     wasn't embedded. */
  var canonical = normalizeExpectationTexts(
    (wsRun  && wsRun.expectations)  ||
    (wosRun && wosRun.expectations) ||
    (baselineRun && baselineRun.expectations) || []
  );

  /* Key expectations by a normalized match key (prefix-/whitespace-insensitive)
     rather than raw text, so the same expectation lines up across variants even
     when one grading.json kept the `[auto]` prefix and another stripped it.
     `displayByKey` remembers a human-readable label per key — canonical wins,
     otherwise the first text seen. `order` holds match keys. */
  var byText = {};
  var displayByKey = {};
  function add(exps, slot){
    exps.forEach(function(e){
      if(!(e && e.text)) return;
      var k = expectationMatchKey(e.text);
      if(!byText[k]) byText[k] = {};
      byText[k][slot] = e;
      if(!(k in displayByKey)) displayByKey[k] = e.text;
    });
  }
  add(blExps, "baseline");
  add(wosExps, "wos");
  add(wsExps, "ws");

  var order = [];
  var seen = {};
  canonical.forEach(function(t){
    var k = expectationMatchKey(t);
    if(!seen[k]){ order.push(k); seen[k] = true; displayByKey[k] = t; }
  });
  [wsExps, wosExps, blExps].forEach(function(list){
    list.forEach(function(e){
      if(!(e && e.text)) return;
      var k = expectationMatchKey(e.text);
      if(!seen[k]){ order.push(k); seen[k] = true; if(!(k in displayByKey)) displayByKey[k] = e.text; }
    });
  });
  if(!order.length) return "";

  /* Columns in left-to-right render order. In regression mode "wos" carries
     the previous_skill run (already aliased upstream in
     buildEvalGroupsForReview); the CSS class is "previous". */
  var cols = [];
  if(hasBaseline){
    cols.push({slot:"baseline", cls:"baseline", label:"Baseline", full:"Baseline (without skill)"});
  }
  cols.push({
    slot:"wos",
    cls: mode === "regression" ? "previous" : "baseline",
    label: variantLabelForSide("wos", mode),
    full:  variantLabelFullForSide("wos", mode)
  });
  cols.push({
    slot:"ws",
    cls:"current",
    label: variantLabelForSide("ws", mode),
    full:  variantLabelFullForSide("ws", mode)
  });

  var sums = {
    baseline: (baselineRun && baselineRun.grading && baselineRun.grading.summary) || null,
    wos: (wosRun && wosRun.grading && wosRun.grading.summary) || null,
    ws:  (wsRun  && wsRun.grading  && wsRun.grading.summary)  || null
  };

  function passRateFromSum(sum){
    if(!sum) return null;
    if(sum.pass_rate != null) return sum.pass_rate;
    if(sum.passed != null && sum.failed != null && (sum.passed + sum.failed) > 0){
      return sum.passed / (sum.passed + sum.failed);
    }
    return null;
  }

  /* Variant pills in the section-head carry the pass-rate percentage so the
     reader sees both the run label and the score in one glance. */
  function headPill(col){
    var rate = passRateFromSum(sums[col.slot]);
    var pct = rate == null ? "" : '<strong class="pct">' + (rate * 100).toFixed(0) + '%</strong>';
    return '<span class="variant-pill ' + col.cls + '" title="' + esc(col.full) + '">' +
      esc(col.label) + pct + '</span>';
  }

  /* Per-expectation, per-variant evidence cell. Evidence is an array of
     quoted passages — one block per element. Tolerates legacy single-string
     values written by older grader/comparator runs. */
  function evidenceItems(ev){
    if(ev == null) return [];
    if(Array.isArray(ev)){
      return ev.map(function(s){ return s == null ? "" : String(s); })
               .filter(function(s){ return s.length > 0; });
    }
    var s = String(ev);
    return s.length > 0 ? [s] : [];
  }
  function renderCell(col, e){
    var statusCls = !e ? "na" : (e.passed ? "pass" : "fail");
    var statusGlyph = !e ? "&mdash;" : (e.passed ? "&#10003;" : "&#10007;");
    var evidenceHtml;
    if(!e){
      evidenceHtml = '<div class="expect-evidence na">No data</div>';
    } else {
      var items = evidenceItems(e.evidence);
      evidenceHtml = items.map(function(s){
        return '<div class="expect-evidence">' + esc(s) + '</div>';
      }).join("");
    }
    var html = '<div class="expect-cell ' + col.cls + '">';
    html +=   '<div class="expect-cell-head">';
    html +=     '<span class="variant-pill ' + col.cls + '" title="' + esc(col.full) + '">' + esc(col.label) + '</span>';
    html +=     '<span class="expect-status ' + statusCls + '">' + statusGlyph + '</span>';
    html +=   '</div>';
    html +=   evidenceHtml;
    html += '</div>';
    return html;
  }

  /* Flips: gains/regressions between visible slot pairs. */
  var EV = window.__EV;
  var flipsStrip;
  if(mode === "regression" && hasBaseline){
    var fPrev = EV.flipsBetween(byText, order, "wos", "ws");
    var fBase = EV.flipsBetween(byText, order, "baseline", "ws");
    flipsStrip = EV.renderFlipsStrip([
      { label: "Current vs Previous", gains: fPrev.gains, regs: fPrev.regs },
      { label: "Current vs Baseline", gains: fBase.gains, regs: fBase.regs }
    ]);
  } else {
    var f = EV.flipsBetween(byText, order, "wos", "ws");
    flipsStrip = EV.renderFlipsStrip([ { label: "Flips", gains: f.gains, regs: f.regs } ]);
  }

  var rowsHtml = '';
  order.forEach(function(key, i){
    var row = byText[key] || {};
    var num = i + 1;
    var text = displayByKey[key] != null ? displayByKey[key] : key;
    rowsHtml += '<div class="expect-row">';
    rowsHtml +=   '<div class="expect-row-head">';
    rowsHtml +=     '<span class="expect-num">#' + num + '</span>';
    rowsHtml +=     '<span class="expect-text">' + esc(text) + '</span>';
    rowsHtml +=   '</div>';
    rowsHtml +=   '<div class="expect-row-variants" style="--er-cols:' + cols.length + '">';
    cols.forEach(function(c){
      rowsHtml += renderCell(c, row[c.slot]);
    });
    rowsHtml +=   '</div>';
    rowsHtml += '</div>';
  });

  var html = '';
  html += '<div class="sec-heading" id="sec-expectations">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.expectations + '</span>';
  html +=   '<h2>Expectations</h2>';
  html +=   '<div class="variant-pill-row">';
  cols.forEach(function(c){ html += headPill(c); });
  html +=   '</div>';
  html += '</div>';
  html += '<div class="card">';
  html += flipsStrip;
  html += '<div class="expect-rows">' + rowsHtml + '</div>';
  html += '</div>';
  return html;
}

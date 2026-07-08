/* Shared helpers exposed on `window.__EV` for cross-module reuse. Concatenated
   first so later src/ modules can depend on it. The format/render helpers
   used by the inline IIFE (esc, formatStatPct, renderMarkdown, …) are NOT
   here — they live alongside the boot code so the IIFE closure can call them
   directly without a trip through window.__EV. */

(function(){
  "use strict";

  var EV = window.__EV = window.__EV || {};
  EV.helpers = EV.helpers || {};

  /* flipsBetween(byText, order, refSlot, curSlot)
     -----------------------------------------------------------
     Computes the gain/regression delta between two expectation slots.

       byText:  { [text]: { baseline?, wos?, ws? } } from buildExpectationCompare
       order:   [text, text, …] canonical ordering
       refSlot: "baseline" | "wos" | "ws"
       curSlot: "baseline" | "wos" | "ws"

     Returns { gains:[#N, …], regs:[#N, …] } where N is the 1-based index of
     the expectation in `order`. Rows missing in either slot are skipped. */
  EV.flipsBetween = function flipsBetween(byText, order, refSlot, curSlot){
    var gains = [], regs = [];
    for(var i = 0; i < order.length; i++){
      var t = order[i];
      var row = byText[t] || {};
      var ref = row[refSlot], cur = row[curSlot];
      if(!ref || !cur) continue;
      var idx = i + 1;
      if(!ref.passed && cur.passed) gains.push(idx);
      else if(ref.passed && !cur.passed) regs.push(idx);
    }
    return { gains: gains, regs: regs };
  };

  /* renderFlipsStrip(flipsByLabel) → innerHTML for a .section-card-flips row.

       flipsByLabel: [ { label, gains, regs }, … ]

     Multi-comparison rows (e.g. "Current vs Previous", "Current vs Baseline"
     in regression mode) each render one line. Empty sets still render the
     "(0 gains · 0 regressions)" tail so reviewers know the comparison ran. */
  /* Pull the average for `key` from a run_summary bucket
     ({ pass_rate: { mean, … }, time_seconds: { mean, … }, … }). Returns null
     when the bucket or the keyed entry is missing or non-numeric. */
  EV.metricMean = function metricMean(bucket, key){
    if(!bucket) return null;
    var entry = bucket[key];
    if(entry && typeof entry === "object" && "mean" in entry){
      var n = Number(entry.mean);
      return Number.isNaN(n) ? null : n;
    }
    return null;
  };

  /* Strip provider prefixes (e.g. "claude-sonnet-4.5" → "sonnet-4.5") so a
     model badge can fit in tight UI without losing meaning. Idempotent for
     names already short. */
  EV.shortModel = function shortModel(name){
    if(!name) return "";
    return String(name).replace(/^claude-/i, "");
  };

  /* Derive the model used for `variant` (default "current_skill") in the
     given iteration's benchmark.json (D.iteration_benchmarks[iter]). Returns:
       • { label: "sonnet-4.5", mixed: false, models: ["sonnet-4.5"] } when one
       • { label: "Mixed", mixed: true,  models: [...] } when multiple
       • null when no models can be resolved. */
  EV.iterationModel = function iterationModel(iterNum, variant){
    variant = variant || "current_skill";
    var bm = (typeof D !== "undefined" && D.iteration_benchmarks) ? D.iteration_benchmarks[String(iterNum)] : null;
    if(!bm || !bm.runs) return null;
    var seen = {};
    var models = [];
    bm.runs.forEach(function(r){
      if(r.configuration !== variant) return;
      var m = r.result && r.result.model;
      if(!m) return;
      var s = EV.shortModel(m);
      if(!seen[s]){ seen[s] = true; models.push(s); }
    });
    if(!models.length) return null;
    return {
      label: models.length === 1 ? models[0] : "Mixed",
      mixed: models.length > 1,
      models: models
    };
  };

  EV.renderFlipsStrip = function renderFlipsStrip(flipsByLabel){
    if(!flipsByLabel || !flipsByLabel.length) return "";
    var lines = flipsByLabel.map(function(row){
      var chips = "";
      row.gains.forEach(function(n){ chips += '<span class="flip-chip gain">#' + n + ' &#10007;&rarr;&#10003;</span> '; });
      row.regs .forEach(function(n){ chips += '<span class="flip-chip reg">#'  + n + ' &#10003;&rarr;&#10007;</span> '; });
      var tail = '<span class="sc-flips-tail">(' +
        row.gains.length + ' gain' + (row.gains.length === 1 ? '' : 's') +
        ' · ' +
        row.regs.length + ' regression' + (row.regs.length === 1 ? '' : 's') +
        ')</span>';
      var prefix = '<span class="sc-flips-prefix">' + row.label + ':</span>';
      return prefix + ' ' + chips + tail;
    });
    return '<div class="section-card-flips">' + lines.join('<br>') + '</div>';
  };

})();

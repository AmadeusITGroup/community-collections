/* Benchmark Per-Eval Scorecard — compact sortable table, one row per eval.
   Default sort: Δ ascending (worst-first). Filter chips:
     [All] [Regressions] [Neutral (<±5%)] [Wins].

   Data source:
     1. src.per_eval — iteration-level aggregated payload, when available.
     2. Otherwise derive from src.runs by grouping on eval_id. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  function pct(v){
    if(v == null) return "N/A";
    return (v * 100).toFixed(0) + "%";
  }

  function bucketizeFromRuns(runs){
    var m = {};
    var order = [];
    (runs || []).forEach(function(r){
      if(!r) return;
      var key = r.eval_id != null ? r.eval_id : r.eval_name;
      if(!m[key]){
        m[key] = { eval_id: r.eval_id, eval_name: r.eval_name };
        order.push(key);
      }
      var cfg = r.configuration || r.variant;
      var rate = r.result ? r.result.pass_rate : null;
      if(cfg === "current_skill") m[key].current_skill_pass_rate = rate;
      else if(cfg === "without_skill") m[key].without_skill_pass_rate = rate;
      else if(cfg === "previous_skill") m[key].previous_skill_pass_rate = rate;
    });
    return order.map(function(k){ return m[k]; });
  }

  function rowsFromSrc(src){
    var pe = src.per_eval;
    if(pe && pe.length && pe[0].current_skill_pass_rate !== undefined){
      return pe.slice();
    }
    if(src.runs && src.runs.length){
      return bucketizeFromRuns(src.runs);
    }
    return [];
  }

  /* Classify row for filter chips. */
  function classify(row, mode){
    var cur = row.current_skill_pass_rate;
    var base = mode === "regression" ? row.previous_skill_pass_rate : row.without_skill_pass_rate;
    if(cur == null || base == null) return "neutral";
    var d = cur - base;
    if(d >= 0.05) return "win";
    if(d <= -0.05) return "regression";
    return "neutral";
  }

  function deltaChip(row, mode){
    var cur = row.current_skill_pass_rate;
    var base = mode === "regression" ? row.previous_skill_pass_rate : row.without_skill_pass_rate;
    if(cur == null || base == null) return '<span class="delta-chip flat">\u2014</span>';
    var d = cur - base;
    if(Math.abs(d) < 0.001) return '<span class="delta-chip flat">=</span>';
    var cls = d > 0 ? "pos" : "neg";
    var sign = d > 0 ? "+" : "";
    return '<span class="delta-chip ' + cls + '">' + sign + (d * 100).toFixed(0) + '%</span>';
  }

  EV.buildBenchmarkScorecard = function buildBenchmarkScorecard(src){
    if(!src) return "";
    var mode = getComparisonMode();
    var rows = rowsFromSrc(src);
    if(!rows.length) return "";

    /* Annotate rows with delta + bucket + sort keys. */
    rows = rows.map(function(r){
      var cur = r.current_skill_pass_rate;
      var base = mode === "regression" ? r.previous_skill_pass_rate : r.without_skill_pass_rate;
      var d = (cur != null && base != null) ? cur - base : null;
      return {
        id: r.eval_id,
        name: r.eval_name,
        baseline: r.without_skill_pass_rate,
        previous: r.previous_skill_pass_rate,
        skill: cur,
        delta: d,
        bucket: classify(r, mode)
      };
    });

    var counts = {
      all: rows.length,
      regression: rows.filter(function(r){ return r.bucket === "regression"; }).length,
      neutral: rows.filter(function(r){ return r.bucket === "neutral"; }).length,
      win: rows.filter(function(r){ return r.bucket === "win"; }).length
    };

    var html = '';
    html += '<div class="sec-heading" id="sec-per-eval" data-section="per-eval">';
    html += '<span class="sec-icon">' + NAV_ICONS["per-eval"] + '</span>';
    html += '<h2>Per-Eval Scorecard</h2></div>';
    html += '<div class="card">';
    html += '<div class="scorecard-controls">';
    html += '<span class="sort-label">Sort</span>';
    html += '<select class="sort-select" data-scorecard-sort>' +
      '<option value="delta-asc">\u0394 ascending</option>' +
      '<option value="delta-desc">\u0394 descending</option>' +
      '<option value="id">Eval #</option>' +
      '<option value="baseline-desc">Baseline %</option>' +
      '<option value="skill-desc">Skill %</option>' +
      '</select>';
    html += '<div class="filter-chip-row" data-scorecard-filters>';
    html += '<button class="filter-chip active" data-filter="all">All <span class="count">' + counts.all + '</span></button>';
    html += '<button class="filter-chip impact-blocking" data-filter="regression">Regressions <span class="count">' + counts.regression + '</span></button>';
    html += '<button class="filter-chip impact-minor" data-filter="neutral">Neutral <span class="count">' + counts.neutral + '</span></button>';
    html += '<button class="filter-chip" data-filter="win">Wins <span class="count">' + counts.win + '</span></button>';
    html += '</div></div>';

    /* Sort rows by default (delta asc — regressions first, then smallest wins). */
    rows.sort(function(a, b){
      var da = a.delta == null ? Infinity : a.delta;
      var db = b.delta == null ? Infinity : b.delta;
      if(da !== db) return da - db;
      return (a.id || 0) - (b.id || 0);
    });

    html += '<div class="scorecard-wrap"><table class="scorecard-table">';
    html += '<thead><tr><th>#</th><th>Eval</th><th>Baseline</th>';
    if(mode === "regression") html += '<th>Previous</th>';
    html += '<th>Skill</th><th>\u0394</th><th>\u2197</th></tr></thead>';
    html += '<tbody data-scorecard-body>';
    rows.forEach(function(r){
      html += '<tr class="scorecard-row" data-bucket="' + r.bucket + '" data-delta="' + (r.delta == null ? "" : r.delta) + '" data-id="' + (r.id == null ? "" : r.id) +
        '" data-baseline="' + (r.baseline == null ? "" : r.baseline) +
        '" data-skill="' + (r.skill == null ? "" : r.skill) +
        '" data-eval-id="' + (r.id == null ? "" : r.id) + '">';
      html += '<td>' + (r.id != null ? "#" + r.id : "\u2014") + '</td>';
      html += '<td title="' + esc(r.name || "") + '">' + esc(r.name || "\u2014") + '</td>';
      html += '<td>' + pct(r.baseline) + '</td>';
      if(mode === "regression") html += '<td>' + pct(r.previous) + '</td>';
      html += '<td>' + pct(r.skill) + '</td>';
      html += '<td>' + deltaChip({current_skill_pass_rate:r.skill, without_skill_pass_rate:r.baseline, previous_skill_pass_rate:r.previous}, mode) + '</td>';
      html += '<td class="jump-cell">\u2197</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    html += '</div>'; /* card */
    return html;
  };

  function sortRows(tbody, key){
    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr.scorecard-row"));
    function num(v){ return v === "" || v == null ? NaN : parseFloat(v); }
    rows.sort(function(a, b){
      var da, db;
      if(key === "delta-asc" || key === "delta-desc"){
        da = num(a.getAttribute("data-delta"));
        db = num(b.getAttribute("data-delta"));
        if(isNaN(da) && isNaN(db)) return 0;
        if(isNaN(da)) return 1;
        if(isNaN(db)) return -1;
        return key === "delta-asc" ? da - db : db - da;
      }
      if(key === "id"){
        da = num(a.getAttribute("data-id"));
        db = num(b.getAttribute("data-id"));
        return (isNaN(da) ? 0 : da) - (isNaN(db) ? 0 : db);
      }
      if(key === "baseline-desc"){
        da = num(a.getAttribute("data-baseline"));
        db = num(b.getAttribute("data-baseline"));
        return (isNaN(db) ? 0 : db) - (isNaN(da) ? 0 : da);
      }
      if(key === "skill-desc"){
        da = num(a.getAttribute("data-skill"));
        db = num(b.getAttribute("data-skill"));
        return (isNaN(db) ? 0 : db) - (isNaN(da) ? 0 : da);
      }
      return 0;
    });
    rows.forEach(function(r){ tbody.appendChild(r); });
  }

  EV.bindBenchmarkScorecard = function bindBenchmarkScorecard(root){
    if(!root) return;
    var tbody = root.querySelector("[data-scorecard-body]");
    if(!tbody) return;
    var filterWrap = root.querySelector("[data-scorecard-filters]");
    var sortEl = root.querySelector("[data-scorecard-sort]");
    var activeFilter = "all";

    function applyFilter(){
      tbody.querySelectorAll("tr.scorecard-row").forEach(function(tr){
        var b = tr.getAttribute("data-bucket");
        var show = (activeFilter === "all") || (activeFilter === b);
        tr.classList.toggle("hidden", !show);
      });
    }

    if(filterWrap){
      filterWrap.querySelectorAll(".filter-chip").forEach(function(chip){
        chip.addEventListener("click", function(){
          filterWrap.querySelectorAll(".filter-chip").forEach(function(c){ c.classList.remove("active"); });
          this.classList.add("active");
          activeFilter = this.getAttribute("data-filter");
          applyFilter();
        });
      });
    }

    if(sortEl){
      sortEl.addEventListener("change", function(){ sortRows(tbody, this.value); });
    }

    tbody.querySelectorAll("tr.scorecard-row").forEach(function(tr){
      tr.addEventListener("click", function(){
        var id = this.getAttribute("data-eval-id");
        if(id) _navToReviewEval(parseInt(id, 10));
      });
    });
  };
})();

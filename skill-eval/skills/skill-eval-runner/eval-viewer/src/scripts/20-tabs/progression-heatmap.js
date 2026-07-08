/* Progression Heatmap — Δ column, sort dropdown, sticky header,
   cell-click jumps to the matching eval in the Review tab. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  function heatClass(v){
    if(v == null) return "hm-gray";
    return v >= 0.8 ? "hm-green" : v >= 0.5 ? "hm-yellow" : "hm-red";
  }
  function heatText(v){ return v == null ? "\u2014" : (v * 100).toFixed(0) + "%"; }

  function findForEval(iter, ev){
    return (iter.per_eval || []).find(function(p){
      return ev.id != null ? p.eval_id === ev.id : p.eval_name === ev.name;
    }) || null;
  }

  EV.buildProgressionHeatmap = function buildProgressionHeatmap(iters){
    if(!iters || !iters.length){
      return '<p style="color:var(--text-muted);text-align:center">No per-eval data</p>';
    }

    /* Gather unique evals. */
    var evalList = [];
    var seen = {};
    iters.forEach(function(it){
      (it.per_eval || []).forEach(function(pe){
        var key = pe.eval_id != null ? "id:" + pe.eval_id : "name:" + pe.eval_name;
        if(!seen[key]){ seen[key] = true; evalList.push({id: pe.eval_id, name: pe.eval_name}); }
      });
    });
    if(!evalList.length) return '<p style="color:var(--text-muted);text-align:center">No per-eval data</p>';

    /* Resolve baseline (latest iter's without_skill). */
    function baselineFor(ev){
      for(var i = iters.length - 1; i >= 0; i--){
        var p = findForEval(iters[i], ev);
        if(p && p.without_skill_pass_rate != null) return p.without_skill_pass_rate;
      }
      return null;
    }

    /* Build rows with iteration-by-iteration values + Δ. */
    var rows = evalList.map(function(ev){
      var base = baselineFor(ev);
      var vals = iters.map(function(it){
        var p = findForEval(it, ev);
        return p ? p.current_skill_pass_rate : null;
      });
      var first = null, last = null;
      for(var i = 0; i < vals.length; i++){ if(vals[i] != null){ first = vals[i]; break; } }
      for(var j = vals.length - 1; j >= 0; j--){ if(vals[j] != null){ last = vals[j]; break; } }
      var delta = (first != null && last != null) ? last - first : null;
      var latest = last;
      return { ev: ev, base: base, vals: vals, delta: delta, latest: latest };
    });

    /* Controls + legend. */
    var html = '<div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:10px">';
    html += '<span class="sort-label">Sort</span>';
    html += '<select class="sort-select" data-hm-sort>' +
      '<option value="id">By eval #</option>' +
      '<option value="delta-worst">By \u0394 (biggest regression first)</option>' +
      '<option value="latest-desc">By latest pass rate</option>' +
      '</select>';
    html += '<div class="heatmap-legend" style="margin-left:auto">' +
      '<span><span class="swatch red"></span>&lt;50%</span>' +
      '<span><span class="swatch yellow"></span>50\u201379%</span>' +
      '<span><span class="swatch green"></span>\u226580%</span>' +
      '<span><span class="swatch gray"></span>no data</span>' +
      '</div>';
    html += '</div>';

    html += '<div class="heatmap-wrap"><table class="heatmap-table">';
    html += '<thead><tr><th style="text-align:center">ID</th><th>Eval</th><th title="Baseline without skill">Baseline</th>';
    iters.forEach(function(it){ html += '<th>Iter ' + it.iteration + '</th>'; });
    html += '<th>\u0394</th></tr></thead><tbody data-hm-body>';

    rows.forEach(function(r){
      var rowId = r.ev.id == null ? "" : r.ev.id;
      var tr = '<tr data-eval-id="' + rowId + '" data-delta="' + (r.delta == null ? "" : r.delta) + '" data-latest="' + (r.latest == null ? "" : r.latest) + '" data-id="' + rowId + '">';
      tr += '<td class="hm-eval-id">' + (r.ev.id != null ? "#" + r.ev.id : "-") + '</td>';
      tr += '<td class="hm-eval-name" title="' + esc(r.ev.name || "") + '">' + esc(r.ev.name || "") + '</td>';
      tr += '<td class="' + heatClass(r.base) + '">' + heatText(r.base) + '</td>';
      iters.forEach(function(it, i){
        var v = r.vals[i];
        var cls = heatClass(v) + (v != null && r.ev.id != null ? ' hm-clickable' : '');
        tr += '<td class="' + cls + '" data-iter="' + it.iteration + '">' + heatText(v) + '</td>';
      });
      /* Δ arrow column. */
      var deltaCls = "flat", deltaArrow = "\u2192";
      if(r.delta != null){
        if(Math.abs(r.delta) < 0.02){ deltaCls = "flat"; deltaArrow = "\u2192"; }
        else if(r.delta > 0){ deltaCls = "up"; deltaArrow = "\u2197"; }
        else { deltaCls = "down"; deltaArrow = "\u2198"; }
      }
      tr += '<td class="hm-delta-cell ' + deltaCls + '">' + deltaArrow + '</td>';
      tr += '</tr>';
      html += tr;
    });
    html += '</tbody></table></div>';
    return html;
  };

  EV.bindProgressionHeatmap = function bindProgressionHeatmap(root){
    if(!root) return;
    var card = root.querySelector("[data-hm-body]");
    if(!card) return;
    var sortEl = root.querySelector("[data-hm-sort]");

    function num(v){ return v === "" || v == null ? NaN : parseFloat(v); }

    function sortBy(key){
      var rows = Array.prototype.slice.call(card.querySelectorAll("tr"));
      rows.sort(function(a, b){
        if(key === "id"){
          return (num(a.getAttribute("data-id")) || 0) - (num(b.getAttribute("data-id")) || 0);
        }
        if(key === "delta-worst"){
          var da = num(a.getAttribute("data-delta"));
          var db = num(b.getAttribute("data-delta"));
          if(isNaN(da) && isNaN(db)) return 0;
          if(isNaN(da)) return 1;
          if(isNaN(db)) return -1;
          return da - db;
        }
        if(key === "latest-desc"){
          var la = num(a.getAttribute("data-latest"));
          var lb = num(b.getAttribute("data-latest"));
          return (isNaN(lb) ? 0 : lb) - (isNaN(la) ? 0 : la);
        }
        return 0;
      });
      rows.forEach(function(r){ card.appendChild(r); });
    }

    if(sortEl){
      sortEl.addEventListener("change", function(){ sortBy(this.value); });
    }

    card.querySelectorAll("td.hm-clickable").forEach(function(td){
      td.addEventListener("click", function(){
        var tr = td.parentElement;
        var id = tr && tr.getAttribute("data-eval-id");
        if(id) _navToReviewEval(parseInt(id, 10));
      });
    });
  };
})();

/* Benchmark Insights — grouped callouts (Action Needed / Pattern /
   Positive Signal) backed by the `intent` / `headline` / `suggestion`
   fields the analyzer agent emits. When a note lacks those fields, the
   frontend derives them heuristically from category + text. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var GROUPS = [
    { key: "action_needed",  label: "Action Needed",   cls: "action"   },
    { key: "pattern",        label: "Pattern",         cls: "pattern"  },
    { key: "positive_signal",label: "Positive Signal", cls: "positive" }
  ];

  var POSITIVE_CUES = /(preferred|no contradictions|all \d+ evals|strongly positive|agrees with grader|wins?|improvement|improved|\+\d)/i;

  function deriveIntent(note){
    if(note.intent) return note.intent;
    var cat = note.category || "observation";
    var text = String(note.text || "");
    var impact = (note.metrics && (note.metrics.impact || note.metrics.severity)) || "";
    if(cat === "non_discriminating" || cat === "skill_hurts" || cat === "regression" || cat === "contradiction" || cat === "broken") {
      return "action_needed";
    }
    if(cat === "skill_feedback"){
      return (impact === "blocking" || impact === "major") ? "action_needed" : "pattern";
    }
    if(cat === "skill_value" || cat === "improvement" || cat === "cost_saving") return "positive_signal";
    if(cat === "new_eval") return "pattern";
    if(cat === "observation"){
      return POSITIVE_CUES.test(text) ? "positive_signal" : "pattern";
    }
    return "pattern";
  }

  function deriveHeadline(note){
    if(note.headline) return note.headline;
    var t = String(note.text || "").trim();
    if(!t) return note.category || "Observation";
    /* First sentence up to period or 90 chars. */
    var dot = t.indexOf(". ");
    if(dot > 8 && dot < 90) return t.slice(0, dot);
    return t.length > 90 ? t.slice(0, 87) + "\u2026" : t;
  }

  function resolveEvalChip(id, src){
    /* Try to find the eval_name from the benchmark payload so the chip
       reads "#N truncated-name" instead of bare "#N". */
    var name = "";
    if(src && src.per_eval){
      for(var i = 0; i < src.per_eval.length; i++){
        if(src.per_eval[i].eval_id === id){ name = src.per_eval[i].eval_name || ""; break; }
      }
    }
    if(!name && src && src.runs){
      for(var j = 0; j < src.runs.length; j++){
        if(src.runs[j].eval_id === id){ name = src.runs[j].eval_name || ""; break; }
      }
    }
    if(name && name.length > 26) name = name.slice(0, 24) + "\u2026";
    var safe = esc(name);
    return '<button type="button" class="eval-chip" data-nav-eval="' + id + '">' +
      '<span class="eval-chip-id">#' + id + '</span>' +
      (safe ? ' <span class="eval-chip-name">' + safe + '</span>' : '') +
      '</button>';
  }

  function metricPills(note){
    var m = note.metrics;
    if(!m || typeof m !== "object") return "";
    var pills = [];
    Object.keys(m).forEach(function(k){
      if(pills.length >= 3) return;
      var v = m[k];
      if(v == null || typeof v === "object") return;
      if(typeof v === "string" && v.length > 26) return;
      pills.push({ key: k, value: v });
    });
    if(!pills.length) return "";
    return '<div class="insight-metric-pills">' + pills.map(function(p){
      var label = p.key.replace(/_/g, " ");
      var value = typeof p.value === "number" ? (Number.isInteger(p.value) ? p.value : p.value.toFixed(2)) : p.value;
      return '<span class="pill"><strong>' + value + '</strong>&nbsp;' + esc(label) + '</span>';
    }).join("") + '</div>';
  }

  function insightBody(note, src){
    /* highlightNote also handles esc() + #N / number / 'quoted' highlighting. */
    var text = highlightNote(note.text || "");
    var html = '';
    html += metricPills(note);
    html += '<div class="insight-prose">' + text + '</div>';
    var refs = note.eval_refs || [];
    if(refs.length){
      html += '<div class="insight-refs"><span class="refs-label">Evals</span>';
      refs.forEach(function(id){ html += resolveEvalChip(id, src); });
      html += '</div>';
    }
    if(note.suggestion){
      html += '<div class="insight-suggestion">' + esc(note.suggestion) + '</div>';
    }
    return html;
  }

  /* Dedupe consecutive skill_feedback notes into one grouped note with
     combined eval_refs. */
  function dedupeSkillFeedback(notes){
    var out = [];
    var pending = null;
    notes.forEach(function(note){
      if(note.category === "skill_feedback"){
        if(!pending){
          pending = Object.assign({}, note);
          pending.eval_refs = (note.eval_refs || []).slice();
          pending._merged = 1;
          out.push(pending);
        } else {
          (note.eval_refs || []).forEach(function(id){
            if(pending.eval_refs.indexOf(id) === -1) pending.eval_refs.push(id);
          });
          pending._merged += 1;
          /* Concatenate text body so individual entries are not lost. */
          if(note.text && pending.text && pending.text.indexOf(note.text) === -1){
            pending.text = pending.text + " \u2014 " + note.text;
          }
        }
      } else {
        pending = null;
        out.push(note);
      }
    });
    return out;
  }

  EV.buildBenchmarkInsightsCard = function buildBenchmarkInsightsCard(src){
    var notes = (src && src.notes) || [];
    if(!notes.length){
      return '<div class="sec-heading" id="sec-insights" data-section="insights">' +
        '<span class="sec-icon">' + NAV_ICONS.insights + '</span>' +
        '<h2>Insights</h2></div>' +
        '<div class="card"><div class="insights-empty">No insights available for this iteration.</div></div>';
    }

    notes = dedupeSkillFeedback(notes.slice());

    /* Enrich + bucket. */
    var buckets = { action_needed: [], pattern: [], positive_signal: [] };
    notes.forEach(function(note){
      var intent = deriveIntent(note);
      var headline = deriveHeadline(note);
      note = Object.assign({}, note, { intent: intent, headline: headline });
      if(!buckets[intent]) intent = "pattern";
      buckets[intent].push(note);
    });

    var html = '';
    html += '<div class="sec-heading" id="sec-insights" data-section="insights">';
    html += '<span class="sec-icon">' + NAV_ICONS.insights + '</span>';
    html += '<h2>Insights</h2></div>';
    html += '<div class="card">';

    var visibleGroups = 0;
    GROUPS.forEach(function(g){
      var items = buckets[g.key];
      if(!items || !items.length) return;
      visibleGroups++;
      /* Order: action_needed by severity, positive by magnitude of metric delta. */
      if(g.key === "action_needed"){
        items.sort(function(a, b){
          var order = { blocking: 0, major: 1, minor: 2 };
          var ai = (a.metrics && a.metrics.impact) || "";
          var bi = (b.metrics && b.metrics.impact) || "";
          return (order[ai] || 99) - (order[bi] || 99);
        });
      }

      var glyph = g.key === "action_needed" ? "\u26A0" : (g.key === "pattern" ? "\u25C7" : "\u2713");
      html += '<div class="insight-group ' + g.cls + '">';
      html += '<div class="insight-group-head"><span>' + glyph + ' ' + g.label + '</span><span class="group-count">\u00b7 ' + items.length + ' item' + (items.length === 1 ? '' : 's') + '</span></div>';
      items.forEach(function(note){
        html += '<div class="insight-item ' + g.cls + '">';
        html += '<div class="insight-headline">' + glyph + ' ' + esc(note.headline) + '</div>';
        html += insightBody(note, src);
        html += '</div>';
      });
      html += '</div>';
    });

    if(visibleGroups === 0){
      html += '<div class="insights-empty">No insights available for this iteration.</div>';
    }
    html += '</div>'; /* card */
    return html;
  };

  EV.bindBenchmarkInsightsNav = function bindBenchmarkInsightsNav(root){
    if(!root) return;
    root.querySelectorAll(".eval-chip[data-nav-eval]").forEach(function(chip){
      chip.addEventListener("click", function(e){
        e.stopPropagation();
        var id = this.getAttribute("data-nav-eval");
        if(id) _navToReviewEval(parseInt(id, 10));
      });
    });
  };
})();

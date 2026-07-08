/* Benchmark Cost Overhead card — separate panel for "cost, not benefit"
   metrics so a regression on tokens/time isn't conflated with a pass-rate
   regression.
     Metric | Baseline | (Previous) | Skill | Δ | Ratio
   Δ uses amber (cost overhead is an expected tradeoff, not failure);
   Ratio ≥ 2× gets a ⚠ suffix. Tool Calls / Steps rows render only when
   rs.current_skill exposes them. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var metricMean = EV.metricMean;

  function fmtDecimal(v, digits){
    if(v == null) return "N/A";
    return Number(v).toFixed(digits == null ? 1 : digits);
  }
  function fmtNullableDecimal(v){
    return v == null ? null : fmtDecimal(v, 1);
  }

  EV.buildBenchmarkCostCard = function buildBenchmarkCostCard(src){
    if(!src) return "";
    var rs = src.run_summary || {};
    var mode = getComparisonMode();

    var ws = rs.current_skill || {};
    var wos = rs.without_skill || {};
    var prev = rs.previous_skill || null;

    /* Column setup.
       Skill column = current_skill (always).
       Baseline column = without_skill (always, for cost reference).
       Previous column = previous_skill in regression mode only. */
    var cols = [];
    cols.push({key:"wos",  label:"Baseline", bucket:wos});
    if(mode === "regression" && prev){
      cols.push({key:"prev", label:"Previous", bucket:prev});
    }
    cols.push({key:"ws",   label: mode === "regression" ? "Current" : "Skill", bucket:ws});

    var rows = [
      {label:"Avg Time",       key:"time_seconds", fmt:formatTime, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1) + "s"; }},
      {label:"Avg Tokens",     key:"tokens",       fmt:formatNum,  deltaFmt: function(d){ return (d >= 0 ? "+" : "") + Math.round(d).toLocaleString(); }},
      {label:"Avg Tool Calls", key:"tool_calls",   fmt:fmtNullableDecimal, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1); }},
      {label:"Avg Agent Turns", key:"steps",       fmt:fmtNullableDecimal, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1); }}
    ];

    /* Table — ditch rows where every value is null (tool_calls / steps often
       aren't exposed by older aggregator versions). Keep rows where at least
       one variant has a value. */
    var visibleRows = rows.filter(function(row){
      return cols.some(function(c){ return metricMean(c.bucket, row.key) != null; });
    });

    if(!visibleRows.length) return "";

    var deltaRefBucket = (mode === "regression" && prev) ? prev : wos;
    var deltaRefLabel  = (mode === "regression" && prev) ? "Previous" : "Baseline";

    var html = '';
    html += '<div class="sec-heading" id="sec-cost" data-section="cost">';
    html += '<span class="sec-icon">' + NAV_ICONS.cost + '</span>';
    html += '<h2>Cost Overhead</h2></div>';
    html += '<div class="card">';
    html += '<div style="overflow-x:auto"><table class="bench-cost-table"><thead><tr>';
    html += '<th>Metric</th>';
    cols.forEach(function(c){ html += '<th>' + c.label + '</th>'; });
    html += '<th title="Current vs ' + deltaRefLabel + '">\u0394 <span class="bench-cost-ref">vs ' + deltaRefLabel + '</span></th>';
    html += '<th title="Current / Baseline">Ratio <span class="bench-cost-ref">vs Baseline</span></th>';
    html += '</tr></thead><tbody>';

    /* Δ and Ratio answer different questions:
         Δ     = vs Previous in regression mode (was the last iteration cheaper?),
                 vs Baseline in baseline mode.
         Ratio = always vs Baseline (how expensive is the skill overall?).
       Splitting references means a stable Ratio doesn't decay to ~1× as
       iterations converge, while Δ stays actionable per iteration. */
    visibleRows.forEach(function(row){
      var wsVal = metricMean(ws, row.key);
      var deltaRefVal = metricMean(deltaRefBucket, row.key);
      var ratioBaseVal = metricMean(wos, row.key);
      var delta = (wsVal != null && deltaRefVal != null) ? wsVal - deltaRefVal : null;
      var ratio = (wsVal != null && ratioBaseVal != null && ratioBaseVal !== 0) ? wsVal / ratioBaseVal : null;
      var ratioFlag = ratio != null && ratio >= 2;

      html += '<tr>';
      html += '<td>' + row.label + '</td>';
      cols.forEach(function(c){
        var v = metricMean(c.bucket, row.key);
        html += '<td>' + (v == null ? "\u2014" : row.fmt(v)) + '</td>';
      });
      html += '<td class="cell-delta">';
      if(delta != null){
        var chipCls = delta === 0 ? "flat" : (delta < 0 ? "pos" : "cost");
        html += '<span class="delta-chip ' + chipCls + '">' + row.deltaFmt(delta) + '</span>';
      } else {
        html += '\u2014';
      }
      html += '</td>';
      html += '<td' + (ratioFlag ? ' class="bench-cost-ratio-warn"' : '') + '>';
      html += ratio == null ? "\u2014" : (fmtDecimal(ratio, 2) + "\u00d7");
      html += '</td>';
      html += '</tr>';
    });

    html += '</tbody></table></div>';

    /* Narrative footer — prefer analyzer_notes synth, else client-side. */
    var notes = src.notes || [];
    var overheadNote = null;
    for(var i = 0; i < notes.length; i++){
      var n = notes[i];
      var txt = (n && n.text) || "";
      if(/skill overhead|token overhead|cost|tokens? higher|token spend|trade/i.test(txt)){
        overheadNote = txt;
        break;
      }
    }
    var narrative = overheadNote;
    if(!narrative){
      var wsPR = ws.pass_rate ? ws.pass_rate.mean : null;
      var wosPR = wos.pass_rate ? wos.pass_rate.mean : null;
      var ppDelta = (wsPR != null && wosPR != null) ? (wsPR - wosPR) * 100 : null;
      var wsTok = metricMean(ws, "tokens"), baseTok = metricMean(wos, "tokens");
      var tokRatio = (wsTok != null && baseTok != null && baseTok !== 0) ? wsTok / baseTok : null;
      if(ppDelta != null && tokRatio != null){
        var sign = ppDelta >= 0 ? "+" : "";
        narrative = "Skill trades " + sign + ppDelta.toFixed(1) + "pp pass rate for ~" + tokRatio.toFixed(1) + "\u00d7 token spend.";
      }
    }
    if(narrative){
      html += '<div class="bench-cost-narrative">' + esc(narrative) + '</div>';
    }
    html += '</div>'; /* card */
    return html;
  };
})();

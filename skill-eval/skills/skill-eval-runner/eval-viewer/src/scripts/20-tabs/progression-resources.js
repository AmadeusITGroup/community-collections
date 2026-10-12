/* Progression Resource Usage. Per-iteration grouped columns
   (Base / Current / Δ) for each metric (Time, Tokens, Tool calls, Steps).
   Sparklines render inline above the table when ≥2 iterations exist. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var mean = EV.metricMean;

  /* Resource cells use em-dash for nulls so dense tables stay clean. */
  function fmtTime(v){ return v == null ? "—" : parseFloat(v).toFixed(1) + "s"; }
  function fmtNum(v){  return v == null ? "—" : Math.round(parseFloat(v)).toLocaleString(); }
  function fmtTokens(v){ return v == null ? "N/A" : EV.formatTokenCount(v); }
  function fmtDec(v){  return v == null ? "—" : Number(v).toFixed(1); }

  var METRICS = [
    {label:"Avg Time",       key:"time_seconds", fmt:fmtTime, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDec(d) + "s"; }},
    {label:"Avg Tokens",     key:"tokens",       fmt:fmtTokens, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + EV.formatTokenCount(d); }},
    {label:"Avg Tool Calls", key:"tool_calls",   fmt:fmtDec,  deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDec(d); }},
    {label:"Avg Agent Turns", key:"steps",       fmt:fmtDec,  deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDec(d); }}
  ];

  function variantsFor(iter){
    var rs = iter.run_summary || {};
    var isRegression = (iter.comparison_mode === "regression");
    return {
      isRegression: isRegression,
      ws:  rs.current_skill || {},
      base: (isRegression && rs.previous_skill) ? rs.previous_skill : (rs.without_skill || {}),
      modeLabel: isRegression ? "Iter " + iter.iteration + " (regression)" : "Iter " + iter.iteration + " (baseline)"
    };
  }

  function currentMetricFor(iter, variants, metric){
    var value = mean(variants.ws, metric.key);
    var session = null;
    if(metric.key === "tokens" && value == null){
      session = EV.iterationSessionUsageAverage(iter.iteration, "total_tokens");
      if(session) value = session.value;
    }
    return { value: value, session: session };
  }

  function previousMetricFor(iter, variants, metric){
    var value = mean(variants.base, metric.key);
    var session = null;
    if(metric.key === "tokens" && variants.isRegression && value == null){
      var previousIteration = Number.isInteger(iter.previous_iteration)
        ? iter.previous_iteration
        : iter.iteration - 1;
      if(Number.isInteger(previousIteration) && previousIteration > 0){
        session = EV.iterationSessionUsageAverage(previousIteration, "total_tokens");
        if(session) value = session.value;
      }
    }
    return { value: value, session: session };
  }

  function sparkline(points, color){
    if(!points.length) return "";
    var W = 320, H = 60, PAD = 4;
    var plotW = W - PAD * 2, plotH = H - PAD * 2;
    var values = points.map(function(p){ return p.y; });
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    if(hi === lo){ hi = lo + 1; }
    var coords = points.map(function(p, i){
      var x = points.length === 1 ? PAD + plotW / 2 : PAD + (i / (points.length - 1)) * plotW;
      var y = PAD + plotH - ((p.y - lo) / (hi - lo)) * plotH;
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    var svg = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg">';
    svg += '<polyline fill="none" stroke="' + color + '" stroke-width="1.8" points="' + coords + '"/>';
    points.forEach(function(p, i){
      var x = points.length === 1 ? PAD + plotW / 2 : PAD + (i / (points.length - 1)) * plotW;
      var y = PAD + plotH - ((p.y - lo) / (hi - lo)) * plotH;
      svg += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2.2" fill="' + color + '"/>';
    });
    svg += '</svg>';
    return svg;
  }

  EV.buildProgressionResourceUsage = function buildProgressionResourceUsage(iters){
    if(!iters || !iters.length){
      return '<p style="color:var(--text-muted);text-align:center">No data</p>';
    }

    /* Keep only iterations that have a run_summary (guard against partial data). */
    var validIters = iters.filter(function(it){ return it && it.run_summary; });
    if(!validIters.length){
      return '<p style="color:var(--text-muted);text-align:center">No resource data</p>';
    }

    var html = '';

    /* Sparklines render inline above the table when ≥2 iterations exist
       (1 point isn't a trend — suppress entirely in that case). */
    if(validIters.length >= 2){
      var sparkRows = '';
      var colorCurrent = "var(--var-current)";
      METRICS.forEach(function(m){
        var points = validIters.map(function(it){
          var v = variantsFor(it);
          var y = currentMetricFor(it, v, m).value;
          return y == null ? null : { x: it.iteration, y: y };
        }).filter(function(p){ return p != null; });
        if(points.length < 2) return;
        var lastVal = points[points.length - 1].y;
        sparkRows += '<div class="resource-sparkline">';
        sparkRows += '<div class="spark-label">' + m.label + ' (current)</div>';
        sparkRows += '<div class="spark-value">' + m.fmt(lastVal) + '</div>';
        sparkRows += sparkline(points, colorCurrent);
        sparkRows += '</div>';
      });
      if(sparkRows){
        html += '<div class="resource-sparklines">' + sparkRows + '</div>';
      }
    }

    html += '<table class="resource-table">';
    /* Grouped header row. Model badge sits below "Iter N" so the reader can
       attribute time/token deltas to the model that produced them. Mixed-model
       iterations get a styled badge so the confound is visible at a glance. */
    html += '<thead><tr class="group-header"><th></th>';
    validIters.forEach(function(it, idx){
      var v = variantsFor(it);
      var cls = idx > 0 ? ' class="group-boundary"' : '';
      var model = EV.iterationModel ? EV.iterationModel(it.iteration, "current_skill") : null;
      var modelTitle = model && model.source === "session"
        ? "Session-level model(s), not attributed to individual evals: " + model.models.join(", ")
        : (model ? (model.mixed
          ? "Mixed current_skill models: " + model.models.join(", ")
          : "Per-run current_skill model: " + model.label) : "");
      var modelBadge = model
        ? '<div class="iter-model-badge' + (model.mixed ? ' mixed' : '') +
          '" title="' + esc(modelTitle) + '">' +
          esc(model.label) + '</div>'
        : '';
      html += '<th colspan="3"' + cls + ' title="' + v.modeLabel + '">Iter ' +
        it.iteration + modelBadge + '</th>';
    });
    html += '</tr>';
    /* Sub-header row. */
    html += '<tr><th>Metric</th>';
    validIters.forEach(function(it, idx){
      var v = variantsFor(it);
      var base = v.isRegression ? "Prev" : "Base";
      var bcls = idx > 0 ? ' class="group-boundary"' : '';
      html += '<th' + bcls + '>' + base + '</th><th>Current</th><th>Δ</th>';
    });
    html += '</tr></thead><tbody>';

    METRICS.forEach(function(m){
      /* Skip rows where no iter has any value — keeps the table lean. */
      var any = validIters.some(function(it){
        var v = variantsFor(it);
        return currentMetricFor(it, v, m).value != null ||
          previousMetricFor(it, v, m).value != null ||
          (m.key === "tokens" && (
            (v.ws && Object.prototype.hasOwnProperty.call(v.ws, "tokens")) ||
            (v.base && Object.prototype.hasOwnProperty.call(v.base, "tokens"))
          ));
      });
      if(!any) return;
      html += '<tr><td>' + m.label + '</td>';
      validIters.forEach(function(it, idx){
        var v = variantsFor(it);
        var baseMetric = previousMetricFor(it, v, m);
        var currentMetric = currentMetricFor(it, v, m);
        var bVal = baseMetric.value;
        var cVal = currentMetric.value;
        var bSession = baseMetric.session;
        var cSession = currentMetric.session;
        var d = (bVal != null && cVal != null &&
          !(bSession && bSession.partial) &&
          !(cSession && cSession.partial)) ? cVal - bVal : null;
        var bcls = idx > 0 ? ' class="group-boundary"' : '';
        var baselineTitle = "";
        if(m.key === "tokens" && bVal != null){
          var baseTitle = bSession
            ? EV.sessionUsageAverageTitle(bSession) + " "
            : "";
          baseTitle += "Exact displayed average: " + formatNum(bVal) + " tokens.";
          baselineTitle = ' title="' + esc(baseTitle) + '"';
        }
        html += '<td' + bcls + baselineTitle + '>' + m.fmt(bVal) + '</td>';
        var sessionTitle = "";
        if(m.key === "tokens" && cVal != null){
          var title = cSession
            ? EV.sessionUsageAverageTitle(cSession) + " "
            : "";
          title += "Exact displayed average: " + formatNum(cVal) + " tokens.";
          sessionTitle = ' title="' + esc(title) + '"';
        }
        html += '<td' + sessionTitle + '>' + m.fmt(cVal) + '</td>';
        var chipCls = "flat";
        if(d != null && d !== 0){
          chipCls = d < 0 ? "pos" : "cost";
        }
        var deltaTitle = "";
        if(m.key === "tokens" && d != null){
          var deltaDescription = bSession || cSession
            ? "One or both values use display-only session averages, which " +
              "include shared framework usage and are not per-run measurements. "
            : "";
          deltaDescription += "Exact token difference: " + formatNum(d) + " tokens.";
          deltaTitle = ' title="' + esc(deltaDescription) + '"';
        }
        html += '<td class="cell-delta"' + deltaTitle + '>' +
          (d == null ? "—" : ('<span class="delta-chip ' + chipCls + '">' + m.deltaFmt(d) + '</span>')) +
          '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';

    return html;
  };
})();

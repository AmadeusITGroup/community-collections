/* Progression Skill Feedback Trend — Blocking / Major / Minor impact
   columns, Δ pill per row after iter-1, subtitle headline delta story,
   and "top categories moved" footer. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var CATEGORIES = ["missing_from_skill","ambiguous_instructions","broken_references","outdated_or_wrong"];

  function labelize(s){
    return String(s || "").replace(/_/g, " ");
  }

  EV.buildProgressionSkillFeedbackTrend = function buildProgressionSkillFeedbackTrend(){
    if(typeof D === "undefined") return "";
    var benchmarks = D.iteration_benchmarks || {};
    var keys = Object.keys(benchmarks).sort(function(a, b){ return parseInt(a, 10) - parseInt(b, 10); });
    var points = [];
    keys.forEach(function(k){
      var rollup = (benchmarks[k] && benchmarks[k].skill_feedback_rollup) || null;
      if(!rollup) return;
      var totals = rollup.totals || {};
      var total = CATEGORIES.reduce(function(s, c){ return s + (totals[c] || 0); }, 0);
      var impact = rollup.by_impact || {};
      points.push({
        iter: parseInt(k, 10),
        total: total,
        blocking: impact.blocking || 0,
        major:    impact.major    || 0,
        minor:    impact.minor    || 0,
        totals:   totals
      });
    });
    if(!points.length) return "";

    /* Headline story line: "N → M items · X major → Y major" */
    var first = points[0], last = points[points.length - 1];
    var subtitle = "";
    if(points.length >= 2){
      subtitle += '<strong>' + first.total + '</strong> \u2192 <strong>' + last.total + '</strong> items';
      if(first.major !== last.major){
        subtitle += ' \u00b7 <strong>' + first.major + '</strong> major \u2192 <strong>' + last.major + '</strong> major';
      }
    } else {
      subtitle += '<strong>' + last.total + '</strong> items flagged';
    }

    var max = Math.max.apply(null, points.map(function(p){ return p.total; })) || 1;

    var html = '<div class="sf-trend-subtitle">' + subtitle + '</div>';
    html += '<table class="sf-trend-table"><thead><tr>';
    html += '<th>Iteration</th>';
    html += '<th>Total</th>';
    html += '<th>Blocking</th>';
    html += '<th>Major</th>';
    html += '<th>Minor</th>';
    html += '<th>Trend</th>';
    html += '<th>\u0394</th>';
    html += '</tr></thead><tbody>';
    points.forEach(function(p, i){
      var pct = (p.total / max * 100).toFixed(0);
      var deltaHtml = '';
      if(i > 0){
        var prevTotal = points[i - 1].total;
        var d = p.total - prevTotal;
        if(Math.abs(d) < 0.5){
          deltaHtml = '<span class="delta-chip flat">=</span>';
        } else {
          var cls = d < 0 ? "pos" : "neg"; /* fewer items is good */
          var sign = d > 0 ? "+" : "";
          deltaHtml = '<span class="delta-chip ' + cls + '">' + sign + d + '</span>';
        }
      } else {
        deltaHtml = '<span style="color:var(--text-light)">\u2014</span>';
      }
      html += '<tr>';
      html += '<td>Iter ' + p.iter + '</td>';
      html += '<td>' + p.total + '</td>';
      html += '<td' + (p.blocking > 0 ? ' style="color:var(--red);font-weight:700"' : '') + '>' + p.blocking + '</td>';
      html += '<td' + (p.major > 0 ? ' style="color:var(--warn);font-weight:700"' : '') + '>' + p.major + '</td>';
      html += '<td style="color:var(--text-muted)">' + p.minor + '</td>';
      html += '<td><div class="sf-trend-bar-track"><span class="sf-trend-bar-fill" style="width:' + pct + '%"></span></div></td>';
      html += '<td>' + deltaHtml + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';

    /* Top categories moved (iter1 → iterN category deltas). */
    if(points.length >= 2){
      var deltas = CATEGORIES.map(function(c){
        return { cat: c, d: (last.totals[c] || 0) - (first.totals[c] || 0) };
      }).filter(function(x){ return x.d !== 0; });
      deltas.sort(function(a, b){ return Math.abs(b.d) - Math.abs(a.d); });
      if(deltas.length){
        var top = deltas.slice(0, 3).map(function(x){
          var sign = x.d > 0 ? "+" : "";
          return '<strong>' + labelize(x.cat) + '</strong> (' + sign + x.d + ')';
        }).join(" \u00b7 ");
        html += '<div class="sf-trend-categories">Top categories moved: ' + top + '</div>';
      }
    }

    return html;
  };
})();

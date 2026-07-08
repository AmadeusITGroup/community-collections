/* Benchmark Headline card — pass-rate hero + comparator verdict in one
   "did it work?" panel. Regression mode shows three bars
   (baseline/previous/current) plus a "Δ +X pp vs prev · +Y pp vs baseline"
   line; baseline mode shows two bars and a single Δ vs baseline line.

   Data sources:
     • src.run_summary.{current_skill,without_skill,previous_skill}.pass_rate.mean
     • src.comparisons (wins/losses/ties — both regression + baseline shapes)
     • src.contradictions.length — "N contradictions with grader" footnote */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  function pct01(v){
    if(v == null) return "N/A";
    return (v * 100).toFixed(1) + "%";
  }
  function fmtPp(delta01){
    if(delta01 == null) return "";
    var pp = delta01 * 100;
    var sign = pp >= 0 ? "+" : "";
    return sign + pp.toFixed(1) + "pp";
  }

  function bar(slot, label, rate, maxRate, version){
    var pct = rate == null ? 0 : rate * 100;
    var fillW = maxRate ? Math.min(100, pct) : pct;
    var versionHtml = version
      ? ' <span class="variant-pill-version">v' + esc(version) + '</span>'
      : '';
    return (
      '<div class="bench-passrate-label">' +
        '<span class="variant-pill ' + slot + '">' + label + versionHtml + '</span>' +
      '</div>' +
      '<div class="bench-passrate-track">' +
        '<div class="bench-passrate-fill ' + slot + '" style="width:' + fillW.toFixed(1) + '%"></div>' +
      '</div>' +
      '<div class="bench-passrate-num">' + pct01(rate) + '</div>'
    );
  }

  EV.buildBenchmarkHeadlineCard = function buildBenchmarkHeadlineCard(src){
    if(!src) return "";
    var rs = src.run_summary || {};
    var mode = getComparisonMode();

    var wsRate = rs.current_skill && rs.current_skill.pass_rate ? rs.current_skill.pass_rate.mean : null;
    var wosRate = rs.without_skill && rs.without_skill.pass_rate ? rs.without_skill.pass_rate.mean : null;
    var prevRate = rs.previous_skill && rs.previous_skill.pass_rate ? rs.previous_skill.pass_rate.mean : null;

    var comp = src.comparisons || {};
    var wins = comp.current_wins != null ? comp.current_wins : comp.current_skill_wins;
    var losses = comp.previous_wins != null ? comp.previous_wins : comp.without_skill_wins;
    var ties = comp.regression_ties != null ? comp.regression_ties : comp.ties;
    var w = (wins != null ? wins : 0), l = (losses != null ? losses : 0), t = (ties != null ? ties : 0);
    var total = w + l + t;
    var winRatePct = total > 0 ? (w / total * 100).toFixed(0) + "%" : "N/A";

    var contradictionsCount = (src.contradictions || []).length;

    var meta = src.metadata || {};
    var currentVersion = meta.skill_version || null;
    var prevVersion = null;
    if(meta.previous_iteration != null){
      var prevBench = getBenchmarkData(meta.previous_iteration);
      prevVersion = prevBench && prevBench.metadata ? prevBench.metadata.skill_version : null;
    }

    var html = '';
    html += '<div class="sec-heading" id="sec-headline" data-section="headline">';
    html += '<span class="sec-icon">' + NAV_ICONS.headline + '</span>';
    html += '<h2>Headline</h2></div>';
    html += '<div class="card">';
    html += '<div class="bench-headline-body">';
    html += '<div class="bench-passrate">';
    if(mode === "regression"){
      html += bar("baseline", "Baseline", wosRate, false, null);
      html += bar("previous", "Previous", prevRate, false, prevVersion);
      html += bar("current",  "Current",  wsRate,  false, currentVersion);
    } else {
      html += bar("baseline", "Baseline", wosRate, false, null);
      html += bar("current",  "Skill", wsRate, false, currentVersion);
    }
    html += '</div>';

    /* Δ line */
    var deltas = [];
    if(mode === "regression"){
      if(wsRate != null && prevRate != null) deltas.push(fmtPp(wsRate - prevRate) + " vs prev");
      if(wsRate != null && wosRate != null) deltas.push(fmtPp(wsRate - wosRate) + " vs baseline");
    } else {
      if(wsRate != null && wosRate != null) deltas.push(fmtPp(wsRate - wosRate) + " vs baseline");
    }
    if(deltas.length){
      html += '<div class="bench-verdict-sub" style="margin-top:-4px">' +
        '<span><strong>\u0394</strong> ' + deltas.join(" \u00b7 ") + '</span>' +
        '</div>';
    }

    html += '<div class="bench-headline-divider"></div>';

    /* Comparator verdict strip */
    html += '<div>';
    html += '<div class="bench-verdict-heading">Comparator Verdict <span class="bench-verdict-meta">(blind, ' + total + ' evals)</span></div>';
    html += '<div class="bench-verdict-strip">';
    html += '<div class="verdict-block"><span class="verdict-num wins">' + w + '</span><span class="verdict-label">wins</span></div>';
    html += '<div class="verdict-block"><span class="verdict-num losses">' + l + '</span><span class="verdict-label">losses</span></div>';
    html += '<div class="verdict-block"><span class="verdict-num ties">' + t + '</span><span class="verdict-label">ties</span></div>';
    html += '</div>';
    html += '<div class="bench-verdict-sub">';
    html += '<span><strong>' + winRatePct + '</strong> win rate</span>';
    html += '<span><strong>' + contradictionsCount + '</strong> contradiction' + (contradictionsCount === 1 ? '' : 's') + ' with grader</span>';
    html += '</div>';
    html += '</div>';

    html += '</div>'; /* bench-headline-body */
    html += '</div>'; /* card */
    return html;
  };
})();

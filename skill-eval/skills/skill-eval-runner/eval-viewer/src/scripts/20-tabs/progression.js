/* Progression tab orchestration. Owns Overview, Pass-Rate Trend, Health
   Signals, and dispatches the heavy sections (Heatmap, Resource Usage,
   Skill Feedback Trend) to dedicated builders on `window.__EV`. */

function buildHealthSignalsCard(iters){
  if(!iters || !iters.length) return "";
  var rows = [];
  var anySignal = false;
  iters.forEach(function(it){
    var bench = getBenchmarkData(it.iteration);
    if(!bench) return;
    var cContradictions = (bench.contradictions || []).length;
    var sr = bench.skill_regressions || {};
    var cBaseline = (sr.vs_baseline || []).length;
    var cPrevious = (sr.vs_previous || []).length;
    var rs = bench.run_summary || {};
    var wsPr = rs.current_skill && rs.current_skill.pass_rate ? rs.current_skill.pass_rate.mean : null;
    if(cContradictions > 0 || cBaseline > 0 || cPrevious > 0) anySignal = true;
    var EV = window.__EV || {};
    var model = EV.iterationModel ? EV.iterationModel(it.iteration, "current_skill") : null;
    var skillVersion = bench.metadata && bench.metadata.skill_version;
    rows.push({
      iteration: it.iteration,
      pass_rate: wsPr,
      contradictions: cContradictions,
      regBaseline: cBaseline,
      regPrevious: cPrevious,
      mode: bench.comparison_mode || (it.comparison_mode || "baseline"),
      model: model,
      skill_version: skillVersion || null
    });
  });
  if(!rows.length) return "";

  /* Only show the Model / Skill columns when at least one iteration has the
     data — keeps the table compact for older runs missing those fields. */
  var anyModel = rows.some(function(r){ return r.model; });
  var anySkillVersion = rows.some(function(r){ return r.skill_version; });

  var tableHtml = '<table class="data-table"><thead><tr>';
  tableHtml += '<th>Iteration</th>';
  if(anySkillVersion) tableHtml += '<th title="Version of the skill that was evaluated">Skill</th>';
  if(anyModel) tableHtml += '<th title="current_skill model used in this iteration">Model</th>';
  tableHtml += '<th class="num">Pass Rate</th>';
  tableHtml += '<th class="num" title="Grader vs comparator disagreed by ≥0.20">Contradictions</th>';
  tableHtml += '<th class="num" title="Comparator preferred without_skill over current_skill">vs Baseline</th>';
  tableHtml += '<th class="num" title="Comparator preferred previous_skill over current_skill">vs Previous</th>';
  tableHtml += '</tr></thead><tbody>';
  rows.forEach(function(r){
    tableHtml += '<tr>';
    tableHtml += '<td>#' + r.iteration + ' <span style="color:var(--text-light);font-size:0.72rem">' + esc(r.mode) + '</span></td>';
    if(anySkillVersion){
      if(r.skill_version){
        tableHtml += '<td>v' + esc(r.skill_version) + '</td>';
      } else {
        tableHtml += '<td style="color:var(--text-light)">—</td>';
      }
    }
    if(anyModel){
      if(r.model){
        var tip = r.model.mixed ? "Mixed: " + r.model.models.join(", ") : r.model.label;
        tableHtml += '<td><span class="iter-model-badge' + (r.model.mixed ? ' mixed' : '') + '" title="' + esc(tip) + '">' + esc(r.model.label) + '</span></td>';
      } else {
        tableHtml += '<td style="color:var(--text-light)">—</td>';
      }
    }
    tableHtml += '<td class="num">' + formatStatPct(r.pass_rate) + '</td>';
    tableHtml += '<td class="num" style="' + (r.contradictions > 0 ? "color:var(--warn);font-weight:700" : "color:var(--text-muted)") + '">' + r.contradictions + '</td>';
    tableHtml += '<td class="num" style="' + (r.regBaseline > 0    ? "color:var(--red);font-weight:700"  : "color:var(--text-muted)") + '">' + r.regBaseline + '</td>';
    tableHtml += '<td class="num" style="' + (r.regPrevious > 0    ? "color:var(--red);font-weight:700"  : "color:var(--text-muted)") + '">' + r.regPrevious + '</td>';
    tableHtml += '</tr>';
  });
  tableHtml += '</tbody></table>';

  /* Empty state — collapse the table behind a "Show per-iteration detail" disclosure. */
  if(!anySignal){
    return '<div class="card">' +
      '<p class="health-signals-empty">No contradictions or skill regressions detected.</p>' +
      '<details class="health-signals-details">' +
      '<summary class="signal-expand">Show per-iteration detail</summary>' +
      '<div style="overflow-x:auto">' + tableHtml + '</div>' +
      '</details></div>';
  }
  return '<div class="card" style="overflow-x:auto">' + tableHtml + '</div>';
}

function renderProgressionPage(){
  var iters = getIterationsUpTo(state.activeIteration);
  buildProgressionSidebar(iters);
  if(!iters.length){
    $main.innerHTML = '<div class="card" style="text-align:center;padding:60px;color:var(--text-muted)">No iteration data available.</div>';
    return;
  }
  var latest = iters[iters.length - 1];
  var rs = latest.run_summary || {};
  var ws = rs.current_skill || {};
  var isRegression = (latest.comparison_mode === "regression");
  var delta = (isRegression && rs.regression_delta) ? rs.regression_delta : (rs.delta || {});
  var deltaRefLabel = (isRegression && rs.regression_delta) ? "Previous" : "Baseline";

  var modeBadge = isRegression
    ? '<span class="mode-badge regression" title="Comparing against previous iteration">Regression mode</span>'
    : '<span class="mode-badge baseline" title="Comparing against no-skill baseline">Baseline mode</span>';

  var passRateMean = ws.pass_rate ? ws.pass_rate.mean : null;
  var passRateStddev = ws.pass_rate ? ws.pass_rate.stddev : null;
  var deltaPassRate = parseFloat(delta.pass_rate);
  var avgTokens = ws.tokens ? ws.tokens.mean : null;

  var html = "";
  html += secHeading(NAV_ICONS.overview, "Overview", "overview").replace('</div>', modeBadge + '</div>');
  html += '<div class="card-grid">';
  html += '<div class="metric-card"><div class="metric-label">Pass Rate (Current)</div>' +
    '<div class="metric-value accent">' + formatStatPct(passRateMean) + '</div>' +
    '<div class="metric-sub">± ' + formatStatPct(passRateStddev) + '</div></div>';
  html += '<div class="metric-card"><div class="metric-label">Δ vs ' + deltaRefLabel + '</div>' +
    '<div class="metric-value ' + (deltaPassRate >= 0 ? "green" : "red") + '">' + formatDelta(delta.pass_rate) + '</div>' +
    '<div class="metric-sub">pass rate</div></div>';
  html += '<div class="metric-card"><div class="metric-label">Evaluations</div>' +
    '<div class="metric-value accent">' + (latest.per_eval ? latest.per_eval.length : 0) + '</div>' +
    '<div class="metric-sub">test cases</div></div>';
  html += '<div class="metric-card"><div class="metric-label">Avg Tokens</div>' +
    '<div class="metric-value">' + (avgTokens != null ? Math.round(avgTokens).toLocaleString() : "N/A") + '</div>' +
    '<div class="metric-sub">per eval</div></div>';
  html += '</div>';

  html += secHeading(NAV_ICONS.trend, "Pass Rate Trend", "trend");
  html += '<div class="card">' + buildTrendChart(iters) + '</div>';

  var healthHtml = buildHealthSignalsCard(iters);
  if(healthHtml){
    html += secHeading(NAV_ICONS.health, "Health Signals", "health");
    html += healthHtml;
  }

  var EV = window.__EV;
  html += secHeading(NAV_ICONS.heatmap, "Eval Heatmap", "heatmap");
  html += '<div class="card" style="overflow-x:auto">' + EV.buildProgressionHeatmap(iters) + '</div>';

  html += secHeading(NAV_ICONS.resources, "Resource Usage", "resources");
  html += '<div class="card" style="overflow-x:auto">' + EV.buildProgressionResourceUsage(iters) + '</div>';

  var sfTrend = EV.buildProgressionSkillFeedbackTrend();
  if(sfTrend){
    html += secHeading(NAV_ICONS["sf-trend"], "Skill Feedback Trend", "sf-trend");
    html += '<div class="card">' + sfTrend + '</div>';
  }

  $main.innerHTML = html;
  bindChartTooltips();
  EV.bindProgressionHeatmap($main);
}

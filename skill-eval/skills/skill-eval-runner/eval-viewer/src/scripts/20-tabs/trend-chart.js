/* Pass-rate trend chart for the Progression tab.
     • current  (solid blue)  — rs.current_skill per iteration.
     • baseline (dashed slate, horizontal reference line) — iteration-1's
       rs.without_skill; subsequent regression iterations don't re-execute it.
   The previous_skill series is intentionally omitted: it duplicates the
   current series shifted by one iteration (iter N's "previous" is iter N-1's
   "current") and clutters the chart without adding signal. */

function buildTrendChart(iters){
  if(iters.length < 1) return '<p style="color:var(--text-muted);text-align:center">No data</p>';

  /* Bottom padding leaves room for two-line x-axis labels (Iter N + model
     name) when models differ across iterations. */
  var W = 640, H = 270, PAD_L = 50, PAD_R = 60, PAD_T = 20, PAD_B = 50;
  var plotW = W - PAD_L - PAD_R;
  var plotH = H - PAD_T - PAD_B;

  var wsPoints = [], wosPoints = [];
  var baselineVal = null;
  iters.forEach(function(it, i){
    var rs = it.run_summary || {};
    var x = iters.length === 1 ? PAD_L + plotW / 2 : PAD_L + (i / (iters.length - 1)) * plotW;
    var yOf = function(v){ return PAD_T + plotH - (v * plotH); };
    var wsVal   = rs.current_skill  && rs.current_skill.pass_rate  ? rs.current_skill.pass_rate.mean  : null;
    var wosVal  = rs.without_skill  && rs.without_skill.pass_rate  ? rs.without_skill.pass_rate.mean  : null;
    if(wsVal   != null) wsPoints  .push({x:x, y:yOf(wsVal),   val:wsVal,   iter:it.iteration});
    if(wosVal  != null) wosPoints .push({x:x, y:yOf(wosVal),  val:wosVal,  iter:it.iteration});
    if(i === 0 && wosVal != null) baselineVal = wosVal;
  });

  var svg = '<div class="chart-container" style="position:relative">';
  svg += '<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg">';

  /* Grid lines + Y-axis labels at each 25% increment. */
  for(var g = 0; g <= 4; g++){
    var gy = PAD_T + plotH - (g * 0.25 * plotH);
    svg += '<line x1="' + PAD_L + '" y1="' + gy + '" x2="' + (W - PAD_R) + '" y2="' + gy + '" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4,4"/>';
    svg += '<text x="' + (PAD_L - 8) + '" y="' + (gy + 4) + '" text-anchor="end" fill="var(--chart-text)" font-size="10">' + (g * 25) + '%</text>';
  }

  /* X-axis labels. Append the (short) model name on a second line when models
     differ between iterations — that's when the model is a confound for the
     pass-rate trend the reader is interpreting. Same model across all iters →
     model is noise, suppress it. */
  var EV = window.__EV || {};
  var iterModels = iters.map(function(it){
    return EV.iterationModel ? EV.iterationModel(it.iteration, "current_skill") : null;
  });
  var distinctModels = {};
  iterModels.forEach(function(m){ if(m) distinctModels[m.label] = true; });
  var showModelOnAxis = Object.keys(distinctModels).length > 1;

  iters.forEach(function(it, i){
    var x = iters.length === 1 ? PAD_L + plotW / 2 : PAD_L + (i / (iters.length - 1)) * plotW;
    svg += '<text x="' + x + '" y="' + (H - 22) + '" text-anchor="middle" fill="var(--chart-text)" font-size="10">Iter ' + it.iteration + '</text>';
    if(showModelOnAxis && iterModels[i]){
      var m = iterModels[i];
      svg += '<text x="' + x + '" y="' + (H - 8) + '" text-anchor="middle" fill="var(--text-light)" font-size="9" font-style="italic">' + m.label + '</text>';
    }
  });

  /* Baseline reference line + label. The label is rendered twice — once with a
     stroke matching --card-bg, once with the colored fill — so the text rides
     above the dotted line even when the grid crosses it. */
  if(baselineVal != null){
    var by = PAD_T + plotH - (baselineVal * plotH);
    svg += '<line x1="' + PAD_L + '" y1="' + by + '" x2="' + (W - PAD_R) + '" y2="' + by +
           '" stroke="var(--var-baseline)" stroke-width="1.5" stroke-dasharray="2,4" opacity="0.85"/>';
    svg += '<text class="trend-baseline-label-bg" x="' + (W - PAD_R - 4) + '" y="' + (by - 6) + '" text-anchor="end" font-size="10" font-weight="600">Baseline ' + (baselineVal * 100).toFixed(1) + '%</text>';
    svg += '<text x="' + (W - PAD_R - 4) + '" y="' + (by - 6) + '" text-anchor="end" fill="var(--var-baseline)" font-size="10" font-weight="600">Baseline ' + (baselineVal * 100).toFixed(1) + '%</text>';
  }

  /* Filled area + line for current_skill. */
  if(wsPoints.length > 1){
    var areaPath = 'M' + wsPoints[0].x + ',' + (PAD_T + plotH);
    wsPoints.forEach(function(p){ areaPath += ' L' + p.x + ',' + p.y; });
    areaPath += ' L' + wsPoints[wsPoints.length-1].x + ',' + (PAD_T + plotH) + ' Z';
    svg += '<path d="' + areaPath + '" fill="var(--var-current)" opacity="0.08"/>';
    var linePath = 'M' + wsPoints.map(function(p){return p.x+','+p.y}).join(' L');
    svg += '<path d="' + linePath + '" fill="none" stroke="var(--var-current)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  if(wosPoints.length > 1){
    var wosLinePath = 'M' + wosPoints.map(function(p){return p.x+','+p.y}).join(' L');
    svg += '<path d="' + wosLinePath + '" fill="none" stroke="var(--var-baseline)" stroke-width="2" stroke-dasharray="6,4" stroke-linecap="round" stroke-linejoin="round"/>';
  }

  /* Single-point halo so a one-iteration series still reads as data, not noise. */
  function haloSingle(pts, color){
    if(pts.length !== 1) return "";
    var p = pts[0];
    return '<circle cx="' + p.x + '" cy="' + p.y + '" r="10" fill="' + color + '" opacity="0.18"/>';
  }
  svg += haloSingle(wsPoints,   "var(--var-current)");
  svg += haloSingle(wosPoints,  "var(--var-baseline)");

  wsPoints.forEach(function(p){
    svg += '<circle cx="' + p.x + '" cy="' + p.y + '" r="5" fill="var(--var-current)" stroke="var(--card-bg)" stroke-width="2" class="chart-point" data-tip="Iter ' + p.iter + ': ' + (p.val * 100).toFixed(1) + '% (current)"/>';
  });
  if(wosPoints.length > 1){
    wosPoints.forEach(function(p){
      svg += '<circle cx="' + p.x + '" cy="' + p.y + '" r="4" fill="var(--var-baseline)" stroke="var(--card-bg)" stroke-width="2" class="chart-point" data-tip="Iter ' + p.iter + ': ' + (p.val * 100).toFixed(1) + '% (without skill)"/>';
    });
  }

  svg += '</svg>';

  /* Legend with the latest value beside each series so readers don't need to hover. */
  var latestWs = wsPoints.length ? wsPoints[wsPoints.length-1] : null;
  var legend = '<div class="chart-legend">';
  legend += '<span><span class="leg-line leg-solid" style="background:var(--var-current)"></span>Current' +
            (latestWs != null ? ' <strong style="color:var(--var-current);margin-left:4px">' + (latestWs.val*100).toFixed(1) + '%</strong>' : '') + '</span>';
  if(baselineVal != null){
    legend += '<span><span class="leg-line leg-dashed" style="background:repeating-linear-gradient(90deg,var(--var-baseline) 0,var(--var-baseline) 3px,transparent 3px,transparent 6px)"></span>Baseline <strong style="color:var(--var-baseline);margin-left:4px">' + (baselineVal*100).toFixed(1) + '%</strong></span>';
  }
  legend += '</div>';
  svg += legend;
  svg += '</div>';

  return svg;
}

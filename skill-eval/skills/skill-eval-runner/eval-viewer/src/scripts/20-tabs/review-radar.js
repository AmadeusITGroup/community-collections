/* Radar chart for the Review-tab Comparison panel.
   Flat-top hexagon: Content axes strictly in the top half (y<0), Structure
   axes strictly in the bottom half (y>0). Divider runs through y=0 between
   two horizontal hex edges, never through a vertex/axis. */

function buildRadarChart(rubricWos, rubricWs, rubricBaseline){
  var axes = [
    {key:"accuracy",     label:"Accuracy",     group:"content",   angle:-150},
    {key:"correctness",  label:"Correctness",  group:"content",   angle: -90},
    {key:"completeness", label:"Completeness", group:"content",   angle: -30},
    {key:"formatting",   label:"Formatting",   group:"structure", angle:  30},
    {key:"organization", label:"Organization", group:"structure", angle:  90},
    {key:"usability",    label:"Usability",    group:"structure", angle: 150}
  ];
  var RMAX = 100;

  function polar(score, angleDeg){
    var r = (Math.max(0, Math.min(5, score || 0)) / 5) * RMAX;
    var rad = angleDeg * Math.PI / 180;
    return {
      x: Math.round(r * Math.cos(rad) * 100) / 100,
      y: Math.round(r * Math.sin(rad) * 100) / 100
    };
  }

  function getScore(rubric, axis){
    if(!rubric) return null;
    var grp = rubric[axis.group];
    if(grp && grp[axis.key] != null) return grp[axis.key];
    return null;
  }

  function gridRing(scale){
    return '<circle class="radar-grid" cx="0" cy="0" r="' + (RMAX * scale) + '"/>';
  }

  /* viewBox accommodates external axis labels (RMAX + 18 ≈ 118 from origin)
     plus side gutters for CONTENT / STRUCTURE group labels. */
  var VB_X = -200, VB_Y = -150, VB_W = 400, VB_H = 300;
  var svg = '<svg width="100%" height="100%" viewBox="' + VB_X + ' ' + VB_Y + ' ' + VB_W + ' ' + VB_H + '" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">';

  svg += '<text class="radar-grouplabel" x="' + (VB_X + 6) + '" y="-6" text-anchor="start">▲ CONTENT</text>';
  svg += '<text class="radar-grouplabel" x="' + (VB_X + VB_W - 6) + '" y="14" text-anchor="end">STRUCTURE ▼</text>';

  svg += gridRing(0.33);
  svg += gridRing(0.66);
  svg += gridRing(1.0);
  svg += '<line class="radar-divider" x1="' + (VB_X + 4) + '" y1="0" x2="' + (VB_X + VB_W - 4) + '" y2="0"/>';

  axes.forEach(function(a){
    var end = polar(5, a.angle);
    svg += '<line class="radar-spoke" x1="0" y1="0" x2="' + end.x + '" y2="' + end.y + '"/>';
  });

  /* Baseline polygon drawn first so wos/ws overlay on top in regression mode. */
  var basePoints = [];
  if(rubricBaseline){
    var basePts = axes.map(function(a){
      var sc = getScore(rubricBaseline, a);
      var p = polar(sc || 0, a.angle);
      basePoints.push({score: sc, axis: a, p: p});
      return p.x + "," + p.y;
    }).join(" ");
    svg += '<polygon class="radar-area-baseline" points="' + basePts + '"/>';
  }

  var wosPoints = [];
  var wosPts = axes.map(function(a){
    var sc = getScore(rubricWos, a);
    var p = polar(sc || 0, a.angle);
    wosPoints.push({score: sc, axis: a, p: p});
    return p.x + "," + p.y;
  }).join(" ");
  if(rubricWos) svg += '<polygon class="radar-area-wos" points="' + wosPts + '"/>';

  var wsPoints = [];
  var wsPts = axes.map(function(a){
    var sc = getScore(rubricWs, a);
    var p = polar(sc || 0, a.angle);
    wsPoints.push({score: sc, axis: a, p: p});
    return p.x + "," + p.y;
  }).join(" ");
  if(rubricWs) svg += '<polygon class="radar-area-ws" points="' + wsPts + '"/>';

  /* Dots with mode-aware tooltips. */
  var radarMode = getComparisonMode();
  var wosFull = variantLabelFullForSide("wos", radarMode);
  var wsFull  = variantLabelFullForSide("ws",  radarMode);
  basePoints.forEach(function(pt){
    if(pt.score == null) return;
    svg += '<circle class="radar-dot-baseline" cx="' + pt.p.x + '" cy="' + pt.p.y + '" r="3" data-tip="' + esc(pt.axis.label) + ': ' + pt.score.toFixed(1) + ' (Baseline)"/>';
  });
  wosPoints.forEach(function(pt){
    if(pt.score == null) return;
    svg += '<circle class="radar-dot-wos" cx="' + pt.p.x + '" cy="' + pt.p.y + '" r="3.5" data-tip="' + esc(pt.axis.label) + ': ' + pt.score.toFixed(1) + ' (' + wosFull + ')"/>';
  });
  wsPoints.forEach(function(pt){
    if(pt.score == null) return;
    svg += '<circle class="radar-dot-ws" cx="' + pt.p.x + '" cy="' + pt.p.y + '" r="4" data-tip="' + esc(pt.axis.label) + ': ' + pt.score.toFixed(1) + ' (' + wsFull + ')"/>';
  });

  axes.forEach(function(a){
    var lblR = RMAX + 18;
    var rad = a.angle * Math.PI / 180;
    var lx = lblR * Math.cos(rad);
    var ly = lblR * Math.sin(rad);
    /* Vertical nudge keeps text strictly inside its zone and off the divider. */
    if(a.group === "content") ly -= 2;
    else                      ly += 10;
    var anchor = "middle";
    if(Math.abs(Math.cos(rad)) > 0.3){
      anchor = Math.cos(rad) > 0 ? "start" : "end";
    }
    var cls = a.group === "content" ? "content-grp" : "structure-grp";
    svg += '<text class="radar-label ' + cls + '" text-anchor="' + anchor + '" x="' + lx.toFixed(1) + '" y="' + ly.toFixed(1) + '">' + a.label + '</text>';
  });

  svg += '</svg>';
  return svg;
}

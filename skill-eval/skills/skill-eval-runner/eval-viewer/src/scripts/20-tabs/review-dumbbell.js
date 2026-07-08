/* Dumbbell chart for the Review-tab Comparison panel.
   Stacked panels: Content (sub-dims + content_score), Structure (sub-dims +
   structure_score), Overall. Sub-dim values live in rubric[group][key] on a
   0-5 scale; content_score / structure_score are 0-5 too (×2 to render on
   the 0-10 axis). overall_score is already 0-10 natively. */

function buildDumbbellChart(rubricWos, rubricWs, rubricBaseline){
  function subScore(r, group, key){
    if(!r) return null;
    var grp = r[group];
    if(grp && grp[key] != null) return grp[key] * 2;
    return null;
  }
  function aggScore(r, field, scale){
    if(!r || r[field] == null) return null;
    return r[field] * scale;
  }

  var dbMode = getComparisonMode();
  var dbWosFull = variantLabelFullForSide("wos", dbMode);
  var dbWsFull  = variantLabelFullForSide("ws",  dbMode);

  /* Read variant colors off `body` (not `:root`), since the regression-mode
     override `--var-wos: var(--var-previous)` is scoped to
     `body[data-comp-mode="regression"]`. Reading from documentElement would
     return the baseline-mode default and silently break regression coloring. */
  var cs = getComputedStyle(document.body);
  var varColors = {
    baseline: cs.getPropertyValue("--var-baseline").trim() || "#6c757d",
    wos:      cs.getPropertyValue("--var-wos").trim()      || "#6c757d",
    ws:       cs.getPropertyValue("--var-ws").trim()       || "#4361ee"
  };

  function rowHtml(row){
    var inner = '';
    inner += '<div class="label-wrap"><span class="label">' + row.label + '</span></div>';
    inner += '<div class="dumbbell-track">';
    inner += '<div class="dumbbell-scale"></div>';

    /* Render one gradient bar segment per pair of consecutive dots (sorted
       by score). Each segment fades from its left dot's color to its right
       dot's color, with the color transition landing exactly on the middle
       dot. Three-dot regression rows produce grey→orange + orange→blue;
       two-dot baseline rows produce a single grey→blue segment. */
    var stops = [];
    if(row.base != null) stops.push({ val: row.base, color: varColors.baseline });
    if(row.wos  != null) stops.push({ val: row.wos,  color: varColors.wos });
    if(row.ws   != null) stops.push({ val: row.ws,   color: varColors.ws });
    if(stops.length >= 2){
      stops.sort(function(a, b){ return a.val - b.val; });
      for(var i = 0; i < stops.length - 1; i++){
        var a = stops[i], b = stops[i + 1];
        if(a.val === b.val) continue;
        inner += '<div class="dumbbell-bar" style="left:' + (a.val / 10 * 100).toFixed(2) +
          '%;width:' + ((b.val - a.val) / 10 * 100).toFixed(2) +
          '%;background:linear-gradient(to right,' + a.color + ',' + b.color + ')"></div>';
      }
    }

    if(row.base != null){
      inner += '<div class="dumbbell-dot baseline" style="left:' + (row.base/10*100) + '%" data-tip="Baseline: ' + row.base.toFixed(1) + '/10"></div>';
    }
    if(row.wos != null){
      inner += '<div class="dumbbell-dot wos" style="left:' + (row.wos/10*100) + '%" data-tip="' + dbWosFull + ': ' + row.wos.toFixed(1) + '/10"></div>';
    }
    if(row.ws != null){
      inner += '<div class="dumbbell-dot ws" style="left:' + (row.ws/10*100) + '%" data-tip="' + dbWsFull + ': ' + row.ws.toFixed(1) + '/10"></div>';
    }
    inner += '</div>';

    var headline = row.ws != null ? row.ws.toFixed(1)
                  : row.wos != null ? row.wos.toFixed(1)
                  : row.base != null ? row.base.toFixed(1)
                  : '—';
    inner += '<div class="dumbbell-current-value">' + headline + '</div>';
    return '<div class="dumbbell-row' + (row.cls ? ' ' + row.cls : '') + '">' + inner + '</div>';
  }

  var contentSubs = [
    {key:"correctness",  label:"Correctness"},
    {key:"completeness", label:"Completeness"},
    {key:"accuracy",     label:"Accuracy"}
  ];
  var structureSubs = [
    {key:"organization", label:"Organization"},
    {key:"formatting",   label:"Formatting"},
    {key:"usability",    label:"Usability"}
  ];

  function buildSubRows(group, subs){
    return subs.map(function(s){
      return rowHtml({
        label: s.label,
        base: subScore(rubricBaseline, group, s.key),
        wos:  subScore(rubricWos, group, s.key),
        ws:   subScore(rubricWs, group, s.key)
      });
    }).join("");
  }

  var ticks = '<div class="dumbbell-ticks"><span>0</span><span>2</span><span>4</span><span>6</span><span>8</span><span>10</span></div>';

  var html = '<div class="db-group">';

  html += '<div class="db-section content">';
  html += '<div class="db-section-label">▲ Content</div>';
  html += buildSubRows("content", contentSubs);
  html += rowHtml({
    cls: "summary",
    label: "Content Score",
    base: aggScore(rubricBaseline, "content_score", 2),
    wos:  aggScore(rubricWos, "content_score", 2),
    ws:   aggScore(rubricWs, "content_score", 2)
  });
  html += '</div>';

  html += '<div class="db-section structure">';
  html += '<div class="db-section-label">▼ Structure</div>';
  html += buildSubRows("structure", structureSubs);
  html += rowHtml({
    cls: "summary",
    label: "Structure Score",
    base: aggScore(rubricBaseline, "structure_score", 2),
    wos:  aggScore(rubricWos, "structure_score", 2),
    ws:   aggScore(rubricWs, "structure_score", 2)
  });
  html += '</div>';

  html += '<div class="db-section overall">';
  html += '<div class="db-section-label">★ Overall</div>';
  html += rowHtml({
    cls: "overall-row",
    label: "Overall Score",
    base: aggScore(rubricBaseline, "overall_score", 1),
    wos:  aggScore(rubricWos, "overall_score", 1),
    ws:   aggScore(rubricWs, "overall_score", 1)
  });
  html += '</div>';

  html += ticks;
  html += '</div>';
  return html;
}

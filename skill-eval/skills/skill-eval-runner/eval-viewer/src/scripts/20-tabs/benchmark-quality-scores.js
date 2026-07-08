/* Benchmark Quality Scores — mean/min/max of all per-eval rubrics across
   the active iteration. Reuses buildRadarChart + buildDumbbellChart with
   aggregated values. Capped error-bars (min/max) are overlaid on the
   dumbbell rows via absolutely-positioned .bench-qs-errorbar spans,
   rendered only when max-min > 1.5 points per row (below that threshold
   the bars read as noise).

   Data source: D.iteration_runs[activeIter] — each run carries a
   .comparison payload keyed by the same A/B assignment used by the
   per-eval Review tab. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var SUB_AXES = [
    {group:"content",   key:"correctness"},
    {group:"content",   key:"completeness"},
    {group:"content",   key:"accuracy"},
    {group:"structure", key:"organization"},
    {group:"structure", key:"formatting"},
    {group:"structure", key:"usability"}
  ];

  function collectRuns(iter){
    return (D.iteration_runs && D.iteration_runs[String(iter)]) || [];
  }

  function variantRubricFromRun(run, variant){
    if(!run || !run.comparison || !run.comparison.rubric) return null;
    var assign = run.comparison.assignment || {};
    var r = run.comparison.rubric;
    if(assign.A === variant) return r.A || null;
    if(assign.B === variant) return r.B || null;
    return null;
  }

  function pushScore(bucket, key, val){
    if(val == null || Number.isNaN(val)) return;
    if(!bucket[key]) bucket[key] = { values: [] };
    bucket[key].values.push(val);
  }

  function stats(values){
    if(!values || !values.length) return null;
    var sum = 0, lo = Infinity, hi = -Infinity;
    for(var i = 0; i < values.length; i++){
      var v = values[i];
      sum += v;
      if(v < lo) lo = v;
      if(v > hi) hi = v;
    }
    return { mean: sum / values.length, min: lo, max: hi, n: values.length };
  }

  /* Collapse a variant's accumulator into a rubric object shaped like
     {content:{correctness,completeness,accuracy},structure:{...},content_score,
      structure_score,overall_score}. Also returns a parallel "stats" shape with
     {mean,min,max,n} per leaf, for the whisker overlay. */
  function freezeAccum(accum){
    var rubric = {
      content: {},
      structure: {},
      content_score: null,
      structure_score: null,
      overall_score: null
    };
    var statsOut = {
      content: {},
      structure: {},
      content_score: null,
      structure_score: null,
      overall_score: null
    };
    SUB_AXES.forEach(function(ax){
      var s = stats((accum[ax.group] && accum[ax.group][ax.key]) ? accum[ax.group][ax.key].values : []);
      if(s){
        rubric[ax.group][ax.key] = s.mean;
        statsOut[ax.group][ax.key] = s;
      }
    });
    ["content_score","structure_score","overall_score"].forEach(function(k){
      var s = stats(accum[k] ? accum[k].values : []);
      if(s){
        rubric[k] = s.mean;
        statsOut[k] = s;
      }
    });
    return { rubric: rubric, stats: statsOut, hasData: Object.keys(rubric.content).length + Object.keys(rubric.structure).length > 0 };
  }

  /* Walk every run with a comparison payload and pull the rubric for the
     requested variant via the A/B assignment. We do NOT filter by
     `run.variant`, because the rubric for previous_skill is embedded in
     current_skill runs' comparison data — there's no on-disk previous_skill
     run dir for regression iterations. Each comparison contributes at most
     one rubric per variant, so duplicates are naturally avoided. */
  function aggregateVariant(runs, variant){
    var accum = { content: {}, structure: {}, content_score: { values: [] }, structure_score: { values: [] }, overall_score: { values: [] } };
    var seenEvalIds = {};
    runs.forEach(function(run){
      var rub = variantRubricFromRun(run, variant);
      if(!rub) return;
      var key = run.eval_id != null ? String(run.eval_id) : (run.path || Math.random());
      if(seenEvalIds[key]) return;
      seenEvalIds[key] = true;
      SUB_AXES.forEach(function(ax){
        var grp = rub[ax.group] || {};
        pushScore(accum[ax.group], ax.key, grp[ax.key] != null ? Number(grp[ax.key]) : null);
      });
      if(rub.content_score != null) accum.content_score.values.push(Number(rub.content_score));
      if(rub.structure_score != null) accum.structure_score.values.push(Number(rub.structure_score));
      if(rub.overall_score != null) accum.overall_score.values.push(Number(rub.overall_score));
    });
    return freezeAccum(accum);
  }

  /* For regression-mode baseline polygon: the baseline iteration's
     without_skill rubric, resolved from iteration_runs[baseline_iter]. */
  function resolveBaselineRuns(){
    var base = (D.served_iteration_config || {}).baseline_iteration || 1;
    return (D.iteration_runs && D.iteration_runs[String(base)]) || [];
  }

  /* Capped error-bar overlay. Each variant emits one span that owns:
       • a horizontal line at full opacity (the span itself)
       • two vertical caps at the endpoints (via ::before / ::after)
     Positioned absolutely inside the .dumbbell-track, below the dots.
     Rendered whenever a variant has spread between min and max — even small
     spreads matter on aggregate score rows because they signal whether the
     average is masking variance from sub-dimensions. */
  function whiskerOverlayHtml(statsByVariant, rowKey, isSubField, group){
    var pieces = "";
    var currentLabel = getComparisonMode() === "regression" ? "Current" : "Skill";
    var slotLabels = { baseline: "Baseline", previous: "Previous", current: currentLabel };
    ["baseline","previous","current"].forEach(function(slot){
      var s = statsByVariant[slot];
      if(!s) return;
      var scoreStats = isSubField ? (s[group] && s[group][rowKey]) : s[rowKey];
      if(!scoreStats) return;
      var scale = isSubField ? 2 : (rowKey === "overall_score" ? 1 : 2);
      var minPct = (scoreStats.min * scale) / 10 * 100;
      var maxPct = (scoreStats.max * scale) / 10 * 100;
      var span = maxPct - minPct;
      if(span <= 0) return;
      var minVal = scoreStats.min * scale;
      var maxVal = scoreStats.max * scale;
      var tip = slotLabels[slot] + " · min " + minVal.toFixed(1) +
                " · max " + maxVal.toFixed(1);
      pieces += '<span class="bench-qs-errorbar ' + slot + '" data-tip="' + tip + '" ' +
        'style="left:' + minPct.toFixed(2) + '%;width:' + span.toFixed(2) + '%"></span>';
    });
    return pieces;
  }

  function injectWhiskersIntoDumbbellHtml(dumbbellHtml, statsByVariant){
    /* The dumbbell HTML is a string built by buildDumbbellChart — each
       .dumbbell-row contains a .dumbbell-track which is where we want to
       append the whisker spans. We match rows by their summary labels and
       the order of sub-axes. This is fragile vs a structural rewrite but
       keeps the shared primitive intact. */
    /* Row order produced by buildDumbbellChart: content(correctness,completeness,accuracy),content_score,structure(organization,formatting,usability),structure_score,overall. */
    var rowOrder = [
      {isSub:true,  group:"content",  key:"correctness"},
      {isSub:true,  group:"content",  key:"completeness"},
      {isSub:true,  group:"content",  key:"accuracy"},
      {isSub:false, key:"content_score"},
      {isSub:true,  group:"structure", key:"organization"},
      {isSub:true,  group:"structure", key:"formatting"},
      {isSub:true,  group:"structure", key:"usability"},
      {isSub:false, key:"structure_score"},
      {isSub:false, key:"overall_score"}
    ];
    /* Split on track-close boundary so we can inject whiskers before the
       closing </div> of each .dumbbell-track. */
    var parts = dumbbellHtml.split('<div class="dumbbell-track">');
    /* parts[0] is everything before the first track. Each subsequent part
       starts with track innerHTML then the rest. For each row we re-stitch
       with whisker spans appended just before the last </div> of the track
       block (which closes the .dumbbell-track). */
    if(parts.length - 1 !== rowOrder.length){
      /* Row count drift — skip the overlay rather than misalign. */
      return dumbbellHtml;
    }
    var rebuilt = parts[0];
    for(var i = 1; i < parts.length; i++){
      var chunk = parts[i];
      /* Whiskers belong inside the track (position:absolute child) — inject
         at the end of track content. The track content runs from start of
         chunk up to the first '</div>' that closes it. */
      var closeIdx = chunk.indexOf('</div>');
      var row = rowOrder[i - 1];
      var whisk = whiskerOverlayHtml(statsByVariant, row.key, row.isSub, row.group);
      rebuilt += '<div class="dumbbell-track">' + chunk.slice(0, closeIdx) + whisk + chunk.slice(closeIdx);
    }
    return rebuilt;
  }

  EV.buildBenchmarkQualityScoresCard = function buildBenchmarkQualityScoresCard(src){
    if(!src) return "";
    var iter = (typeof state !== "undefined" && state.activeIteration) ? state.activeIteration : null;
    if(iter == null) return "";
    var runs = collectRuns(iter);
    if(!runs.length) return "";

    var mode = getComparisonMode();

    /* Aggregate per variant. */
    var aggCurrent = aggregateVariant(runs, "current_skill");
    var aggWos = aggregateVariant(runs, "without_skill");
    var aggPrev = (mode === "regression") ? aggregateVariant(runs, "previous_skill") : { rubric: null, stats: null, hasData: false };

    /* Regression-mode baseline polygon from iteration-1's without_skill runs. */
    var aggBaseline = { rubric: null, stats: null, hasData: false };
    if(mode === "regression"){
      var baseRuns = resolveBaselineRuns();
      if(baseRuns.length){
        aggBaseline = aggregateVariant(baseRuns, "without_skill");
      }
    }

    /* Bail if nothing aggregated. */
    if(!aggCurrent.hasData && !aggWos.hasData && !aggPrev.hasData && !aggBaseline.hasData) return "";

    /* Map to rubricWos / rubricWs / rubricBaseline used by the shared charts.
       Baseline mode: wos = without_skill, ws = current_skill, baseline = null.
       Regression mode: wos = previous_skill, ws = current_skill, baseline = baseline-iter without_skill.
    */
    var rubricWs = aggCurrent.hasData ? aggCurrent.rubric : null;
    var rubricWos, rubricBaseline;
    if(mode === "regression"){
      rubricWos = aggPrev.hasData ? aggPrev.rubric : null;
      rubricBaseline = aggBaseline.hasData ? aggBaseline.rubric : null;
    } else {
      rubricWos = aggWos.hasData ? aggWos.rubric : null;
      rubricBaseline = null;
    }

    var statsByVariant = {
      current: aggCurrent.hasData ? aggCurrent.stats : null,
      previous: (mode === "regression" && aggPrev.hasData) ? aggPrev.stats : null,
      baseline: (mode === "regression" ? (aggBaseline.hasData ? aggBaseline.stats : null) : (aggWos.hasData ? aggWos.stats : null))
    };

    /* Section-head pills with averaged overall_score. */
    function pillFor(slot, label, overallMean, title){
      var score = overallMean != null ? overallMean.toFixed(1) + "/10" : "N/A";
      var titleAttr = title ? ' title="' + esc(title) + '"' : '';
      return '<span class="variant-pill ' + slot + '"' + titleAttr + '>' + label + '<span class="pct">' + score + '</span></span>';
    }
    var pills = '';
    if(mode === "regression"){
      if(rubricBaseline) pills += pillFor("baseline", "Baseline", rubricBaseline.overall_score);
      if(rubricWos) pills += pillFor("previous", "Previous", rubricWos.overall_score,
        "Previous-iteration responses re-graded by this iteration's comparator. " +
        "May differ from the original iteration's grading.");
    } else {
      if(rubricWos) pills += pillFor("baseline", "Baseline", rubricWos.overall_score);
    }
    if(rubricWs) pills += pillFor("current", mode === "regression" ? "Current" : "Skill", rubricWs.overall_score);

    var radarHtml = buildRadarChart(rubricWos, rubricWs, rubricBaseline);
    var dumbbellHtml = injectWhiskersIntoDumbbellHtml(
      buildDumbbellChart(rubricWos, rubricWs, rubricBaseline),
      statsByVariant
    );

    var nEvals = (aggCurrent.stats && aggCurrent.stats.overall_score) ? aggCurrent.stats.overall_score.n : runs.length;

    var html = '';
    html += '<div class="sec-heading" id="sec-quality-scores" data-section="quality-scores">';
    html += '<span class="sec-icon">' + NAV_ICONS["quality-scores"] + '</span>';
    html += '<h2>Quality Scores</h2>';
    if(pills) html += '<div class="variant-pill-row">' + pills + '</div>';
    html += '</div>';
    html += '<div class="card">';
    html += '<div class="bench-qs-charts">';
    html += '<div class="bench-qs-chart-wrap">' + radarHtml + '</div>';
    html += '<div class="bench-qs-chart-wrap">';
    html += dumbbellHtml;
    html += '</div>';
    html += '</div>';
    var subtitleParts = [
      nEvals + ' eval' + (nEvals === 1 ? '' : 's') + ' averaged',
      'whiskers show min/max per dimension'
    ];
    if(mode === "regression"){
      subtitleParts.push(
        '<em>Previous</em> scores are re-graded at this iteration\u2019s comparator run, so the same response may score differently than in its original iteration'
      );
    }
    html += '<div class="bench-qs-subtitle">' + subtitleParts.join(' \u00b7 ') + '.</div>';

    /* Bimodal callout on overall_score when spread > 4 for any visible variant. */
    var bimodalSlot = null, bimodalSpread = 0;
    ["current","previous","baseline"].forEach(function(slot){
      var s = statsByVariant[slot];
      if(!s || !s.overall_score) return;
      var span = s.overall_score.max - s.overall_score.min;
      if(span > 4 && span > bimodalSpread){
        bimodalSpread = span;
        bimodalSlot = slot;
      }
    });
    if(bimodalSlot){
      var s = statsByVariant[bimodalSlot].overall_score;
      html += '<div class="bench-qs-bimodal">\u26A0 Wide spread on overall_score \u2014 some evals at ' +
        s.min.toFixed(0) + '/10, others at ' + s.max.toFixed(0) + '/10 (' + bimodalSlot + ').</div>';
    }

    html += '</div>'; /* card */
    return html;
  };
})();

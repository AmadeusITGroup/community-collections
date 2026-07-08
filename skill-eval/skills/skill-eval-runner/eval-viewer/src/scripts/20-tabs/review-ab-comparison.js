/* Review-tab A/B Comparison panel — comparator verdict prose + radar + dumbbell
   charts. Returns the raw inner content (no outer wrapper); the caller is
   responsible for the .sec-heading + card chrome. */

function buildABComparisonContent(c, baselineRun){
  if(!c) return { verdict: "", body: "" };

  var assignment = c.assignment || {};
  /* Map A/B to variant-side rubrics:
       rubricWos = without_skill | previous_skill
       rubricWs  = current_skill */
  var rubricWos = null, rubricWs = null;
  if(c.rubric){
    ["A","B"].forEach(function(letter){
      var v = assignment[letter];
      if(!v) return;
      if(v === "current_skill") rubricWs = c.rubric[letter];
      else                      rubricWos = c.rubric[letter];
    });
    if(!rubricWos && !rubricWs){
      rubricWos = c.rubric.A;
      rubricWs  = c.rubric.B;
    }
  }

  /* In regression mode the 3rd polygon/dot comes from the baseline run's
     own comparison.json (where A=without_skill). */
  var rubricBaseline = null;
  if(getComparisonMode() === "regression" && baselineRun){
    rubricBaseline = rubricForVariant(baselineRun, "without_skill");
  }

  var verdict = "";
  if(c.reasoning){
    verdict = '<div class="review-ab-comparison-verdict">' +
      highlightVariants(c.reasoning, assignment) + '</div>';
  }

  var body = "";
  if(rubricWos || rubricWs || rubricBaseline){
    body += '<div class="rubric-charts">';
    body +=   '<div class="chart-panel">';
    body +=     '<div class="chart-title">Sub-dimensions</div>';
    body +=     '<div class="radar-wrap">' + buildRadarChart(rubricWos, rubricWs, rubricBaseline) + '</div>';
    body +=   '</div>';
    body +=   '<div class="chart-panel dumbbell-panel">';
    body +=     '<div class="chart-title">Summary scores</div>';
    body +=     buildDumbbellChart(rubricWos, rubricWs, rubricBaseline);
    body +=   '</div>';
    body += '</div>';

    var legendMode = getComparisonMode();
    body += '<div class="rubric-legend">';
    if(rubricBaseline){
      body += '<span title="Baseline (no skill)"><span class="dot baseline"></span> Baseline (no skill)</span>';
    }
    body += '<span title="' + variantLabelFullForSide("wos", legendMode) + '"><span class="dot wos"></span> ' + variantLabelFullForSide("wos", legendMode) + '</span>';
    body += '<span title="' + variantLabelFullForSide("ws",  legendMode) + '"><span class="dot ws"></span> '  + variantLabelFullForSide("ws",  legendMode) + '</span>';
    body += '</div>';
  }

  return { verdict: verdict, body: body };
}

/* Replace standalone variant names in comparator reasoning with tinted spans.
   Tight labels for display, full names in title= tooltips. */
function highlightVariants(text, assignment){
  var mode = getComparisonMode();
  function tag(which, full){
    return '<span class="variant-tag ' + which + '" title="' + full + '">' +
      variantLabelForSide(which, mode) + '</span>';
  }
  var s = esc(text);
  s = s.replace(/\bcurrent_skill\b/g,  tag("ws",  "Current skill"));
  s = s.replace(/\bprevious_skill\b/g, tag("wos", "Previous skill"));
  s = s.replace(/\bwithout_skill\b/g,  tag("wos", "Without skill"));
  /* Replace standalone A/B references with their assigned variant. */
  if(assignment && assignment.A && assignment.B){
    s = s.replace(/(?:^|\s|\()([AB])(?=\s|\)|,|\.|:|;|$)/g, function(m, letter){
      var mapped = assignment[letter];
      if(!mapped) return m;
      var which = variantCssClass(mapped);
      if(which === "baseline") which = "wos";
      var full = variantLabelFullForSide(which, mode);
      return m.replace(letter, '<span class="variant-tag ' + which + '" title="' + full + '">' + variantLabelForSide(which, mode) + '</span>');
    });
  }
  return s;
}

/* Return the A/B rubric block that matches `variant` based on the run's own
   comparison.assignment. Used to synthesize the 3rd (baseline) polygon for
   radar/dumbbell in regression mode. */
function rubricForVariant(run, variant){
  if(!run || !run.comparison || !run.comparison.rubric) return null;
  var assign = run.comparison.assignment || {};
  var r = run.comparison.rubric;
  if(assign.A === variant) return r.A || null;
  if(assign.B === variant) return r.B || null;
  if(variant === "current_skill") return r.B || null;
  return r.A || null;
}

/* Benchmark tab orchestration. Sections, in render order:
     1. Headline             (benchmark-headline.js)
     2. Cost Overhead        (benchmark-cost.js)
     3. Quality Scores       (benchmark-quality-scores.js)
     4. Contradictions       (benchmark-contradictions.js, conditional)
     5. Skill Regressions    (benchmark-contradictions.js, conditional)
     6. Skill Feedback       (benchmark-skill-feedback.js, conditional)
     7. Per-Eval Scorecard   (benchmark-scorecard.js)
     8. Insights             (benchmark-insights.js) */

function buildBenchmarkSidebar(src){
  var items = [];
  items.push({id:"headline",   label:"Headline", active:true});
  items.push({id:"cost",       label:"Cost Overhead"});
  items.push({id:"quality-scores", label:"Quality Scores"});

  if(src && src.contradictions && src.contradictions.length){
    items.push({id:"contradictions", label:"Contradictions"});
  }
  var sr = src && src.skill_regressions;
  if(sr && ((sr.vs_baseline || []).length || (sr.vs_previous || []).length)){
    items.push({id:"skill-regressions", label:"Skill Regressions"});
  }
  if(src && src.skill_feedback_rollup){
    items.push({id:"skill-feedback", label:"Skill Feedback"});
  }

  items.push({id:"per-eval", label:"Per-Eval"});
  items.push({id:"insights", label:"Insights"});

  items.forEach(function(it){ it.icon = NAV_ICONS[it.id] || ""; });

  var html = '<ul class="sidebar-nav">';
  items.forEach(function(it){
    html += '<li><a href="#sec-' + it.id + '"' + (it.active ? ' class="active"' : '') +
            '><span class="nav-icon">' + it.icon + '</span>' + it.label + '</a></li>';
  });
  html += '</ul>';
  $sidebar.innerHTML = html;
  bindSidebarLinks();
}

function renderBenchmarkPage(){
  var iterData = getIterationData(state.activeIteration);
  var bench = getBenchmarkData(state.activeIteration);
  var src = bench || iterData;
  buildBenchmarkSidebar(src);

  if(!src){
    $main.innerHTML = '<div class="card" style="text-align:center;padding:60px;color:var(--text-muted)">No benchmark data for iteration ' + state.activeIteration + '.</div>';
    return;
  }

  var EV = window.__EV;
  var html = "";
  html += EV.buildBenchmarkHeadlineCard(src);
  html += EV.buildBenchmarkCostCard(src);
  html += EV.buildBenchmarkQualityScoresCard(src);

  if((src.contradictions || []).length){
    html += EV.buildContradictionsCard(src.contradictions);
  }
  html += EV.buildSkillRegressionsCard(src.skill_regressions, getComparisonMode());
  html += EV.buildBenchmarkSkillFeedbackCard(src);
  html += EV.buildBenchmarkScorecard(src);

  /* Insights needs sortNotes-processed note list. */
  var srcForInsights = Object.assign({}, src, {
    notes: sortNotes(src.notes || (iterData ? iterData.notes : []) || [])
  });
  html += EV.buildBenchmarkInsightsCard(srcForInsights);

  $main.innerHTML = html;

  EV.bindBenchmarkScorecard($main);
  EV.bindBenchmarkSkillFeedback($main);
  EV.bindContradictionsRegressionsNav($main);
  EV.bindBenchmarkInsightsNav($main);
  bindChartTooltips();
}

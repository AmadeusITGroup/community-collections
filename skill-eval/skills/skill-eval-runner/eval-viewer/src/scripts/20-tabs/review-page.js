/* Review-tab body renderer (focus mode).

   Switching evals never re-fetches — runs are stashed in `state._reviewBuilt`
   after the initial render. The flow on each render call:

     1. Compute eval groups + order once per call.
     2. Mount the sticky header bar (review-header-bar.js).
     3. Resolve the initial active eval (localStorage → first).
     4. _renderActiveEval(id) renders just that eval's body, primes the
        scroll-spy, runs every bind helper, and updates the header. */

function _reviewStashBuilt(builtGroups, evalOrder, mode){
  state._reviewBuilt = {
    groups: builtGroups,
    order: evalOrder,
    mode: mode
  };
}

/* Convert buildEvalGroupsForReview(...).order (array of keys) into an
   array of {id, name, mainRun, group} objects sorted ascending by id. */
function _reviewBuildEvalOrder(builtGroups, builtOrder){
  return builtOrder.map(function(key){
    var g = builtGroups[key];
    return { id: g.id, name: g.name, mainRun: g.current || g.ws, group: g };
  });
}

/* Δ chip source. Regression mode uses per-eval pass_rate delta vs previous,
   computed from per_eval_comparisons[].per_expectation; baseline mode uses
   ws minus wos. */
function _reviewBuildDeltaMap(evalOrder, mode){
  var out = {};
  if(mode === "regression"){
    var bench = getBenchmarkData(state.activeIteration);
    var pecList = (bench && bench.per_eval_comparisons) || [];
    pecList.forEach(function(pec){
      if(pec.eval_id == null) return;
      var perExp = pec.per_expectation;
      if(!Array.isArray(perExp) || !perExp.length) return;
      var curPassed = 0, prevPassed = 0, curTotal = 0, prevTotal = 0;
      perExp.forEach(function(row){
        if(row.current_skill && typeof row.current_skill.passed === "boolean"){
          curTotal++;
          if(row.current_skill.passed) curPassed++;
        }
        if(row.previous_skill && typeof row.previous_skill.passed === "boolean"){
          prevTotal++;
          if(row.previous_skill.passed) prevPassed++;
        }
      });
      if(!curTotal || !prevTotal) return;
      out[pec.eval_id] = (curPassed / curTotal) - (prevPassed / prevTotal);
    });
  } else {
    evalOrder.forEach(function(ev){
      var g = ev.group;
      var wsSum  = g.ws  && g.ws.grading  && g.ws.grading.summary;
      var wosSum = g.wos && g.wos.grading && g.wos.grading.summary;
      if(!wsSum || !wosSum) return;
      if(wsSum.pass_rate == null || wosSum.pass_rate == null) return;
      out[ev.id] = wsSum.pass_rate - wosSum.pass_rate;
    });
  }
  return out;
}

function renderReviewBody(currentRuns, mode, baselineRuns, prevRuns){
  if(!currentRuns || !currentRuns.length){
    $main.innerHTML = '<div class="card" style="text-align:center;padding:60px;color:var(--text-muted)">No run data available for iteration ' + state.activeIteration + '.</div>';
    return;
  }
  var built = buildEvalGroupsForReview(currentRuns, mode, {
    baselineRuns: baselineRuns,
    prevRuns: prevRuns
  });
  var groups = built.groups;
  var evalOrder = _reviewBuildEvalOrder(groups, built.order);
  if(!evalOrder.length){
    $main.innerHTML = '<div class="card" style="text-align:center;padding:60px;color:var(--text-muted)">No evals to display.</div>';
    return;
  }
  _reviewStashBuilt(groups, evalOrder, mode);

  /* Mount the header bar inside main; the eval body slot follows. */
  var deltaByEval = _reviewBuildDeltaMap(evalOrder, mode);
  $main.innerHTML = '<div id="review-eval-body"></div>';
  buildReviewHeaderBar($main, evalOrder, deltaByEval, mode);

  _renderActiveEval(_reviewHeaderResolveInitial(evalOrder));
}

/* Render a single eval's body in #review-eval-body, prime scroll-spy, run
   binds, and refresh the header bar. */
function _renderActiveEval(evalId){
  if(evalId == null) return;
  var built = state._reviewBuilt;
  if(!built) return;
  var group = built.groups[evalId];
  if(!group){
    /* Resolve via order entry — the keyed lookup misses when groups uses
       eval_name as the key. */
    for(var i = 0; i < built.order.length; i++){
      if(built.order[i].id === evalId){ group = built.order[i].group; break; }
    }
  }
  if(!group) return;
  state.activeEvalId = evalId;

  var oqSides = resolveOutputQualitySides(group.comparison);
  var bodySlot = document.getElementById("review-eval-body");
  if(!bodySlot) return;
  bodySlot.innerHTML = buildEvalReviewBlock(group, built.mode, oqSides);

  bindOutputTabs();
  bindFeedbackAreas();
  bindChartTooltips();

  /* Wire the Notes-section Submit Feedback button. */
  var submitBtn = bodySlot.querySelector("#submit-feedback-btn");
  if(submitBtn){
    submitBtn.addEventListener("click", function(){
      submitFeedback();
      this.textContent = "Submitted!";
      var self = this;
      setTimeout(function(){ self.textContent = "Submit Feedback"; }, 2000);
    });
  }

  _bindReviewScrollSpy();
  updateReviewHeaderBar(evalId);

  window.scrollTo({top:0});
}

/* Used by Benchmark scorecard / contradictions / skill-feedback "jump to eval"
   affordances. */
function _navToReviewEval(evalId){
  if(evalId == null) return;
  switchPage("review");
  setTimeout(function(){ _renderActiveEval(parseInt(evalId, 10)); }, 50);
}

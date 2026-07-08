/* Review-tab entry — sets up the sidebar from any cached runs, kicks off
   the fetches required for the active iteration's mode, then dispatches to
   renderReviewBody once the data lands. Renders an inline error card on
   network failure (typical for static exports loaded over file://). */

function renderReviewPage(){
  var mode = getComparisonMode();
  var cfg = D.served_iteration_config || {};
  var baselineIter = cfg.baseline_iteration || 1;
  var iter = state.activeIteration;

  var needed = [iter];
  if(mode === "regression"){
    if(baselineIter !== iter) needed.push(baselineIter);
    if(iter - 1 >= 1 && iter - 1 !== baselineIter) needed.push(iter - 1);
  }

  /* Render sidebar from whatever current-iter runs are already embedded/
     cached, so the left rail doesn't pop in after the fetch. */
  buildReviewSidebar(getRunsData(iter) || []);

  $main.innerHTML = '<div class="card loading-card"><div class="spinner"></div>' +
    '<div>Loading iteration ' + iter + ' outputs…</div></div>';

  Promise.all(needed.map(fetchRunsData))
    .then(function(results){
      /* Re-check active iteration — user may have switched while loading. */
      if(state.activeIteration !== iter || state.activePage !== "review") return;
      var currentRuns  = results[0] || [];
      var baselineRuns = mode === "regression" ? (getRunsData(baselineIter) || []) : [];
      var prevRuns     = mode === "regression" && iter > 1 ? (getRunsData(iter - 1) || []) : [];
      buildReviewSidebar(currentRuns);
      renderReviewBody(currentRuns, mode, baselineRuns, prevRuns);
    })
    .catch(function(err){
      $main.innerHTML = '<div class="card" style="text-align:center;padding:60px;color:var(--text-muted)">' +
        '<div style="font-size:2rem;margin-bottom:12px;opacity:0.5">📄</div>' +
        '<p>Could not load outputs for iteration ' + iter + '.</p>' +
        '<p style="margin-top:8px;font-size:0.85rem;color:var(--text-light)">' +
        (window.location.protocol === "file:"
          ? "Static export: re-generate with --static and include --iteration " + iter + "."
          : esc(String((err && err.message) || err))) +
        '</p></div>';
    });
}

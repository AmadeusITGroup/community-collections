/* Build a mode-aware, side-aware eval grouping structure for the Review tab.

   - baseline mode:   groups built from currentRuns; .wos = without_skill
                      run, .ws = current_skill run.
   - regression mode: .baseline = iter-1's without_skill run (reference only);
                      .prev    = iter N-1's current_skill (= previous_skill);
                      .current = iter N's current_skill;
                      .wos / .ws aliased to .prev / .current so existing
                      downstream helpers keep working unchanged. */

function buildEvalGroupsForReview(currentRuns, mode, extras){
  extras = extras || {};
  var baselineRuns = extras.baselineRuns || [];
  var prevRuns = extras.prevRuns || [];

  function indexBy(runs, variant){
    var m = {};
    (runs || []).forEach(function(r){
      if(r.variant === variant || r.configuration === variant){
        var k = r.eval_id != null ? r.eval_id : r.eval_name;
        if(!m[k]) m[k] = r;
      }
    });
    return m;
  }
  var baselineByEval = indexBy(baselineRuns, "without_skill");
  var prevByEval     = indexBy(prevRuns, "current_skill");

  var groups = {};
  var order = [];
  currentRuns.forEach(function(r){
    var key = r.eval_id != null ? r.eval_id : r.eval_name;
    if(!groups[key]){
      groups[key] = {
        id: r.eval_id,
        name: r.eval_name,
        prompt: "",
        comparison: null,
        baseline: null,
        prev: null,
        current: null,
        wos: null,
        ws: null
      };
      order.push(key);
    }
    var g = groups[key];
    if(r.prompt && !g.prompt) g.prompt = r.prompt;
    if(r.comparison && !g.comparison) g.comparison = r.comparison;
    if(r.variant === "current_skill" || r.configuration === "current_skill"){
      if(mode === "regression") g.current = r;
      else                      g.ws      = r;
    }
    if(r.variant === "without_skill" || r.configuration === "without_skill"){
      if(mode !== "regression") g.wos = r;
    }
  });

  if(mode === "regression"){
    order.forEach(function(key){
      var g = groups[key];
      g.baseline = baselineByEval[key] || null;
      g.prev     = prevByEval[key]     || null;
      /* Alias prev/current → wos/ws so buildExpectationCompare,
         resolveOutputQualitySides, buildEvalReviewBlock, and
         buildComparisonSection keep working unchanged. */
      g.wos = g.prev;
      g.ws  = g.current;
    });
  }

  order.sort(function(a, b){
    var ga = groups[a], gb = groups[b];
    if(ga.id != null && gb.id != null) return ga.id - gb.id;
    return 0;
  });

  return { groups: groups, order: order };
}

/* Map comparison.output_quality A/B slots onto wos/ws sides via assignment. */
function resolveOutputQualitySides(c){
  if(!c || !c.output_quality) return null;
  var assignment = c.assignment || {};
  var oq = c.output_quality;
  var wos = null, ws = null;
  ["A","B"].forEach(function(letter){
    if(!oq[letter]) return;
    var mapped = assignment[letter];
    if(variantCssClass(mapped) === "ws") ws = oq[letter];
    else if(mapped) wos = oq[letter];
  });
  if(!wos && !ws){
    wos = oq.A || null;
    ws  = oq.B || null;
  }
  return { wos: wos, ws: ws };
}

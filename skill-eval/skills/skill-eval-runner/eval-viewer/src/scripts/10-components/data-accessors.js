/* Data accessors over the embedded payload (D) plus a network-aware fetcher
   for run outputs not yet inlined in the bundle. */

function getIterationsUpTo(iterNum){
  return (D.iterations || []).filter(function(it){ return it.iteration <= iterNum; });
}

function getIterationData(iterNum){
  return (D.iterations || []).find(function(it){ return it.iteration === iterNum; }) || null;
}

function getBenchmarkData(iterNum){
  if(D.iteration_benchmarks && D.iteration_benchmarks[String(iterNum)]){
    return D.iteration_benchmarks[String(iterNum)];
  }
  return null;
}

function getRunsData(iterNum){
  var k = String(iterNum);
  if(D.iteration_runs && D.iteration_runs[k]) return D.iteration_runs[k];
  if(state.runsCache[k]) return state.runsCache[k];
  return null;
}

/* Async accessor: returns a Promise resolving with runs for iterNum.
   Resolves instantly if embedded/cached; otherwise fetches via API.
   Dedups concurrent in-flight requests. Rejects on network failure
   (e.g. file:// static export without a reachable server). */
function fetchRunsData(iterNum){
  var k = String(iterNum);
  if(D.iteration_runs && D.iteration_runs[k]) return Promise.resolve(D.iteration_runs[k]);
  if(state.runsCache[k]) return Promise.resolve(state.runsCache[k]);
  if(state.runsInflight[k]) return state.runsInflight[k];
  var p = fetch("/api/iteration/" + iterNum + "/runs")
    .then(function(r){
      if(!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function(runs){
      state.runsCache[k] = runs;
      if(!D.iteration_runs) D.iteration_runs = {};
      D.iteration_runs[k] = runs;
      delete state.runsInflight[k];
      return runs;
    })
    .catch(function(err){
      delete state.runsInflight[k];
      throw err;
    });
  state.runsInflight[k] = p;
  return p;
}

/* Shared helpers exposed on `window.__EV` for cross-module reuse. Concatenated
   first so later src/ modules can depend on it. The format/render helpers
   used by the inline IIFE (esc, formatStatPct, renderMarkdown, …) are NOT
   here — they live alongside the boot code so the IIFE closure can call them
   directly without a trip through window.__EV. */

(function(){
  "use strict";

  var EV = window.__EV = window.__EV || {};
  EV.helpers = EV.helpers || {};

  EV.formatTokenCount = function formatTokenCount(value){
    if(value == null) return "N/A";
    var numeric = typeof value === "number" ? value : Number(value);
    if(!Number.isFinite(numeric)) return "N/A";
    var magnitude = Math.abs(numeric);
    var units = [
      { threshold: 1e12, divisor: 1e12, suffix: "T" },
      { threshold: 1e9, divisor: 1e9, suffix: "B" },
      { threshold: 1e6, divisor: 1e6, suffix: "M" },
      { threshold: 1e3, divisor: 1e3, suffix: "K" }
    ];
    for(var i = 0; i < units.length; i++){
      if(magnitude >= units[i].threshold){
        var scaled = numeric / units[i].divisor;
        var rounded = Number(scaled.toFixed(1));
        if(Math.abs(rounded) >= 1000 && i > 0){
          scaled = numeric / units[i - 1].divisor;
          return scaled.toFixed(1).replace(/\.0$/, "") + units[i - 1].suffix;
        }
        return scaled.toFixed(1).replace(/\.0$/, "") + units[i].suffix;
      }
    }
    var roundedInteger = Math.round(numeric);
    return Math.abs(roundedInteger) >= 1000
      ? (roundedInteger < 0 ? "-1K" : "1K")
      : roundedInteger.toLocaleString();
  };

  /* flipsBetween(byText, order, refSlot, curSlot)
     -----------------------------------------------------------
     Computes the gain/regression delta between two expectation slots.

       byText:  { [text]: { baseline?, wos?, ws? } } from buildExpectationCompare
       order:   [text, text, …] canonical ordering
       refSlot: "baseline" | "wos" | "ws"
       curSlot: "baseline" | "wos" | "ws"

     Returns { gains:[#N, …], regs:[#N, …] } where N is the 1-based index of
     the expectation in `order`. Rows missing in either slot are skipped. */
  EV.flipsBetween = function flipsBetween(byText, order, refSlot, curSlot){
    var gains = [], regs = [];
    for(var i = 0; i < order.length; i++){
      var t = order[i];
      var row = byText[t] || {};
      var ref = row[refSlot], cur = row[curSlot];
      if(!ref || !cur) continue;
      var idx = i + 1;
      if(!ref.passed && cur.passed) gains.push(idx);
      else if(ref.passed && !cur.passed) regs.push(idx);
    }
    return { gains: gains, regs: regs };
  };

  /* renderFlipsStrip(flipsByLabel) → innerHTML for a .section-card-flips row.

       flipsByLabel: [ { label, gains, regs }, … ]

     Multi-comparison rows (e.g. "Current vs Previous", "Current vs Baseline"
     in regression mode) each render one line. Empty sets still render the
     "(0 gains · 0 regressions)" tail so reviewers know the comparison ran. */
  /* Pull the average for `key` from a run_summary bucket
     ({ pass_rate: { mean, … }, time_seconds: { mean, … }, … }). Returns null
     when the bucket or the keyed entry is missing or non-numeric. */
  EV.metricMean = function metricMean(bucket, key){
    if(!bucket) return null;
    var entry = bucket[key];
    if(entry && typeof entry === "object" && "mean" in entry){
      if(entry.mean == null) return null;
      var n = Number(entry.mean);
      return Number.isNaN(n) ? null : n;
    }
    return null;
  };

  EV.evaluationCaseCount = function evaluationCaseCount(benchmark){
    if(!benchmark) return 0;
    var seen = Object.create(null);
    (Array.isArray(benchmark.runs) ? benchmark.runs : []).forEach(function(run){
      if(!run || run.eval_id == null) return;
      var id = String(run.eval_id);
      if(id) seen[id] = true;
    });
    var count = Object.keys(seen).length;
    if(count === 0 && Array.isArray(benchmark.per_eval)){
      count = benchmark.per_eval.length;
    }
    return count;
  };

  EV.iterationSessionUsageAverage = function iterationSessionUsageAverage(iterNum, field){
    var usageSummary = EV.iterationUsageSummary(iterNum);
    var sessionUsage = usageSummary && usageSummary.session;
    var sessionValue = sessionUsage && sessionUsage[field];
    var evalCount = usageSummary && usageSummary.eval_count;
    if(typeof sessionValue === "number" && Number.isFinite(sessionValue) &&
       Number.isInteger(evalCount) && evalCount > 0){
      return {
        value: sessionValue / evalCount,
        source: "final_usage",
        divisor: evalCount,
        iterationTotal: sessionValue,
        partial: false
      };
    }
    return null;
  };

  EV.sessionUsageAverageTitle = function sessionUsageAverageTitle(value){
    if(!value || value.source !== "final_usage" ||
       !Number.isInteger(value.divisor) || value.divisor <= 0){
      return "";
    }
    return "Display-only session average: " + formatNum(value.iterationTotal) +
      " total tokens divided equally across " + value.divisor +
      " eval cases; includes shared framework usage and is not measured per run.";
  };

  EV.iterationUsageSummary = function iterationUsageSummary(iterNum){
    var summaries = (typeof D !== "undefined" && D.iteration_usage_summaries)
      ? D.iteration_usage_summaries
      : null;
    var summary = summaries && summaries[String(iterNum)];
    if(!summary || summary.schema_version !== 1 || summary.source !== "copilot-cli"){
      return null;
    }
    return summary;
  };

  EV.runResultMean = function runResultMean(benchmark, configuration, field){
    var values = [];
    (benchmark && Array.isArray(benchmark.runs) ? benchmark.runs : []).forEach(function(run){
      if(!run || run.configuration !== configuration) return;
      var value = run.result && run.result[field];
      if(typeof value === "number" && Number.isFinite(value)){
        values.push(value);
      }
    });
    if(!values.length) return null;
    return values.reduce(function(sum, value){ return sum + value; }, 0) / values.length;
  };

  /* Strip provider prefixes (e.g. "claude-sonnet-4.5" → "sonnet-4.5") so a
     model badge can fit in tight UI without losing meaning. Idempotent for
     names already short. */
  EV.shortModel = function shortModel(name){
    if(!name) return "";
    return String(name).replace(/^claude-/i, "");
  };

  /* Derive the model used for `variant` (default "current_skill") in the
     given iteration's benchmark.json (D.iteration_benchmarks[iter]). Prefer
     run-attributed models, then fall back to session models with a source tag.
     Returns:
       • { label: "sonnet-4.5", mixed: false, models: ["sonnet-4.5"] } when one
       • { label: "Mixed", mixed: true,  models: [...] } when multiple
       • source: "run" or "session"
       • null when no models can be resolved. */
  EV.iterationModel = function iterationModel(iterNum, variant){
    variant = variant || "current_skill";
    var bm = (typeof D !== "undefined" && D.iteration_benchmarks) ? D.iteration_benchmarks[String(iterNum)] : null;
    var usageSummary = EV.iterationUsageSummary(iterNum);
    if(!bm && !usageSummary) return null;
    function distinctModels(values){
      var seen = Object.create(null);
      var models = [];
      values.forEach(function(value){
        if(typeof value !== "string" || !value) return;
        var model = EV.shortModel(value);
        if(!seen[model]){
          seen[model] = true;
          models.push(model);
        }
      });
      return models;
    }
    var runModels = [];
    (Array.isArray(bm && bm.runs) ? bm.runs : []).forEach(function(run){
      if(!run || run.configuration !== variant) return;
      var model = run.result && run.result.model;
      if(typeof model === "string") runModels.push(model);
    });
    var models = distinctModels(runModels);
    var source = "run";
    if(!models.length){
      var agentModels = [];
      (usageSummary && Array.isArray(usageSummary.eval_agents)
        ? usageSummary.eval_agents
        : []
      ).forEach(function(agent){
        if(!agent || agent.role !== "executor" || agent.variant !== variant) return;
        (Array.isArray(agent.models) ? agent.models : []).forEach(function(model){
          agentModels.push(model);
        });
      });
      models = distinctModels(agentModels);
      source = models.length ? "agent" : "session";
    }
    if(!models.length){
      var finalSessionModels = usageSummary && usageSummary.session &&
        usageSummary.session.models;
      models = distinctModels(Array.isArray(finalSessionModels) ? finalSessionModels : []);
    }
    if(!models.length){
      var sessionModels = bm && bm.run_summary && bm.run_summary.session_usage &&
        bm.run_summary.session_usage.models;
      models = distinctModels(Array.isArray(sessionModels) ? sessionModels : []);
    }
    if(!models.length) return null;
    return {
      label: models.length === 1 ? models[0] : "Mixed",
      mixed: models.length > 1,
      models: models,
      source: source
    };
  };

  /* Return all distinct models reported for an iteration, including models
     used by without_skill and session-level Copilot CLI work. */
  EV.iterationModels = function iterationModels(iterNum){
    var bm = (typeof D !== "undefined" && D.iteration_benchmarks)
      ? D.iteration_benchmarks[String(iterNum)]
      : null;
    var usageSummary = EV.iterationUsageSummary(iterNum);
    if(!bm && !usageSummary) return [];
    var seen = {};
    var models = [];
    function add(value){
      if(typeof value !== "string") return;
      value.split(",").forEach(function(name){
        var model = name.trim();
        if(model && !seen[model]){
          seen[model] = true;
          models.push(model);
        }
      });
    }
    var summaryModels = bm && bm.run_summary && bm.run_summary.models;
    if(Array.isArray(summaryModels)){
      summaryModels.forEach(add);
    }
    (bm && Array.isArray(bm.runs) ? bm.runs : []).forEach(function(run){
      add(run.result && run.result.model);
    });
    var sessionModels = bm && bm.run_summary && bm.run_summary.session_usage &&
      bm.run_summary.session_usage.models;
    if(Array.isArray(sessionModels)) sessionModels.forEach(add);
    var finalModels = usageSummary && usageSummary.session && usageSummary.session.models;
    if(Array.isArray(finalModels)) finalModels.forEach(add);
    (usageSummary && Array.isArray(usageSummary.eval_agents)
      ? usageSummary.eval_agents
      : []
    ).forEach(function(agent){
      (agent && Array.isArray(agent.models) ? agent.models : []).forEach(add);
    });
    (usageSummary && Array.isArray(usageSummary.other_agents)
      ? usageSummary.other_agents
      : []
    ).forEach(function(agent){
      (agent && Array.isArray(agent.models) ? agent.models : []).forEach(add);
    });
    return models.sort();
  };

  EV.renderFlipsStrip = function renderFlipsStrip(flipsByLabel){
    if(!flipsByLabel || !flipsByLabel.length) return "";
    var lines = flipsByLabel.map(function(row){
      var chips = "";
      row.gains.forEach(function(n){ chips += '<span class="flip-chip gain">#' + n + ' &#10007;&rarr;&#10003;</span> '; });
      row.regs .forEach(function(n){ chips += '<span class="flip-chip reg">#'  + n + ' &#10003;&rarr;&#10007;</span> '; });
      var tail = '<span class="sc-flips-tail">(' +
        row.gains.length + ' gain' + (row.gains.length === 1 ? '' : 's') +
        ' · ' +
        row.regs.length + ' regression' + (row.regs.length === 1 ? '' : 's') +
        ')</span>';
      var prefix = '<span class="sc-flips-prefix">' + row.label + ':</span>';
      return prefix + ' ' + chips + tail;
    });
    return '<div class="section-card-flips">' + lines.join('<br>') + '</div>';
  };

})();

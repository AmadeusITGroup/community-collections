"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const scriptsRoot =
  "skill-eval/skills/skill-eval-runner/eval-viewer/src/scripts/";

const runSummary = {
  current_skill: {
    pass_rate: { mean: 1, stddev: 0 },
    time_seconds: { mean: 10, stddev: 0 },
    tokens: { mean: null, stddev: null, min: null, max: null },
  },
  without_skill: {
    pass_rate: { mean: 0.5, stddev: 0 },
    time_seconds: { mean: 9, stddev: 0 },
    tokens: { mean: null, stddev: null, min: null, max: null },
  },
  models: ["gpt-4.1", "gpt-5.5", "gpt-session"],
  session_usage: {
    input_tokens: 100,
    input_cached_tokens: 80,
    input_cache_creation_tokens: 10,
    input_cache_write_tokens: 6,
    output_tokens: 25,
    output_reasoning_tokens: 8,
    total_tokens: 125,
    ai_credits: 1.25,
    premium_requests: 1,
    duration_ms: 1200,
    models: ["gpt-session"],
    source: "copilot-cli",
  },
  delta: { pass_rate: "+0.5", time_seconds: "+1.0", tokens: null },
};

const benchmark = {
  run_summary: runSummary,
  runs: [
    {
      eval_id: "eval-1",
      configuration: "current_skill",
      result: { model: "gpt-5.5" },
    },
    {
      eval_id: "eval-1",
      configuration: "without_skill",
      result: { model: "gpt-4.1" },
    },
  ],
};

const progression = {
  iteration: 1,
  comparison_mode: "baseline",
  run_summary: runSummary,
  per_eval: [{ eval_id: 1 }],
};

const context = {
  window: { __EV: {} },
  D: { iteration_benchmarks: { "1": benchmark }, iteration_usage_summaries: {} },
  NAV_ICONS: {
    overview: "",
    trend: "",
    heatmap: "",
    resources: "",
    cost: "",
    prompt: "",
    output: "",
    feedback: "",
    notes: "",
  },
  state: { activeIteration: 1, feedbackMap: {} },
  $main: { innerHTML: "" },
  $sidebar: { innerHTML: "", querySelectorAll: function(){ return []; } },
  getComparisonMode: function(){ return "baseline"; },
  getIterationsUpTo: function(){ return [progression]; },
  getBenchmarkData: function(iteration){
    return context.D.iteration_benchmarks[String(iteration)] || benchmark;
  },
  buildProgressionSidebar: function(){},
  bindSidebarLinks: function(){},
  buildHealthSignalsCard: function(){ return ""; },
  buildTrendChart: function(){ return ""; },
  bindChartTooltips: function(){},
  secHeading: function(_icon, title, id){
    return '<div id="' + id + '"><h2>' + title + "</h2></div>";
  },
  variantLabelTight: function(variant){
    return ({
      without_skill: "Baseline",
      previous_skill: "Previous",
      current_skill: "Current",
    })[variant] || variant;
  },
  variantLabelFull: function(variant){ return variant; },
  buildExpectationCompare: function(){ return ""; },
  formatNum: function(value){ return Number(value).toLocaleString("en-US"); },
  formatTime: function(value){ return Number(value).toFixed(1) + "s"; },
  formatStatPct: function(value){
    return value == null ? "N/A" : Math.round(value * 100) + "%";
  },
  formatDelta: function(value){ return value == null ? "N/A" : String(value); },
  esc: function(value){
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  },
};

context.window.__EV.buildProgressionHeatmap = function(){ return ""; };
context.window.__EV.buildProgressionSkillFeedbackTrend = function(){ return ""; };
context.window.__EV.bindProgressionHeatmap = function(){};

vm.createContext(context);
[
  "00-utils.js",
  "20-tabs/review-sidebar.js",
  "20-tabs/review-per-eval.js",
  "20-tabs/review-page.js",
  "20-tabs/benchmark-cost.js",
  "20-tabs/trend-chart.js",
  "20-tabs/progression.js",
  "20-tabs/progression-resources.js",
].forEach(function(relativePath){
  const filename = scriptsRoot + relativePath;
  vm.runInContext(fs.readFileSync(filename, "utf8"), context, { filename });
});

function testPerRunMetricsShowDetailedCountersAndModel(){
  const html = context.renderGenerationMetrics({
    metrics: {
      host_telemetry: {
        source: "notification",
        model: "gpt-5.5",
        input_tokens: 100,
        input_cached_tokens: 70,
        input_cache_creation_tokens: 5,
        input_cache_write_tokens: 2,
        output_tokens: 25,
        output_reasoning_tokens: 8,
        total_tokens: 125,
      },
    },
  });

  assert.match(html, /gpt-5\.5/);
  assert.match(html, /100<\/strong> input tokens/);
  assert.match(html, /70 cached/);
  assert.match(html, /5 cache creation/);
  assert.match(html, /2 cache write/);
  assert.match(html, /25<\/strong> output tokens/);
  assert.match(html, /8 reasoning/);
  assert.match(html, /125<\/strong> tokens/);
}

function testPerRunMetricsShowUnavailableTokensInsteadOfZero(){
  const html = context.renderGenerationMetrics({
    metrics: {
      host_telemetry: {
        source: "wall_clock",
        total_duration_seconds: 2,
      },
    },
  });

  assert.match(html, /&#128221; Token usage <strong>N\/A<\/strong>/);
  assert.doesNotMatch(html, /<strong>0<\/strong> tokens/);
  assert.doesNotMatch(html, /model.{0,12}N\/A/i);
  assert.doesNotMatch(html, /input.{0,12}N\/A/i);
}

function testReviewTokenCountersUseCompactValuesWithExactTooltips(){
  const totalTokens = 7222124;
  const inputTokens = 5100000;
  const outputTokens = 2122124;
  const generationHtml = context.renderGenerationMetrics({
    metrics: {
      host_telemetry: {
        total_tokens: totalTokens,
        input_tokens: inputTokens,
        input_cached_tokens: 3456789,
        output_tokens: outputTokens,
        output_reasoning_tokens: 1234567,
      },
    },
  }, true);
  const agentHtml = context.renderCostUsageAgent({
    role: "executor",
    models: ["gpt-compact"],
    total_tokens: totalTokens,
    input_tokens: inputTokens,
    input_cached_tokens: 3456789,
    output_tokens: outputTokens,
    output_reasoning_tokens: 1234567,
  });

  assert.match(generationHtml, /7\.2M<\/strong> tokens/);
  assert.match(generationHtml, /5\.1M<\/strong> input tokens/);
  assert.match(generationHtml, /3\.5M cached/);
  assert.match(generationHtml, /2\.1M<\/strong> output tokens/);
  assert.match(generationHtml, /1\.2M reasoning/);
  assert.match(generationHtml, /Exact token count: 7,222,124/);
  assert.match(agentHtml, /7\.2M tokens/);
  assert.match(agentHtml, /Input 5\.1M/);
  assert.match(agentHtml, /Output 2\.1M/);
  assert.match(agentHtml, /Exact token count: 7,222,124 tokens/);
}

function testBenchmarkCostUsesSessionAverageOnlyForFramework(){
  const html = context.window.__EV.buildBenchmarkCostCard(benchmark);

  assert.match(html, /Avg Tokens/);
  assert.match(html, /Average Executor Tokens \/ Eval/);
  assert.match(html, /Average Total Framework Tokens \/ Eval/);
  assert.match(html, /Partial legacy session snapshot/);
  assert.match(html, /Avg Input Tokens/);
  assert.match(html, /Avg Cached Input Tokens/);
  assert.match(html, /Avg Input Cache Creation Tokens/);
  assert.match(html, /Avg Input Cache Write Tokens/);
  assert.match(html, /Avg Output Tokens/);
  assert.match(html, /Avg Output Reasoning Tokens/);
  assert.doesNotMatch(
    html.match(/<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/)[0],
    /125/
  );
  assert.doesNotMatch(html, /Copilot CLI session usage/);
  assert.doesNotMatch(html, /0×|\+0/);
}

function testBenchmarkCostHidesOnlyEqualCacheWriteDetail(){
  const equalCacheBenchmark = JSON.parse(JSON.stringify(benchmark));
  equalCacheBenchmark.run_summary.session_usage.input_cache_write_tokens = 10;
  const equalHtml = context.window.__EV.buildBenchmarkCostCard(equalCacheBenchmark);

  assert.match(equalHtml, /Avg Input Cache Creation Tokens/);
  assert.doesNotMatch(equalHtml, /Avg Input Cache Write Tokens/);
  assert.equal(
    equalCacheBenchmark.run_summary.session_usage.input_cache_write_tokens,
    10
  );

  const writeOnlyBenchmark = JSON.parse(JSON.stringify(benchmark));
  delete writeOnlyBenchmark.run_summary.session_usage.input_cache_creation_tokens;
  writeOnlyBenchmark.run_summary.session_usage.input_cache_write_tokens = 10;
  const writeOnlyHtml = context.window.__EV.buildBenchmarkCostCard(writeOnlyBenchmark);

  assert.doesNotMatch(writeOnlyHtml, /Avg Input Cache Creation Tokens/);
  assert.match(writeOnlyHtml, /Avg Input Cache Write Tokens/);
}

function testBenchmarkCostPrefersRunAverageOverSessionFallback(){
  const benchmarkWithRunTokens = {
    run_summary: {
      current_skill: { tokens: { mean: 321 } },
      without_skill: { tokens: { mean: null } },
      session_usage: { total_tokens: 999, source: "copilot-cli" },
    },
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { tokens: 321 } },
    ],
  };

  const html = context.window.__EV.buildBenchmarkCostCard(benchmarkWithRunTokens);
  const avgTokenRow = html.match(/<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/)[0];

  assert.match(
    avgTokenRow,
    /<td>N\/A<\/td><td><span title="Exact value: 321 tokens\.">321<\/span>/
  );
  assert.doesNotMatch(avgTokenRow, /Session average/);
}

function testIterationModelPrefersVariantModelThenFallsBackToSessionModel(){
  const EV = context.window.__EV;

  assert.equal(typeof EV.iterationModels, "function");
  assert.equal(
    JSON.stringify(EV.iterationModels(1)),
    JSON.stringify(["gpt-4.1", "gpt-5.5", "gpt-session"])
  );
  assert.equal(
    JSON.stringify(EV.iterationModel(1, "current_skill").models),
    JSON.stringify(["gpt-5.5"])
  );
  assert.equal(EV.iterationModel(1, "current_skill").source, "run");

  context.D.iteration_benchmarks["3"] = {
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { model: null } },
    ],
    run_summary: {
      session_usage: { models: ["gpt-session"] },
    },
  };
  assert.deepEqual(
    JSON.parse(JSON.stringify(EV.iterationModel(3, "current_skill"))),
    {
      label: "gpt-session",
      mixed: false,
      models: ["gpt-session"],
      source: "session",
    }
  );
}

function testProgressionOmitsPartialLegacySessionAverageAndModelSideNote(){
  context.renderProgressionPage();

  assert.doesNotMatch(context.$main.innerHTML, /Session average/);
  assert.match(
    context.$main.innerHTML,
    /<div class="metric-label">Avg Tokens<\/div><div class="metric-value"[^>]*>N\/A<\/div>/
  );
  assert.doesNotMatch(context.$main.innerHTML, /Models this iteration/);
}

function testProgressionResourcesIgnorePartialLegacySessionAverage(){
  const resourceProgression = {
    iteration: 1,
    comparison_mode: "baseline",
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: 100 } },
      session_usage: runSummary.session_usage,
    },
  };
  const html = context.window.__EV.buildProgressionResourceUsage([resourceProgression]);

  assert.match(html, /Avg Tokens/);
  assert.doesNotMatch(html, /Session average|125|\+25/);
}

function testProgressionUsesFinalUsageSessionAverageInOverviewAndResources(){
  const iterationBenchmark = {
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
    run_summary: {
      current_skill: { tokens: { mean: null }, pass_rate: { mean: 0.75, stddev: 0 } },
      without_skill: { tokens: { mean: null }, pass_rate: { mean: 0.5, stddev: 0 } },
    },
  };
  const finalUsage = makeUsageSummary(500, [], []);
  finalUsage.eval_count = 4;
  context.D.iteration_benchmarks["9"] = iterationBenchmark;
  context.D.iteration_usage_summaries["9"] = finalUsage;
  const iterationProgression = {
    iteration: 9,
    comparison_mode: "baseline",
    run_summary: iterationBenchmark.run_summary,
    per_eval: [{ eval_id: 1 }, { eval_id: 2 }],
  };
  const originalStateIteration = context.state.activeIteration;
  const originalGetIterations = context.getIterationsUpTo;
  context.state.activeIteration = 9;
  context.getIterationsUpTo = function(){ return [iterationProgression]; };

  context.renderProgressionPage();
  const resourceHtml = context.window.__EV.buildProgressionResourceUsage([
    iterationProgression,
  ]);

  assert.match(context.$main.innerHTML, /session average/i);
  assert.match(context.$main.innerHTML, /4 eval cases/);
  assert.match(context.$main.innerHTML, />125<\/div>/);
  assert.match(resourceHtml, /session average/i);
  assert.match(resourceHtml, /4 eval cases/);
  assert.match(resourceHtml, />125<\/td>/);

  context.state.activeIteration = originalStateIteration;
  context.getIterationsUpTo = originalGetIterations;
}

function testProgressionViewsUseCompactSessionTokenCounts(){
  const iterationBenchmark = {
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
    run_summary: {
      current_skill: { tokens: { mean: null }, pass_rate: { mean: 0.75, stddev: 0 } },
      without_skill: { tokens: { mean: null }, pass_rate: { mean: 0.5, stddev: 0 } },
    },
  };
  const finalUsage = makeUsageSummary(7222124, [], []);
  finalUsage.eval_count = 1;
  context.D.iteration_benchmarks["14"] = iterationBenchmark;
  context.D.iteration_usage_summaries["14"] = finalUsage;
  const iterationProgression = {
    iteration: 14,
    comparison_mode: "baseline",
    run_summary: iterationBenchmark.run_summary,
    per_eval: [{ eval_id: 1 }],
  };
  const originalStateIteration = context.state.activeIteration;
  const originalGetIterations = context.getIterationsUpTo;
  context.state.activeIteration = 14;
  context.getIterationsUpTo = function(){ return [iterationProgression]; };

  context.renderProgressionPage();
  const resourceHtml = context.window.__EV.buildProgressionResourceUsage([
    iterationProgression,
  ]);

  assert.match(context.$main.innerHTML, />7\.2M<\/div>/);
  assert.match(resourceHtml, />7\.2M<\/td>/);
  assert.match(context.$main.innerHTML, /Exact displayed average: 7,222,124 tokens/);
  assert.match(resourceHtml, /Exact displayed average: 7,222,124 tokens/);

  context.state.activeIteration = originalStateIteration;
  context.getIterationsUpTo = originalGetIterations;
}

function testRegressionResourceTokensFallBackToPreviousIterationSession(){
  const previousUsage = makeUsageSummary(7222124, [], []);
  previousUsage.eval_count = 8;
  const currentUsage = makeUsageSummary(5882756, [], []);
  currentUsage.eval_count = 8;
  context.D.iteration_usage_summaries["5"] = previousUsage;
  context.D.iteration_usage_summaries["6"] = currentUsage;
  const previousSummary = {
    current_skill: {
      time_seconds: { mean: 51.5 },
      tokens: { mean: null },
      tool_calls: { mean: 10 },
      steps: { mean: 5 },
    },
    previous_skill: { tokens: { mean: null } },
  };
  const currentSummary = {
    current_skill: {
      time_seconds: { mean: 80 },
      tokens: { mean: null },
      tool_calls: { mean: 13 },
      steps: { mean: 8 },
    },
    previous_skill: { tokens: { mean: null } },
  };
  const iterations = [
    {
      iteration: 5,
      previous_iteration: 4,
      comparison_mode: "regression",
      run_summary: previousSummary,
    },
    {
      iteration: 6,
      previous_iteration: 5,
      comparison_mode: "regression",
      run_summary: currentSummary,
    },
  ];

  const html = context.window.__EV.buildProgressionResourceUsage(iterations);
  const tokenRow = html.match(/<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/)[0];

  assert.match(
    tokenRow,
    /<td class="group-boundary" title="Display-only session average:[^"]*Exact displayed average: 902,765\.5 tokens\.">902\.8K<\/td>/
  );
  assert.match(
    tokenRow,
    /<td title="Display-only session average:[^"]*Exact displayed average: 735,344\.5 tokens\.">735\.3K<\/td>/
  );
  assert.match(
    tokenRow,
    /<td class="cell-delta" title="One or both values use display-only session averages[^"]*Exact token difference: -167,421 tokens\."><span class="delta-chip pos">-167\.4K<\/span><\/td>/
  );
}

function testResourceSparklinesUseCurrentTokenFallbackInMetricOrder(){
  const previousUsage = makeUsageSummary(7222124, [], []);
  previousUsage.eval_count = 8;
  const currentUsage = makeUsageSummary(5882756, [], []);
  currentUsage.eval_count = 8;
  context.D.iteration_usage_summaries["5"] = previousUsage;
  context.D.iteration_usage_summaries["6"] = currentUsage;
  const iterations = [
    {
      iteration: 5,
      comparison_mode: "regression",
      run_summary: {
        current_skill: {
          time_seconds: { mean: 51.5 },
          tokens: { mean: null },
          tool_calls: { mean: 10 },
          steps: { mean: 5 },
        },
      },
    },
    {
      iteration: 6,
      comparison_mode: "regression",
      run_summary: {
        current_skill: {
          time_seconds: { mean: 80 },
          tokens: { mean: null },
          tool_calls: { mean: 13 },
          steps: { mean: 8 },
        },
      },
    },
  ];

  const html = context.window.__EV.buildProgressionResourceUsage(iterations);
  const labels = Array.from(
    html.matchAll(/class="spark-label">([^<]+)<\/div>/g),
    match => match[1]
  );

  assert.deepEqual(
    labels,
    [
      "Avg Time (current)",
      "Avg Tokens (current)",
      "Avg Tool Calls (current)",
      "Avg Agent Turns (current)",
    ]
  );
  assert.equal((html.match(/<svg width="320"/g) || []).length, 4);
  assert.match(
    html,
    /Avg Tokens \(current\)<\/div><div class="spark-value">735\.3K<\/div><svg/
  );
}

function testTrendShowsTheOnlyKnownSessionModel(){
  context.D.iteration_benchmarks["3"] = {
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { model: null } },
    ],
    run_summary: {
      current_skill: { pass_rate: { mean: 0.75 } },
      session_usage: { models: ["gpt-session"] },
    },
  };

  const html = context.buildTrendChart([{
    iteration: 3,
    run_summary: context.D.iteration_benchmarks["3"].run_summary,
  }]);

  assert.match(html, /font-style="italic"[^>]*>gpt-session<\/text>/);
}

function testHealthSignalsShowsSessionModelBadge(){
  context.D.iteration_benchmarks["3"] = {
    comparison_mode: "regression",
    contradictions: [],
    metadata: { skill_version: "1.1.0" },
    skill_regressions: { vs_baseline: [], vs_previous: [] },
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { model: null } },
    ],
    run_summary: {
      current_skill: { pass_rate: { mean: 0.75 } },
      session_usage: { models: ["gpt-session"] },
    },
  };

  const html = context.buildHealthSignalsCard([{
    iteration: 3,
    comparison_mode: "regression",
  }]);

  assert.match(html, /<th[^>]*>Model<\/th>/);
  assert.match(html, /class="iter-model-badge"[^>]*>gpt-session<\/span>/);
  assert.match(html, /session-level/i);
}

function testResourceUsageShowsSessionModelBadgeInsteadOfModelList(){
  context.D.iteration_benchmarks["3"] = {
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { model: null } },
    ],
    run_summary: {
      current_skill: { tokens: { mean: null } },
      session_usage: { models: ["gpt-session"] },
    },
  };

  const html = context.window.__EV.buildProgressionResourceUsage([{
    iteration: 3,
    comparison_mode: "regression",
    run_summary: context.D.iteration_benchmarks["3"].run_summary,
  }]);

  assert.match(html, /class="iter-model-badge"[^>]*>gpt-session<\/div>/);
  assert.match(html, /session-level/i);
  assert.doesNotMatch(html, /Models: gpt-session/);
}

function testCostOverheadKeepsPartialSessionOutOfExecutorDeltas(){
  const comparisonBenchmark = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: 100 } },
      previous_skill: { tokens: { mean: 200 } },
      session_usage: {
        input_tokens: 600,
        input_cached_tokens: 320,
        input_cache_creation_tokens: 80,
        input_cache_write_tokens: 60,
        output_tokens: 300,
        output_reasoning_tokens: 90,
        total_tokens: 900,
        source: "copilot-cli",
      },
    },
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill", "previous_skill"].map(function(configuration){
        return {
          eval_id: evalId,
          configuration: configuration,
          result: configuration === "without_skill"
            ? { input_tokens: 50 }
            : configuration === "previous_skill"
              ? { input_tokens: 100 }
              : {},
        };
      });
    }),
  };
  context.state.activeIteration = 3;
  context.D.served_iteration_config = {
    mode: "regression",
    baseline_iteration: 1,
  };
  context.D.iteration_benchmarks["1"] = {
    run_summary: { without_skill: { tokens: { mean: 100 } } },
    runs: [],
  };
  context.D.iteration_benchmarks["2"] = {
    run_summary: { current_skill: { tokens: { mean: 200 } } },
    runs: [],
  };
  context.D.iteration_benchmarks["3"] = comparisonBenchmark;
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "regression"; };
  const html = context.window.__EV.buildBenchmarkCostCard(comparisonBenchmark, 3);
  context.getComparisonMode = originalComparisonMode;

  const avgTokenRow = html.match(/<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/)[0];
  assert.match(
    avgTokenRow,
    /<td><span[^>]*>100<\/span><\/td><td><span[^>]*>200<\/span><\/td><td>N\/A<\/td>/
  );
  const frameworkIndex = html.indexOf("Average Total Framework Tokens / Eval");
  const frameworkHtml = html.slice(frameworkIndex);
  assert.match(frameworkHtml, /450/);
  assert.match(frameworkHtml, /Partial legacy session snapshot/);
  assert.doesNotMatch(frameworkHtml, />\+250<\/span>/);
}

function testCostOverheadOmitsTokenDetailRowsWhenNoDetailsAreAvailable(){
  const withoutDetails = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      session_usage: { total_tokens: 200, source: "copilot-cli" },
    },
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: {} },
      { eval_id: "eval-2", configuration: "current_skill", result: {} },
    ],
  };

  const html = context.window.__EV.buildBenchmarkCostCard(withoutDetails);

  assert.match(html, /Avg Tokens/);
  assert.match(html, /Whole-session tokens \(iteration total\)/);
  assert.doesNotMatch(html, /Avg Input Tokens|Avg Output Tokens/);
}

function testProgressionModelLabelsAreEscapedForTextAndAttributes(){
  const hostile = '<img src=x onerror="alert(1)">';
  context.D.iteration_benchmarks["2"] = {
    runs: [
      { configuration: "current_skill", result: { model: hostile } },
    ],
    run_summary: { models: [hostile] },
  };
  const html = context.window.__EV.buildProgressionResourceUsage([{
    iteration: 2,
    comparison_mode: "baseline",
    run_summary: {
      current_skill: { tokens: { mean: 1 } },
      without_skill: { tokens: { mean: 1 } },
    },
  }]);

  assert.equal(html.includes(hostile), false);
  assert.match(html, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
}

function makeUsageAgent(evalId, role, variant, totalTokens, model){
  const agent = {
    eval_id: evalId,
    role: role,
    models: [model],
    input_tokens: totalTokens,
    input_cached_tokens: Math.floor(totalTokens / 2),
    input_cache_write_tokens: 5,
    output_tokens: 0,
    output_reasoning_tokens: 0,
    total_tokens: totalTokens,
    total_api_duration_ms: 100,
  };
  if(variant) agent.variant = variant;
  return agent;
}

function makeUsageSummary(totalTokens, evalAgents, otherAgents){
  return {
    schema_version: 1,
    source: "copilot-cli",
    eval_count: 2,
    session: {
      models: ["gpt-session"],
      input_tokens: totalTokens,
      input_cached_tokens: Math.floor(totalTokens / 2),
      input_cache_write_tokens: 10,
      output_tokens: 0,
      output_reasoning_tokens: 0,
      total_tokens: totalTokens,
      total_api_duration_ms: 800,
    },
    eval_agents: evalAgents,
    other_agents: otherAgents || [],
  };
}

function testCostOverheadShowsExecutorEvalLinkedAndFrameworkGroups(){
  const usage = makeUsageSummary(800, [
    makeUsageAgent("eval-1", "executor", "current_skill", 100, "gpt-executor"),
    makeUsageAgent("eval-2", "executor", "current_skill", 200, "gpt-executor"),
    makeUsageAgent("eval-1", "grader", "current_skill", 20, "gpt-grader"),
    makeUsageAgent("eval-2", "grader", "current_skill", 20, "gpt-grader"),
    makeUsageAgent("eval-1", "comparator", null, 50, "gpt-comparator"),
    makeUsageAgent("eval-2", "comparator", null, 50, "gpt-comparator"),
  ], [
    { label: "Runner", models: ["gpt-runner"], total_tokens: 360 },
  ]);
  context.D.iteration_usage_summaries["4"] = usage;
  context.D.iteration_benchmarks["4"] = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
      previous_skill: { tokens: { mean: null } },
    },
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill", "previous_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "regression"; };
  const html = context.window.__EV.buildBenchmarkCostCard(
    context.D.iteration_benchmarks["4"],
    4
  );
  context.getComparisonMode = originalComparisonMode;

  assert.match(html, /Average Executor Tokens \/ Eval/);
  assert.match(html, /Average All Eval-linked Tokens \/ Eval/);
  assert.match(html, /Average Total Framework Tokens \/ Eval/);
  assert.match(html, /Avg Executor API Time \/ Eval/);
  assert.match(html, /150/);
  assert.match(html, /220/);
  assert.match(html, /400/);
  assert.doesNotMatch(html, /2\/2 evals/);
  assert.match(html, /Other framework agents/);
}

function testExecutorTokenComparisonsHidePartialCoverage(){
  const usage = makeUsageSummary(1000, [
    makeUsageAgent("eval-1", "executor", "current_skill", 200, "gpt-executor"),
  ]);
  context.D.iteration_usage_summaries["15"] = usage;
  const benchmarkForCost = {
    run_summary: {
      current_skill: {
        pass_rate: { mean: 0.75 },
        tokens: { mean: null },
      },
      without_skill: {
        pass_rate: { mean: 0.5 },
        tokens: { mean: 100 },
      },
    },
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
    notes: [
      { text: "Skill trades +25pp pass rate for ~2.0× token spend." },
    ],
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };
  const html = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 15);
  context.getComparisonMode = originalComparisonMode;

  const executorTokenRow = html.match(
    /<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/
  )[0];
  assert.match(executorTokenRow, /100/);
  assert.match(executorTokenRow, /200[\s\S]*?1\/2 evals/);
  assert.match(
    executorTokenRow,
    /<td class="cell-delta"[^>]*>N\/A<\/td><td[^>]*>N\/A<\/td>/
  );
  assert.doesNotMatch(executorTokenRow, /delta-chip|2\.00×/);
  assert.doesNotMatch(html, /bench-cost-narrative|Skill trades/);
}

function testCostOverheadCollapsesBreakdownsAndExplainsScopes(){
  const executorOne = makeUsageAgent(
    "eval-1", "executor", "current_skill", 1000, "gpt-executor"
  );
  const executorTwo = makeUsageAgent(
    "eval-2", "executor", "current_skill", 2000, "gpt-executor"
  );
  const graderOne = makeUsageAgent(
    "eval-1", "grader", "current_skill", 100, "gpt-grader"
  );
  const graderTwo = makeUsageAgent(
    "eval-2", "grader", "current_skill", 200, "gpt-grader"
  );
  [executorOne, executorTwo, graderOne, graderTwo].forEach(function(agent){
    agent.input_cache_creation_tokens = 25;
  });
  const usage = makeUsageSummary(10000, [
    executorOne, executorTwo, graderOne, graderTwo,
  ]);
  usage.session.input_cache_creation_tokens = 400;
  context.D.iteration_usage_summaries["8"] = usage;
  const benchmarkForCost = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
    },
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };
  const html = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 8);
  context.getComparisonMode = originalComparisonMode;

  const breakdowns = Array.from(html.matchAll(
    /<details class="bench-cost-breakdown">([\s\S]*?)<\/details>/g
  ));
  assert.equal(breakdowns.length, 3);
  assert.doesNotMatch(html.replace(
    /<details class="bench-cost-breakdown">[\s\S]*?<\/details>/g,
    ""
  ), /class="bench-cost-token-detail"/);
  assert.doesNotMatch(html, /<details[^>]*\sopen(?:\s|>)/i);
  assert.match(html, /Executor-role usage only/i);
  assert.match(html, /All eval-linked agents: executor, grader, comparator and recovery/i);
  assert.match(
    html,
    /Whole Copilot CLI session totals divided by the distinct eval count for each iteration/i
  );
  assert.match(breakdowns[0][1], /&#8595; Avg Input Tokens/);
  assert.match(breakdowns[0][1], /&#128279; Avg Cached Input Tokens/);
  assert.match(breakdowns[0][1], /&#128203; Avg Input Cache Creation Tokens/);
  assert.match(breakdowns[0][1], /&#128221; Avg Input Cache Write Tokens/);
  assert.match(breakdowns[0][1], /&#8593; Avg Output Tokens/);
  assert.match(breakdowns[0][1], /&#129504; Avg Output Reasoning Tokens/);
  assert.match(breakdowns[0][1], /&#9202; Avg Executor API Time \/ Eval/);
}

function testSessionAveragesShowTheirDivisorWithoutMeasuredCoverage(){
  const usage = makeUsageSummary(800, [], []);
  usage.eval_count = 4;
  context.D.iteration_usage_summaries["4"] = usage;
  const benchmark = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
    },
    runs: ["eval-1", "eval-2"].map(function(evalId){
      return { eval_id: evalId, configuration: "current_skill", result: {} };
    }),
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };
  const html = context.window.__EV.buildBenchmarkCostCard(benchmark, 4);
  context.getComparisonMode = originalComparisonMode;

  const frameworkHtml = html.slice(
    html.indexOf("Average Total Framework Tokens / Eval")
  );
  const averageRow = frameworkHtml.match(
    /<tr><td>Avg Tokens<\/td>[\s\S]*?<\/tr>/
  )[0];
  const totalRow = frameworkHtml.match(
    /<tr class="bench-cost-token-detail"><td>&#128202; Whole-session tokens \(iteration total\)<\/td>[\s\S]*?<\/tr>/
  )[0];

  assert.match(averageRow, /200/);
  assert.match(averageRow, /Display-only Copilot CLI session average/);
  assert.match(averageRow, /4 eval cases/);
  assert.match(averageRow, /not measured per run/i);
  assert.doesNotMatch(averageRow, /session total \/ 4 eval cases|4\/4 evals|measured in/);
  assert.match(totalRow, /800/);
  assert.doesNotMatch(totalRow, /4\/4 evals/);
}

function testCostOverheadUsesCompactTokensWithExactTooltipValues(){
  const usage = makeUsageSummary(7222124, [], []);
  usage.eval_count = 1;
  context.D.iteration_usage_summaries["10"] = usage;
  const benchmarkForCost = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
    },
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: {} },
    ],
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };
  const html = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 10);
  context.getComparisonMode = originalComparisonMode;

  assert.match(html, />7\.2M(?:\s|<)/);
  assert.match(html, /7,222,124 tokens divided equally across 1 eval cases/);

  const rolloverUsage = makeUsageSummary(999950, [], []);
  rolloverUsage.eval_count = 1;
  context.D.iteration_usage_summaries["13"] = rolloverUsage;
  const rolloverHtml = context.window.__EV.buildBenchmarkCostCard(
    benchmarkForCost,
    13
  );
  assert.match(rolloverHtml, />1M(?:\s|<)/);
  assert.doesNotMatch(rolloverHtml, />1000K(?:\s|<)/);
}

function testCostOverheadShowsOnlyIncompleteCoverage(){
  const fullUsage = makeUsageSummary(2000, [
    makeUsageAgent("eval-1", "executor", "current_skill", 1000, "gpt-e"),
    makeUsageAgent("eval-2", "executor", "current_skill", 1000, "gpt-e"),
  ]);
  const partialUsage = makeUsageSummary(2000, [
    makeUsageAgent("eval-1", "executor", "current_skill", 1000, "gpt-e"),
  ]);
  const benchmarkForCost = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
    },
    runs: ["eval-1", "eval-2"].map(function(evalId){
      return { eval_id: evalId, configuration: "current_skill", result: {} };
    }),
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };

  context.D.iteration_usage_summaries["11"] = fullUsage;
  const fullHtml = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 11);
  context.D.iteration_usage_summaries["12"] = partialUsage;
  const partialHtml = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 12);

  context.getComparisonMode = originalComparisonMode;

  assert.doesNotMatch(fullHtml, /2\/2 evals|session total \/ 2 eval cases/);
  assert.match(partialHtml, /1\/2 evals/);
  assert.doesNotMatch(partialHtml, /2\/2 evals|session total \/ 2 eval cases/);
}

function testPartialPreviousSessionFallbackIsFrameworkOnly(){
  const usage = makeUsageSummary(800, [
    makeUsageAgent("eval-1", "executor", "current_skill", 100, "gpt-executor"),
    makeUsageAgent("eval-2", "executor", "current_skill", 200, "gpt-executor"),
  ]);
  context.D.iteration_usage_summaries["4"] = usage;
  context.D.iteration_benchmarks["3"] = {
    runs: ["eval-1", "eval-2"].map(function(evalId){
      return { eval_id: evalId, configuration: "current_skill", result: {} };
    }),
    run_summary: {
      current_skill: { tokens: { mean: null } },
      session_usage: {
        input_tokens: 380,
        input_cached_tokens: 300,
        output_tokens: 20,
        total_tokens: 400,
        models: ["gpt-old"],
        source: "copilot-cli",
      },
    },
  };
  const currentBenchmark = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
      previous_skill: { tokens: { mean: null } },
    },
    runs: ["eval-1", "eval-2"].flatMap(function(evalId){
      return ["current_skill", "without_skill", "previous_skill"].map(function(configuration){
        return { eval_id: evalId, configuration: configuration, result: {} };
      });
    }),
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "regression"; };
  const html = context.window.__EV.buildBenchmarkCostCard(currentBenchmark, 4);
  context.getComparisonMode = originalComparisonMode;

  assert.match(html, /partial legacy session snapshot/i);
  assert.match(html, /Average Executor Tokens \/ Eval/);
  assert.match(html, /Average Total Framework Tokens \/ Eval/);
  assert.doesNotMatch(html, />\+200(?:<\/span>)?/);
}

function testOtherFrameworkAgentDetailsAreCollapsed(){
  const usage = makeUsageSummary(800, [], [
    {
      label: "Runner",
      models: ["gpt-runner"],
      input_tokens: 80,
      input_cached_tokens: 60,
      input_cache_write_tokens: 10,
      output_tokens: 20,
      output_reasoning_tokens: 5,
      total_tokens: 100,
      total_api_duration_ms: 3500,
    },
  ]);
  context.D.iteration_usage_summaries["4"] = usage;
  context.D.iteration_benchmarks["4"] = { run_summary: {}, runs: [] };

  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "baseline"; };
  const html = context.window.__EV.buildBenchmarkCostCard(
    context.D.iteration_benchmarks["4"],
    4
  );
  context.getComparisonMode = originalComparisonMode;

  assert.match(html, /<details class="bench-cost-framework-agents-details">/);
  assert.match(html, /<summary>Other framework agents/);
  assert.doesNotMatch(html, /<details[^>]*open/);
  assert.match(html, /Unlinked support-agent totals by iteration/);
  assert.match(html, /included in whole-session totals above/);
  assert.match(
    html,
    /<th>Agent<\/th><th>Baseline<\/th><th>Skill<\/th><th title="Current vs Baseline">Δ/
  );
  assert.match(
    html,
    /<td>Runner<\/td><td>N\/A<\/td><td title="Exact value: 100 tokens\.">100<\/td><td class="cell-delta">N\/A<\/td><td>N\/A<\/td>/
  );
}

function testOtherFrameworkAgentsShowAlignedIterationTotals(){
  context.D.served_iteration_config = {
    mode: "regression",
    baseline_iteration: 1,
  };
  context.D.iteration_usage_summaries["1"] = makeUsageSummary(100, [], [
    { label: "Runner", models: ["gpt-runner"], total_tokens: 10 },
  ]);
  context.D.iteration_usage_summaries["4"] = makeUsageSummary(200, [], [
    { label: "Runner", models: ["gpt-runner"], total_tokens: 20 },
  ]);
  context.D.iteration_usage_summaries["5"] = makeUsageSummary(300, [], [
    { label: "Runner", models: ["gpt-runner"], total_tokens: 7222124 },
  ]);
  const benchmarkForCost = {
    run_summary: {
      current_skill: { tokens: { mean: null } },
      without_skill: { tokens: { mean: null } },
      previous_skill: { tokens: { mean: null } },
    },
    runs: [],
  };
  const originalComparisonMode = context.getComparisonMode;
  context.getComparisonMode = function(){ return "regression"; };
  const html = context.window.__EV.buildBenchmarkCostCard(benchmarkForCost, 5);
  context.getComparisonMode = originalComparisonMode;

  const agentsTable = html.match(
    /<table class="bench-cost-agents-table"[^>]*>([\s\S]*?)<\/table>/
  );
  assert.ok(agentsTable);
  assert.match(html, /unlinked support-agent totals/i);
  assert.match(
    agentsTable[1],
    /<th>Agent<\/th><th>Baseline<\/th><th>Previous<\/th><th>Current<\/th><th[^>]*>Δ <span[^>]*>vs Previous<\/span><\/th><th[^>]*>Ratio <span[^>]*>vs Baseline<\/span><\/th>/
  );
  assert.match(
    agentsTable[1],
    /<td>Runner<\/td><td[^>]*>10<\/td><td[^>]*>20<\/td><td[^>]*>7\.2M<\/td><td[^>]*><span[^>]*>\+7\.2M<\/span><\/td><td[^>]*>722212\.40×<\/td>/
  );
}

function testOtherFrameworkAgentDetailsRenderWithoutSessionTotals(){
  context.D.iteration_usage_summaries["4"] = {
    schema_version: 1,
    source: "copilot-cli",
    eval_count: 1,
    session: { models: ["gpt-session"] },
    eval_agents: [],
    other_agents: [
      { label: "Runner", models: ["gpt-runner"], total_tokens: 50 },
    ],
  };
  context.D.iteration_benchmarks["4"] = { run_summary: {}, runs: [] };

  const html = context.window.__EV.buildBenchmarkCostCard(
    context.D.iteration_benchmarks["4"],
    4
  );

  assert.match(html, /Other framework agents/);
  assert.match(html, /<td>Runner<\/td>/);
  assert.match(html, /Exact value: 50 tokens/);
}

function testVariantCardsExcludeComparisonAgents(){
  const usage = makeUsageSummary(200, [
    makeUsageAgent("eval-1", "executor", "current_skill", 100, "gpt-executor"),
    makeUsageAgent("eval-1", "grader", "current_skill", 20, "gpt-grader"),
    makeUsageAgent("eval-1", "comparator", null, 80, "gpt-comparator"),
  ]);
  const group = {
    id: 1,
    baseline: null,
    prev: null,
    current: { outputs: [], metrics: {} },
    wos: null,
    ws: null,
  };
  const reviewContext = {
    summaries: { "4": usage },
    sources: {
      baseline: { iteration: 1, configuration: "without_skill" },
      previous: { iteration: 3, configuration: "current_skill" },
      current: { iteration: 4, configuration: "current_skill" },
    },
  };

  assert.equal(typeof context.renderReviewCostSection, "function");
  const html = context.renderReviewCostSection(group, "regression", reviewContext);

  assert.match(html, /Executor/);
  assert.match(html, /Grader/);
  assert.doesNotMatch(html, /Comparator|gpt-comparator/);
}

function testReviewSidebarLinksCostSection(){
  context.buildReviewSidebar();

  assert.match(context.$sidebar.innerHTML, /href="#sec-cost"/);
  assert.match(context.$sidebar.innerHTML, />Cost</);
}

function testReviewCardsUseBaselineAndPreviousIterationSummaries(){
  const usageByIteration = {
    "1": makeUsageSummary(10, [
      makeUsageAgent("eval-1", "executor", "without_skill", 10, "gpt-baseline"),
    ]),
    "3": makeUsageSummary(20, [
      makeUsageAgent("eval-1", "executor", "current_skill", 20, "gpt-previous"),
    ]),
    "4": makeUsageSummary(30, [
      makeUsageAgent("eval-1", "executor", "current_skill", 30, "gpt-current"),
    ]),
  };
  const reviewContext = {
    summaries: usageByIteration,
    sources: {
      baseline: { iteration: 1, configuration: "without_skill" },
      previous: { iteration: 3, configuration: "current_skill" },
      current: { iteration: 4, configuration: "current_skill" },
    },
  };
  const group = {
    id: 1,
    prompt: "",
    baseline: { outputs: [] },
    prev: { outputs: [] },
    current: { outputs: [] },
    wos: null,
    ws: null,
  };

  assert.equal(typeof context.renderReviewCostSection, "function");
  const html = context.renderReviewCostSection(group, "regression", reviewContext);

  assert.match(html, /Baseline/);
  assert.match(html, /Previous/);
  assert.match(html, /Current/);
  assert.match(html, /10 tokens/);
  assert.match(html, /20 tokens/);
  assert.match(html, /30 tokens/);
}

function testReviewUsageContextMapsVariantSourceIterations(){
  context.state.activeIteration = 4;
  context.D.served_iteration_config = {
    mode: "regression",
    baseline_iteration: 1,
  };
  context.D.iteration_usage_summaries["1"] = makeUsageSummary(10, [], []);
  context.D.iteration_usage_summaries["3"] = makeUsageSummary(20, [], []);
  context.D.iteration_usage_summaries["4"] = makeUsageSummary(30, [], []);

  const usageContext = context._reviewUsageContext("regression");

  assert.deepEqual(
    JSON.parse(JSON.stringify(usageContext.sources)),
    {
      baseline: { iteration: 1, configuration: "without_skill" },
      previous: { iteration: 3, configuration: "current_skill" },
      current: { iteration: 4, configuration: "current_skill" },
    }
  );
  assert.equal(usageContext.summaries, context.D.iteration_usage_summaries);
}

function testEvalReviewBlockIncludesVariantCostSection(){
  context.state.activeIteration = 4;
  context.D.served_iteration_config = {
    mode: "regression",
    baseline_iteration: 1,
  };
  context.D.iteration_usage_summaries["4"] = makeUsageSummary(100, [
    makeUsageAgent("eval-1", "executor", "current_skill", 100, "gpt-executor"),
  ]);
  const group = {
    id: 1,
    prompt: "",
    comparison: null,
    baseline: null,
    prev: null,
    current: { outputs: [], metrics: {} },
    wos: null,
    ws: null,
  };

  const html = context.buildEvalReviewBlock(
    group,
    "regression",
    null,
    context._reviewUsageContext("regression")
  );

  assert.match(html, /id="sec-cost"/);
  assert.match(html, /Executor/);
  assert.match(html, /100 tokens/);
}

function testOutputCardsDoNotShowTelemetry(){
  const run = {
    outputs: [],
    metrics: {
      host_telemetry: {
        model: "gpt-output",
        total_duration_seconds: 4,
        total_tokens: 100,
        total_tool_calls: 2,
        turn_count: 3,
      },
      self_report: { total_steps: 5 },
    },
  };

  const html = context.renderOutputSection({ wos: run, ws: run }, "baseline");

  assert.doesNotMatch(html, /\b(?:tokens?|tool calls|LLM turns|steps)\b/i);
  assert.doesNotMatch(html, /gpt-output|4\.0s/);
}

function testUnavailableRunMetricsAreNotZero(){
  const group = {
    id: 1,
    baseline: null,
    prev: null,
    current: {
      outputs: [],
      metrics: { host_telemetry: { source: "wall_clock" } },
    },
    wos: null,
    ws: null,
  };
  const reviewContext = {
    summaries: {},
    sources: {
      baseline: { iteration: 1, configuration: "without_skill" },
      previous: { iteration: 3, configuration: "current_skill" },
      current: { iteration: 4, configuration: "current_skill" },
    },
  };

  assert.equal(typeof context.renderReviewCostSection, "function");
  const html = context.renderReviewCostSection(group, "regression", reviewContext);

  assert.match(html, /N\/A/);
  assert.doesNotMatch(html, /<strong>0<\/strong> tokens|0 tool calls|0 agent turns/);
}

function testCostCardDoesNotDuplicateRunMetrics(){
  const group = {
    id: 1,
    baseline: null,
    prev: null,
    current: {
      outputs: [],
      metrics: {
        host_telemetry: {
          source: "notification",
          model: "gpt-reported",
          total_duration_seconds: 3,
          total_tokens: 15,
          input_tokens: 10,
          input_cached_tokens: 5,
          output_tokens: 5,
          total_tool_calls: 2,
        },
        self_report: { total_steps: 4, total_tool_calls: 2 },
      },
    },
    wos: null,
    ws: null,
  };
  const reviewContext = {
    summaries: {},
    sources: {
      baseline: { iteration: 1, configuration: "without_skill" },
      previous: { iteration: 3, configuration: "current_skill" },
      current: { iteration: 4, configuration: "current_skill" },
    },
  };
  const html = context.renderReviewCostSection(group, "regression", reviewContext);

  assert.equal((html.match(/gpt-reported/g) || []).length, 1);
  assert.equal((html.match(/3\.0s/g) || []).length, 1);
}

function testFinalUsageModelsAppearInExistingModelLocations(){
  context.D.iteration_benchmarks["7"] = {
    runs: [
      { eval_id: "eval-1", configuration: "current_skill", result: { model: null } },
    ],
    run_summary: {
      current_skill: { pass_rate: { mean: 0.75 } },
      session_usage: null,
    },
  };
  context.D.iteration_usage_summaries["7"] = makeUsageSummary(100, [
    makeUsageAgent("eval-1", "executor", "current_skill", 100, "gpt-final-usage"),
  ]);
  context.D.iteration_usage_summaries["7"].session.models = ["gpt-session-final"];
  const model = context.window.__EV.iterationModel(7, "current_skill");

  assert.deepEqual(
    JSON.parse(JSON.stringify(model)),
    {
      label: "gpt-final-usage",
      mixed: false,
      models: ["gpt-final-usage"],
      source: "agent",
    }
  );

  const trend = context.buildTrendChart([{
    iteration: 7,
    run_summary: context.D.iteration_benchmarks["7"].run_summary,
  }]);
  assert.match(trend, /gpt-final-usage/);

  const health = context.buildHealthSignalsCard([{
    iteration: 7,
    comparison_mode: "baseline",
  }]);
  assert.match(health, /class="iter-model-badge"[^>]*>gpt-final-usage<\/span>/);

  const resources = context.window.__EV.buildProgressionResourceUsage([{
    iteration: 7,
    comparison_mode: "baseline",
    run_summary: context.D.iteration_benchmarks["7"].run_summary,
  }]);
  assert.match(resources, /class="iter-model-badge"[^>]*>gpt-final-usage<\/div>/);
}

function testSharedTokenFormatterUsesCompactSuffixes(){
  const formatTokenCount = context.window.__EV.formatTokenCount;
  assert.equal(typeof formatTokenCount, "function");
  assert.equal(formatTokenCount(999), "999");
  assert.equal(formatTokenCount(1234), "1.2K");
  assert.equal(formatTokenCount(7222124), "7.2M");
  assert.equal(formatTokenCount(999950), "1M");
  assert.equal(formatTokenCount(-1234), "-1.2K");
  assert.equal(formatTokenCount(null), "N/A");
  assert.equal(context.formatNum(7222124), "7,222,124");
}

testPerRunMetricsShowDetailedCountersAndModel();
testPerRunMetricsShowUnavailableTokensInsteadOfZero();
testReviewTokenCountersUseCompactValuesWithExactTooltips();
testBenchmarkCostUsesSessionAverageOnlyForFramework();
testBenchmarkCostHidesOnlyEqualCacheWriteDetail();
testBenchmarkCostPrefersRunAverageOverSessionFallback();
testIterationModelPrefersVariantModelThenFallsBackToSessionModel();
testProgressionOmitsPartialLegacySessionAverageAndModelSideNote();
testProgressionResourcesIgnorePartialLegacySessionAverage();
testProgressionUsesFinalUsageSessionAverageInOverviewAndResources();
testProgressionViewsUseCompactSessionTokenCounts();
testResourceSparklinesUseCurrentTokenFallbackInMetricOrder();
testRegressionResourceTokensFallBackToPreviousIterationSession();
testTrendShowsTheOnlyKnownSessionModel();
testHealthSignalsShowsSessionModelBadge();
testResourceUsageShowsSessionModelBadgeInsteadOfModelList();
testCostOverheadKeepsPartialSessionOutOfExecutorDeltas();
testCostOverheadOmitsTokenDetailRowsWhenNoDetailsAreAvailable();
testProgressionModelLabelsAreEscapedForTextAndAttributes();
testFinalUsageModelsAppearInExistingModelLocations();
testCostOverheadShowsExecutorEvalLinkedAndFrameworkGroups();
testExecutorTokenComparisonsHidePartialCoverage();
testCostOverheadCollapsesBreakdownsAndExplainsScopes();
testCostOverheadUsesCompactTokensWithExactTooltipValues();
testCostOverheadShowsOnlyIncompleteCoverage();
testSessionAveragesShowTheirDivisorWithoutMeasuredCoverage();
testSharedTokenFormatterUsesCompactSuffixes();
testPartialPreviousSessionFallbackIsFrameworkOnly();
testOtherFrameworkAgentDetailsAreCollapsed();
testOtherFrameworkAgentsShowAlignedIterationTotals();
testOtherFrameworkAgentDetailsRenderWithoutSessionTotals();
testVariantCardsExcludeComparisonAgents();
testReviewSidebarLinksCostSection();
testReviewCardsUseBaselineAndPreviousIterationSummaries();
testReviewUsageContextMapsVariantSourceIterations();
testEvalReviewBlockIncludesVariantCostSection();
testOutputCardsDoNotShowTelemetry();
testUnavailableRunMetricsAreNotZero();
testCostCardDoesNotDuplicateRunMetrics();

console.log("PASS: eval-viewer Copilot telemetry rendering");

/* Benchmark Cost Overhead card — separate panel for "cost, not benefit"
   metrics so a regression on tokens/time isn't conflated with a pass-rate
   regression.
     Metric | Baseline | (Previous) | Skill | Δ | Ratio
   Δ uses amber (cost overhead is an expected tradeoff, not failure);
   Ratio ≥ 2× gets a ⚠ suffix. Tool Calls / Steps rows render only when
   rs.current_skill exposes them. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  var metricMean = EV.metricMean;

  function fmtDecimal(v, digits){
    if(v == null) return "N/A";
    return Number(v).toFixed(digits == null ? 1 : digits);
  }
  function fmtNullableDecimal(v){
    return v == null ? null : fmtDecimal(v, 1);
  }
  function fmtToken(value){
    return value == null ? "N/A" : EV.formatTokenCount(value);
  }

  function exactTokenTitle(value, field){
    if(field === "total_api_duration_ms" || value == null) return "";
    return "Exact value: " + formatNum(value) + " tokens.";
  }

  function withExactTokenTitle(title, value, field){
    var exactTitle = exactTokenTitle(value, field);
    if(!exactTitle) return title;
    return title ? title + " " + exactTitle : exactTitle;
  }

  var EVAL_LINKED_ROLES = [
    "executor",
    "grader",
    "comparator",
    "comparator-recovery",
    "recovery"
  ];
  var USAGE_DETAIL_FIELDS = [
    { key: "input_tokens", label: "&#8595; Avg Input Tokens" },
    { key: "input_cached_tokens", label: "&#128279; Avg Cached Input Tokens" },
    { key: "input_cache_creation_tokens", label: "&#128203; Avg Input Cache Creation Tokens" },
    { key: "input_cache_write_tokens", label: "&#128221; Avg Input Cache Write Tokens" },
    { key: "output_tokens", label: "&#8593; Avg Output Tokens" },
    { key: "output_reasoning_tokens", label: "&#129504; Avg Output Reasoning Tokens" },
    {
      key: "total_api_duration_ms",
      label: "&#9202; Avg API Time / Eval (summed)",
      executorLabel: "&#9202; Avg Executor API Time / Eval"
    }
  ];

  function sourceIterationForColumn(col, iterationNumber, mode){
    if(col.key === "prev"){
      return iterationNumber > 1 ? iterationNumber - 1 : null;
    }
    if(col.key === "wos" && mode === "regression"){
      var config = (typeof D !== "undefined" && D.served_iteration_config) || {};
      var baselineIteration = Number(config.baseline_iteration);
      return Number.isInteger(baselineIteration) && baselineIteration > 0
        ? baselineIteration
        : 1;
    }
    return iterationNumber;
  }

  function sourceConfigurationForColumn(col){
    return col.key === "wos" ? "without_skill" : "current_skill";
  }

  function benchmarkForIteration(iterationNumber, selectedIteration, selectedBenchmark){
    if(iterationNumber === selectedIteration) return selectedBenchmark;
    var benchmarks = (typeof D !== "undefined" && D.iteration_benchmarks) || {};
    return benchmarks[String(iterationNumber)] || null;
  }

  function averageEvalAgentUsage(summary, roles, variant, field){
    if(!summary || !Array.isArray(summary.eval_agents)) return null;
    var perEval = Object.create(null);
    summary.eval_agents.forEach(function(agent){
      if(!agent || roles.indexOf(agent.role) === -1) return;
      if(variant && agent.variant !== variant) return;
      if(typeof agent.eval_id !== "string" || !agent.eval_id) return;
      var bucket = perEval[agent.eval_id];
      if(!bucket){
        bucket = perEval[agent.eval_id] = { sum: 0, count: 0, complete: true };
      }
      var value = agent[field];
      if(typeof value === "number" && Number.isFinite(value) && value >= 0){
        bucket.sum += value;
        bucket.count++;
      } else {
        bucket.complete = false;
      }
    });
    var evalValues = Object.keys(perEval).map(function(evalId){ return perEval[evalId]; })
      .filter(function(bucket){ return bucket.complete && bucket.count > 0; });
    if(!evalValues.length) return null;
    var measuredCount = evalValues.length;
    var expectedCount = Number.isInteger(summary.eval_count) && summary.eval_count > 0
      ? summary.eval_count
      : measuredCount;
    return {
      value: evalValues.reduce(function(sum, bucket){ return sum + bucket.sum; }, 0) /
        measuredCount,
      source: "final_usage",
      coverage: measuredCount,
      total: expectedCount,
      partial: measuredCount < expectedCount
    };
  }

  function runMetricValue(benchmark, col, iterationNumber, mode, field){
    var sourceIteration = sourceIterationForColumn(col, iterationNumber, mode);
    if(sourceIteration == null) return null;
    var sourceBenchmark = benchmarkForIteration(
      sourceIteration, iterationNumber, benchmark
    );
    var configuration = sourceConfigurationForColumn(col);
    if(field === "total_tokens"){
      var bucket = sourceBenchmark && sourceBenchmark.run_summary
        ? sourceBenchmark.run_summary[configuration]
        : col.bucket;
      return metricMean(bucket, "tokens");
    }
    if(sourceBenchmark){
      return EV.runResultMean(sourceBenchmark, configuration, field);
    }
    return null;
  }

  function usageAverageForColumn(benchmark, col, iterationNumber, mode, roles, field){
    var sourceIteration = sourceIterationForColumn(col, iterationNumber, mode);
    if(sourceIteration == null) return null;
    var summary = EV.iterationUsageSummary(sourceIteration);
    var variant = roles.length === 1 && roles[0] === "executor"
      ? sourceConfigurationForColumn(col)
      : null;
    return averageEvalAgentUsage(summary, roles, variant, field);
  }

  function tokenAverage(benchmark, bucket, col, iterationNumber, mode){
    var runMean = runMetricValue(
      benchmark, col, iterationNumber, mode, "total_tokens"
    );
    if(runMean != null) return { value: runMean, source: "run" };
    return usageAverageForColumn(
      benchmark, col, iterationNumber, mode, ["executor"], "total_tokens"
    ) || { value: null, source: null };
  }

  function tokenDetailValue(benchmark, col, iterationNumber, mode, field){
    var runMean = runMetricValue(benchmark, col, iterationNumber, mode, field);
    if(runMean != null) return { value: runMean, source: "run" };
    return usageAverageForColumn(
      benchmark, col, iterationNumber, mode, ["executor"], field
    );
  }

  function detailRowsMatchAcrossColumns(left, right){
    if(!left || !right) return false;
    var foundCommonValue = false;
    for(var i = 0; i < left.values.length; i++){
      var leftValue = left.values[i];
      var rightValue = right.values[i];
      if(leftValue == null && rightValue == null) continue;
      if(leftValue == null || rightValue == null ||
         leftValue.value !== rightValue.value){
        return false;
      }
      foundCommonValue = true;
    }
    return foundCommonValue;
  }

  function legacySessionTitle(value, field){
    if(value.divisor == null){
      return "Partial legacy session snapshot: iteration total of " +
        formatNum(value.iterationTotal) + " " + usageFieldLabel(field) +
        "; historical session usage may omit framework work.";
    }
    return "Partial legacy session snapshot: " + formatNum(value.iterationTotal) +
      " " + usageFieldLabel(field) + " divided across " + value.divisor +
      " eval cases; incomplete framework data and not a measured per-run value.";
  }

  function usageFieldLabel(field){
    var labels = {
      total_tokens: "tokens",
      input_tokens: "input tokens",
      input_cached_tokens: "cached input tokens",
      input_cache_creation_tokens: "input cache creation tokens",
      input_cache_write_tokens: "input cache write tokens",
      output_tokens: "output tokens",
      output_reasoning_tokens: "reasoning tokens",
      total_api_duration_ms: "API duration"
    };
    return labels[field] || field;
  }

  function finalSessionTitle(value, field){
    if(value.divisor == null){
      return "Copilot CLI session total for this iteration; includes shared " +
        "framework usage and is not a per-eval measurement.";
    }
    return "Display-only Copilot CLI session average: " +
      formatNum(value.iterationTotal) + " " + usageFieldLabel(field) +
      " divided equally across " + value.divisor +
      " eval cases; includes shared framework usage and is not measured per run.";
  }

  function usageValueTitle(value, field){
    if(value.source === "legacy_session") return legacySessionTitle(value, field);
    if(value.source === "final_usage" && value.divisor != null){
      return finalSessionTitle(value, field);
    }
    if(value.source === "final_usage" && value.coverage != null){
      if(value.coverage < value.total){
        return "Mean of eval-linked Copilot CLI agent usage in " +
          value.coverage + " of " + value.total +
          " eval cases with complete usage; missing records are excluded, not zero.";
      }
      return "Mean of eval-linked Copilot CLI agent usage across all eval cases.";
    }
    if(value.source === "final_usage"){
      return finalSessionTitle(value, field);
    }
    return "";
  }

  function renderTokenDetailRows(benchmark, cols, mode, iterationNumber){
    var details = USAGE_DETAIL_FIELDS.map(function(field){
      var values = cols.map(function(col){
        return tokenDetailValue(benchmark, col, iterationNumber, mode, field.key);
      });
      return {
        key: field.key,
        label: field.executorLabel || field.label,
        values: values
      };
    }).filter(function(row){
      return row.values.some(function(value){ return value != null; });
    });
    var creationRow = details.filter(function(row){
      return row.key === "input_cache_creation_tokens";
    })[0];
    var writeRow = details.filter(function(row){
      return row.key === "input_cache_write_tokens";
    })[0];
    if(detailRowsMatchAcrossColumns(creationRow, writeRow)){
      details = details.filter(function(row){
        return row.key !== "input_cache_write_tokens";
      });
    }
    if(!details.length) return "";
    var baselineIndex = cols.findIndex(function(col){ return col.key === "wos"; });
    var previousIndex = cols.findIndex(function(col){ return col.key === "prev"; });
    var currentIndex = cols.findIndex(function(col){ return col.key === "ws"; });
    var deltaRefIndex = mode === "regression" && previousIndex >= 0
      ? previousIndex
      : baselineIndex;

    return details.map(function(row){
      var html = '<tr class="bench-cost-token-detail"><td>' + row.label + '</td>';
      row.values.forEach(function(value){
        if(value == null){
          html += '<td>N/A</td>';
        } else {
          var title = withExactTokenTitle(
            usageValueTitle(value, row.key), value.value, row.key
          );
          var coverage = value.coverage != null &&
            value.total != null && value.coverage < value.total
            ? ' <small class="bench-cost-coverage" title="Coverage: ' +
              value.coverage + ' of ' + value.total +
              ' eval cases had complete usage; missing records are excluded, not zero.">' +
              value.coverage + '/' + value.total + ' evals</small>'
            : "";
          var formattedValue = row.key === "total_api_duration_ms"
            ? fmtDecimal(value.value / 1000, 1) + "s"
            : EV.formatTokenCount(value.value);
          html += '<td' + (title ? ' title="' + esc(title) + '"' : "") + '>' +
            formattedValue + coverage + '</td>';
        }
      });
      var current = currentIndex >= 0 ? row.values[currentIndex] : null;
      var deltaRef = deltaRefIndex >= 0 ? row.values[deltaRefIndex] : null;
      var baseline = baselineIndex >= 0 ? row.values[baselineIndex] : null;
      var partialComparison = (current && current.partial) ||
        (deltaRef && deltaRef.partial) || (baseline && baseline.partial);
      var delta = current && deltaRef && !partialComparison
        ? current.value - deltaRef.value
        : null;
      var ratio = current && baseline && !partialComparison && baseline.value !== 0
        ? current.value / baseline.value
        : null;
      var mixedSource = current && deltaRef && current.source !== deltaRef.source;
      var comparisonNotes = [];
      if(mixedSource){
        comparisonNotes.push(
          "Comparison uses different telemetry sources; inspect the per-cell provenance."
        );
      }
      if(delta != null && row.key !== "total_api_duration_ms"){
        comparisonNotes.push(
          "Exact difference: " + formatNum(delta) + " tokens."
        );
      }
      var comparisonTitle = comparisonNotes.length
        ? ' title="' + esc(comparisonNotes.join(" ")) + '"'
        : "";
      html += '<td class="cell-delta"' + comparisonTitle + '>';
      if(delta != null){
        var deltaClass = delta === 0 ? "flat" : (delta < 0 ? "pos" : "cost");
        var deltaText = row.key === "total_api_duration_ms"
          ? (delta >= 0 ? "+" : "") + fmtDecimal(delta / 1000, 1) + "s"
          : (delta >= 0 ? "+" : "") + EV.formatTokenCount(delta);
        html += '<span class="delta-chip ' + deltaClass + '">' + deltaText + '</span>';
      } else {
        html += 'N/A';
      }
      html += '</td>';
      var ratioFlag = ratio != null && ratio >= 2;
      html += '<td' + (ratioFlag ? ' class="bench-cost-ratio-warn"' : '') +
        comparisonTitle + '>' + (ratio == null ? 'N/A' : fmtDecimal(ratio, 2) + '\u00d7') +
        '</td></tr>';
      return html;
    }).join("");
  }

  function frameworkUsageValue(
    benchmark,
    col,
    iterationNumber,
    mode,
    field,
    perEval
  ){
    if(mode === "baseline" && col.key === "wos") return null;
    var sourceIteration = sourceIterationForColumn(col, iterationNumber, mode);
    if(sourceIteration == null) return null;
    var summary = EV.iterationUsageSummary(sourceIteration);
    var value = null, count = 0, source = null, partial = false;
    if(summary && summary.session){
      value = summary.session[field];
      count = summary.eval_count;
      source = "final_usage";
    } else {
      var sourceBenchmark = benchmarkForIteration(
        sourceIteration, iterationNumber, benchmark
      );
      var legacyUsage = sourceBenchmark && sourceBenchmark.run_summary &&
        sourceBenchmark.run_summary.session_usage;
      count = EV.evaluationCaseCount(sourceBenchmark);
      value = legacyUsage && legacyUsage[field];
      source = "legacy_session";
      partial = true;
    }
    if(typeof value !== "number" || !Number.isFinite(value) || count <= 0){
      return null;
    }
    return {
      value: perEval ? value / count : value,
      source: source,
      divisor: perEval ? count : null,
      partial: partial,
      iterationTotal: value
    };
  }

  function evalLinkedUsageValue(
    col,
    iterationNumber,
    mode,
    field
  ){
    if(mode === "baseline" && col.key === "wos") return null;
    var sourceIteration = sourceIterationForColumn(col, iterationNumber, mode);
    if(sourceIteration == null) return null;
    return averageEvalAgentUsage(
      EV.iterationUsageSummary(sourceIteration),
      EVAL_LINKED_ROLES,
      null,
      field
    );
  }

  function renderUsageCell(value, field){
    if(value == null || value.value == null) return "N/A";
    var formatted = field === "total_api_duration_ms"
      ? fmtDecimal(value.value / 1000, 1) + "s"
      : EV.formatTokenCount(value.value);
    if(value.coverage != null && value.total != null &&
       value.coverage < value.total){
      formatted += ' <small class="bench-cost-coverage" title="Coverage: ' +
        value.coverage + ' of ' + value.total +
        ' eval cases had complete usage; missing records are excluded, not zero.">' +
        value.coverage + '/' + value.total + ' evals</small>';
    }
    var title = value.source === "legacy_session"
      ? legacySessionTitle(value, field)
      : usageValueTitle(value, field);
    title = withExactTokenTitle(title, value.value, field);
    return '<span' + (title ? ' title="' + esc(title) + '"' : '') + '>' +
      formatted + '</span>';
  }

  function renderCostGroupHeader(title, description, columnCount){
    return '<tr class="bench-cost-group"><td colspan="' + columnCount +
      '"><strong>' + esc(title) + '</strong><small class="bench-cost-group-description">' +
      esc(description) + '</small></td></tr>';
  }

  function renderCollapsedBreakdown(rows, columnCount){
    if(!rows) return "";
    return '<tr class="bench-cost-details-row"><td colspan="' + columnCount +
      '"><details class="bench-cost-breakdown"><summary>Token breakdown</summary>' +
      '<table class="bench-cost-table bench-cost-detail-table"><tbody>' + rows +
      '</tbody></table></details></td></tr>';
  }

  function renderUsageAverageGroup(title, cols, mode, iterationNumber, benchmark, kind){
    var getValue = kind === "framework"
      ? function(col, field){
          return frameworkUsageValue(
            benchmark, col, iterationNumber, mode, field, true
          );
        }
      : function(col, field){
          return evalLinkedUsageValue(col, iterationNumber, mode, field);
        };
    var tokenValues = cols.map(function(col){ return getValue(col, "total_tokens"); });
    var detailRows = USAGE_DETAIL_FIELDS.map(function(field){
      return {
        key: field.key,
        label: field.label,
        values: cols.map(function(col){ return getValue(col, field.key); })
      };
    }).filter(function(row){
      return row.values.some(function(value){ return value != null; });
    });
    var creationRow = detailRows.filter(function(row){
      return row.key === "input_cache_creation_tokens";
    })[0];
    var writeRow = detailRows.filter(function(row){
      return row.key === "input_cache_write_tokens";
    })[0];
    if(detailRowsMatchAcrossColumns(creationRow, writeRow)){
      detailRows = detailRows.filter(function(row){
        return row.key !== "input_cache_write_tokens";
      });
    }
    var otherAgentDetails = kind === "framework"
      ? renderOtherAgentDetails(cols, mode, iterationNumber)
      : "";
    var hasData = tokenValues.some(function(value){ return value != null; }) ||
      detailRows.some(function(row){
        return row.values.some(function(value){ return value != null; });
      }) || otherAgentDetails !== "";
    if(!hasData) return "";

    var baselineIndex = cols.findIndex(function(col){ return col.key === "wos"; });
    var previousIndex = cols.findIndex(function(col){ return col.key === "prev"; });
    var currentIndex = cols.findIndex(function(col){ return col.key === "ws"; });
    var deltaRefIndex = mode === "regression" && previousIndex >= 0
      ? previousIndex
      : baselineIndex;
    var columnCount = cols.length + 3;
    var description = kind === "framework"
      ? "Whole Copilot CLI session totals divided by the distinct eval count for " +
        "each iteration; includes shared framework usage. Legacy snapshots may " +
        "be partial; this is not a per-run measurement."
      : "All eval-linked agents: executor, grader, comparator and recovery " +
        "records; missing eval usage is excluded, not counted as zero.";
    var html = renderCostGroupHeader(title, description, columnCount);

    function renderRow(label, values, field, detail){
      var rowClass = detail ? ' class="bench-cost-token-detail"' : "";
      var html = '<tr' + rowClass + '><td>' + label + '</td>';
      values.forEach(function(value){
        html += '<td>' + renderUsageCell(value, field) + '</td>';
      });
      var current = currentIndex >= 0 ? values[currentIndex] : null;
      var deltaRef = deltaRefIndex >= 0 ? values[deltaRefIndex] : null;
      var baseline = baselineIndex >= 0 ? values[baselineIndex] : null;
      var partialComparison = (current && current.partial) ||
        (deltaRef && deltaRef.partial) || (baseline && baseline.partial);
      var delta = current && deltaRef && !partialComparison
        ? current.value - deltaRef.value
        : null;
      var ratio = current && baseline && !partialComparison && baseline.value !== 0
        ? current.value / baseline.value
        : null;
      var deltaTitle = delta != null && field !== "total_api_duration_ms"
        ? ' title="' + esc("Exact difference: " + formatNum(delta) + " tokens.") + '"'
        : "";
      html += '<td class="cell-delta"' + deltaTitle + '>';
      if(delta == null){
        html += "N/A";
      } else {
        var deltaClass = delta === 0 ? "flat" : (delta < 0 ? "pos" : "cost");
        var deltaText = field === "total_api_duration_ms"
          ? (delta >= 0 ? "+" : "") + fmtDecimal(delta / 1000, 1) + "s"
          : (delta >= 0 ? "+" : "") + EV.formatTokenCount(delta);
        html += '<span class="delta-chip ' + deltaClass + '">' + deltaText + '</span>';
      }
      html += '</td><td>';
      html += ratio == null ? "N/A" : fmtDecimal(ratio, 2) + "\u00d7";
      html += '</td></tr>';
      return html;
    }

    html += renderRow("Avg Tokens", tokenValues, "total_tokens", false);
    var detailHtml = detailRows.map(function(row){
      return renderRow(row.label, row.values, row.key, true);
    }).join("");

    if(kind === "framework"){
      var totalValues = cols.map(function(col){
        return frameworkUsageValue(
          benchmark, col, iterationNumber, mode, "total_tokens", false
        );
      });
      if(totalValues.some(function(value){ return value != null; })){
        detailHtml += renderRow(
          "&#128202; Whole-session tokens (iteration total)",
          totalValues,
          "total_tokens",
          true
        );
      }
      var apiValues = cols.map(function(col){
        return frameworkUsageValue(
          benchmark, col, iterationNumber, mode, "total_api_duration_ms", false
        );
      });
      if(apiValues.some(function(value){ return value != null; })){
        detailHtml += renderRow(
          "&#9202; Whole-session API time (iteration total)",
          apiValues,
          "total_api_duration_ms",
          true
        );
      }
    }

    html += renderCollapsedBreakdown(detailHtml, columnCount);

    if(kind === "framework"){
      html += otherAgentDetails;
    }
    return html;
  }

  function renderOtherAgentDetails(cols, mode, iterationNumber){
    var agentColumns = cols;
    var agentsByLabel = Object.create(null);
    agentColumns.forEach(function(col, index){
      if(mode === "baseline" && col.key === "wos") return;
      var sourceIteration = sourceIterationForColumn(col, iterationNumber, mode);
      var summary = sourceIteration == null ? null : EV.iterationUsageSummary(sourceIteration);
      var totalsByLabel = Object.create(null);
      (summary && Array.isArray(summary.other_agents) ? summary.other_agents : [])
        .forEach(function(agent){
          if(!agent || typeof agent.label !== "string") return;
          var bucket = totalsByLabel[agent.label];
          if(!bucket){
            bucket = totalsByLabel[agent.label] = {
              total: 0,
              complete: true,
              hasRecord: false
            };
          }
          bucket.hasRecord = true;
          if(typeof agent.total_tokens === "number" &&
             Number.isFinite(agent.total_tokens) && agent.total_tokens >= 0){
            bucket.total += agent.total_tokens;
          } else {
            bucket.complete = false;
          }
        });
      Object.keys(totalsByLabel).forEach(function(label){
        var bucket = totalsByLabel[label];
        var row = agentsByLabel[label];
        if(!row){
          row = agentsByLabel[label] = {
            label: label,
            values: agentColumns.map(function(){ return null; })
          };
        }
        if(bucket.hasRecord && bucket.complete){
          row.values[index] = bucket.total;
        }
      });
    });
    var rows = Object.keys(agentsByLabel).sort().map(function(label){
      return agentsByLabel[label];
    });
    if(!rows.length) return "";

    var baselineIndex = agentColumns.findIndex(function(col){ return col.key === "wos"; });
    var previousIndex = agentColumns.findIndex(function(col){ return col.key === "prev"; });
    var currentIndex = agentColumns.findIndex(function(col){ return col.key === "ws"; });
    var deltaRefIndex = mode === "regression" && previousIndex >= 0
      ? previousIndex
      : baselineIndex;
    var deltaRefLabel = mode === "regression" && previousIndex >= 0
      ? "Previous"
      : "Baseline";
    var html = '<tr class="bench-cost-framework-agents"><td colspan="' +
      (cols.length + 3) +
      '"><details class="bench-cost-framework-agents-details">' +
      '<summary>Other framework agents</summary>' +
      '<p class="bench-cost-framework-agents-note">Unlinked support-agent totals by iteration ' +
      '(not variant-specific); already included in whole-session totals above and not attributed per eval.</p>' +
      '<table class="bench-cost-agents-table" aria-label="Other framework agent token totals by iteration">' +
      '<thead><tr><th>Agent</th>';
    agentColumns.forEach(function(col){
      html += '<th>' + esc(col.label) + '</th>';
    });
    html += '<th title="Current vs ' + deltaRefLabel + '">Δ <span class="bench-cost-ref">vs ' +
      deltaRefLabel + '</span></th>';
    html += '<th title="Current / Baseline">Ratio <span class="bench-cost-ref">vs Baseline</span></th>';
    html += '</tr></thead><tbody>';
    rows.forEach(function(row){
      html += '<tr><td>' + esc(row.label) + '</td>';
      row.values.forEach(function(value){
        if(value == null){
          html += '<td>N/A</td>';
        } else {
          html += '<td title="Exact value: ' + esc(formatNum(value)) +
            ' tokens.">' + EV.formatTokenCount(value) + '</td>';
        }
      });
      var current = currentIndex >= 0 ? row.values[currentIndex] : null;
      var deltaRef = deltaRefIndex >= 0 ? row.values[deltaRefIndex] : null;
      var baseline = baselineIndex >= 0 ? row.values[baselineIndex] : null;
      var delta = current != null && deltaRef != null
        ? current - deltaRef
        : null;
      var ratio = current != null && baseline != null && baseline !== 0
        ? current / baseline
        : null;
      var deltaTitle = delta != null
        ? ' title="Exact token difference: ' + esc(formatNum(delta)) + ' tokens."'
        : "";
      if(delta != null){
        var deltaClass = delta === 0 ? "flat" : (delta < 0 ? "pos" : "cost");
        html += '<td class="cell-delta"' + deltaTitle + '><span class="delta-chip ' +
          deltaClass + '">' + (delta >= 0 ? "+" : "") +
          EV.formatTokenCount(delta) + '</span></td>';
      } else {
        html += '<td class="cell-delta">N/A</td>';
      }
      var ratioFlag = ratio != null && ratio >= 2;
      html += '<td' + (ratioFlag ? ' class="bench-cost-ratio-warn"' : '') + '>' +
        (ratio == null ? "N/A" : fmtDecimal(ratio, 2) + "\u00d7") + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></details></td></tr>';
    return html;
  }

  EV.buildBenchmarkCostCard = function buildBenchmarkCostCard(src, iterationNumber){
    if(!src) return "";
    var rs = src.run_summary || {};
    var mode = getComparisonMode();

    var ws = rs.current_skill || {};
    var wos = rs.without_skill || {};
    var prev = rs.previous_skill || null;

    /* Column setup.
       Skill column = current_skill (always).
       Baseline column = without_skill (always, for cost reference).
       Previous column = previous_skill in regression mode only. */
    var cols = [];
    cols.push({key:"wos",  label:"Baseline", bucket:wos});
    if(mode === "regression" && prev){
      cols.push({key:"prev", label:"Previous", bucket:prev});
    }
    cols.push({key:"ws",   label: mode === "regression" ? "Current" : "Skill", bucket:ws});

    iterationNumber = Number.isInteger(iterationNumber)
      ? iterationNumber
      : (typeof state !== "undefined" && Number.isInteger(state.activeIteration)
          ? state.activeIteration
          : 1);
    var tokenValues = cols.map(function(col){
      return tokenAverage(src, col.bucket, col, iterationNumber, mode);
    });
    var baselineIndex = cols.findIndex(function(col){ return col.key === "wos"; });
    var previousIndex = cols.findIndex(function(col){ return col.key === "prev"; });
    var currentIndex = cols.findIndex(function(col){ return col.key === "ws"; });
    var deltaRefIndex = mode === "regression" && previousIndex >= 0
      ? previousIndex
      : baselineIndex;
    var currentTokens = currentIndex >= 0 ? tokenValues[currentIndex] : null;
    var rows = [
      {label:"Avg Time",       key:"time_seconds", fmt:formatTime, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1) + "s"; }},
      {label:"Avg Tokens",     key:"tokens",       fmt:fmtToken,   deltaFmt: function(d){ return (d >= 0 ? "+" : "") + EV.formatTokenCount(d); }},
      {label:"Avg Tool Calls", key:"tool_calls",   fmt:fmtNullableDecimal, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1); }},
      {label:"Avg Agent Turns", key:"steps",       fmt:fmtNullableDecimal, deltaFmt: function(d){ return (d >= 0 ? "+" : "") + fmtDecimal(d, 1); }}
    ];

    /* Table — ditch rows where every value is null (tool_calls / steps often
       aren't exposed by older aggregator versions). Keep rows where at least
       one variant has a value. Token stats may be explicitly null to mean
       unavailable, so keep that row visible when the schema is present. */
    var visibleRows = rows.filter(function(row){
      return cols.some(function(col, index){
        if(row.key === "tokens"){
          return (tokenValues[index] && tokenValues[index].value != null) ||
            (col.bucket && Object.prototype.hasOwnProperty.call(col.bucket, "tokens"));
        }
        return metricMean(col.bucket, row.key) != null;
      });
    });

    var usageGroups = renderUsageAverageGroup(
      "Average All Eval-linked Tokens / Eval",
      cols,
      mode,
      iterationNumber,
      src,
      "eval_linked"
    );
    usageGroups += renderUsageAverageGroup(
      "Average Total Framework Tokens / Eval",
      cols,
      mode,
      iterationNumber,
      src,
      "framework"
    );
    if(!visibleRows.length && !usageGroups) return "";

    var deltaRefLabel  = (mode === "regression" && prev) ? "Previous" : "Baseline";

    var html = '';
    html += '<div class="sec-heading" id="sec-cost" data-section="cost">';
    html += '<span class="sec-icon">' + NAV_ICONS.cost + '</span>';
    html += '<h2>Cost Overhead</h2></div>';
    html += '<div class="card">';
    if(visibleRows.length || usageGroups){
      html += '<div style="overflow-x:auto"><table class="bench-cost-table"><thead><tr>';
      html += '<th>Metric</th>';
      cols.forEach(function(c){ html += '<th>' + c.label + '</th>'; });
      html += '<th title="Current vs ' + deltaRefLabel + '">\u0394 <span class="bench-cost-ref">vs ' + deltaRefLabel + '</span></th>';
      html += '<th title="Current / Baseline">Ratio <span class="bench-cost-ref">vs Baseline</span></th>';
      html += '</tr></thead><tbody>';

      /* Δ and Ratio answer different questions:
         Δ     = vs Previous in regression mode (was the last iteration cheaper?),
                 vs Baseline in baseline mode.
         Ratio = always vs Baseline (how expensive is the skill overall?).
       Splitting references means a stable Ratio doesn't decay to ~1× as
       iterations converge, while Δ stays actionable per iteration. */
      visibleRows.forEach(function(row){
        if(row.key === "tokens"){
          html += renderCostGroupHeader(
            "Average Executor Tokens / Eval",
            "Executor-role usage only; excludes graders, comparators, recovery, " +
              "and shared framework work.",
            cols.length + 3
          );
        }
        var values = cols.map(function(col, index){
          if(row.key === "tokens") return tokenValues[index];
          return { value: metricMean(col.bucket, row.key), source: "run" };
        });
        var currentValue = currentIndex >= 0 ? values[currentIndex] : null;
        var deltaReference = deltaRefIndex >= 0 ? values[deltaRefIndex] : null;
        var baselineValue = baselineIndex >= 0 ? values[baselineIndex] : null;
        var wsVal = currentValue ? currentValue.value : null;
        var deltaRefVal = deltaReference ? deltaReference.value : null;
        var ratioBaseVal = baselineValue ? baselineValue.value : null;
        var deltaHasPartialTokens = row.key === "tokens" &&
          ((currentValue && currentValue.partial) ||
           (deltaReference && deltaReference.partial));
        var ratioHasPartialTokens = row.key === "tokens" &&
          ((currentValue && currentValue.partial) ||
           (baselineValue && baselineValue.partial));
        var delta = (wsVal != null && deltaRefVal != null &&
          !deltaHasPartialTokens) ? wsVal - deltaRefVal : null;
        var ratio = (wsVal != null && ratioBaseVal != null &&
          ratioBaseVal !== 0 && !ratioHasPartialTokens)
          ? wsVal / ratioBaseVal
          : null;
        var ratioFlag = ratio != null && ratio >= 2;

        html += '<tr>';
        html += '<td>' + row.label + '</td>';
        values.forEach(function(value){
          if(row.key === "tokens"){
            html += '<td>' + renderUsageCell(value, "total_tokens") + '</td>';
          } else {
            var numericValue = value ? value.value : null;
            html += '<td>' +
              (numericValue == null ? "\u2014" : row.fmt(numericValue)) +
              '</td>';
          }
        });
        var mixedSourceTitle = row.key === "tokens" && currentValue &&
          deltaReference && currentValue.source !== deltaReference.source
            ? ' title="Current and comparison values use different telemetry sources."'
            : "";
        html += '<td class="cell-delta"' + mixedSourceTitle + '>';
        if(delta != null){
          var chipCls = delta === 0 ? "flat" : (delta < 0 ? "pos" : "cost");
          html += '<span class="delta-chip ' + chipCls + '">' + row.deltaFmt(delta) + '</span>';
        } else {
          html += row.key === "tokens" ? "N/A" : '\u2014';
        }
        html += '</td>';
        html += '<td' + (ratioFlag ? ' class="bench-cost-ratio-warn"' : '') +
          mixedSourceTitle + '>';
        html += ratio == null
          ? (row.key === "tokens" ? "N/A" : '\u2014')
          : (fmtDecimal(ratio, 2) + "\u00d7");
        html += '</td>';
        html += '</tr>';
        if(row.key === "tokens"){
          html += renderCollapsedBreakdown(
            renderTokenDetailRows(src, cols, mode, iterationNumber),
            cols.length + 3
          );
        }
      });

      html += usageGroups;
      html += '</tbody></table></div>';
    }
    /* Narrative footer — prefer analyzer_notes synth, else client-side. */
    var notes = src.notes || [];
    var overheadNote = null;
    for(var i = 0; i < notes.length; i++){
      var n = notes[i];
      var txt = (n && n.text) || "";
      if(/skill overhead|token overhead|cost|tokens? higher|token spend|trade/i.test(txt)){
        overheadNote = txt;
        break;
      }
    }
    var hasPartialTokenCoverage = Boolean(currentTokens && currentTokens.partial);
    var narrative = hasPartialTokenCoverage ? null : overheadNote;
    if(!narrative && !hasPartialTokenCoverage){
      var wsPR = ws.pass_rate ? ws.pass_rate.mean : null;
      var wosPR = wos.pass_rate ? wos.pass_rate.mean : null;
      var ppDelta = (wsPR != null && wosPR != null) ? (wsPR - wosPR) * 100 : null;
      var wsTok = currentTokens.value, baseTok = metricMean(wos, "tokens");
      var tokRatio = (wsTok != null && baseTok != null && baseTok !== 0 &&
        !(currentTokens && currentTokens.partial))
        ? wsTok / baseTok
        : null;
      if(ppDelta != null && tokRatio != null){
        var sign = ppDelta >= 0 ? "+" : "";
        narrative = "Skill trades " + sign + ppDelta.toFixed(1) + "pp pass rate for ~" + tokRatio.toFixed(1) + "\u00d7 token spend.";
        if(currentTokens.source === "final_usage"){
          narrative += " Current tokens use uniquely attributed final usage.";
        }
      }
    }
    if(narrative){
      html += '<div class="bench-cost-narrative">' + esc(narrative) + '</div>';
    }
    html += '</div>'; /* card */
    return html;
  };
})();

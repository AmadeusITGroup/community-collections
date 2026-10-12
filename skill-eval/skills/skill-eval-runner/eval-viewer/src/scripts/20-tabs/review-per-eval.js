/* Review-tab per-eval block renderer (focus mode).

   Each call renders ONE eval as a stack of eight sections. Anchor ids
   match the slot keys in review-sidebar.js's REVIEW_SUBSECTIONS:

     1. Prompt           — #sec-prompt
     2. Output           — #sec-output
     3. Cost             — #sec-cost
     4. Expectations     — #sec-expectations  (handled by buildExpectationCompare)
     5. Strengths/Weak.  — #sec-sw
     6. A/B Comparison   — #sec-ab-comparison
     7. Skill feedback   — #sec-feedback
     8. Notes            — #sec-notes

   Each section uses the canonical .sec-heading grammar (no card chrome),
   matching Progression and Benchmark. */

function buildEvalReviewBlock(group, mode, oqSides, reviewUsageContext){
  var html = "";

  /* 1. Prompt */
  html += renderPromptSection(group);

  /* 2. Output */
  html += renderOutputSection(group, mode);

  /* 3. Cost */
  html += renderReviewCostSection(group, mode, reviewUsageContext);

  /* 4. Expectations (graded) */
  var expectHtml = buildExpectationCompare(group.wos, group.ws, group.baseline);
  if(expectHtml) html += expectHtml;

  /* 5. Strengths & Weaknesses */
  if(oqSides || group.wos || group.ws || (mode === "regression" && group.baseline)){
    html += renderStrengthsWeaknessesSection(group, mode, oqSides);
  }

  /* 6. A/B Comparison */
  if(group.comparison){
    html += renderABComparisonSection(group, mode);
  }

  /* 7. Skill feedback from this eval (current_skill variant only) */
  html += renderSkillFeedbackSection(group);

  /* 8. Notes textarea */
  html += renderNotesSection(group);

  return html;
}

/* ─────────────────────────────────────────────────────────────────────────
 * 1. Prompt
 * ─────────────────────────────────────────────────────────────────────────
 */
function renderPromptSection(group){
  if(!group.prompt) return "";
  var html = '';
  html += '<div class="sec-heading" id="sec-prompt">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.prompt + '</span>';
  html +=   '<h2>Prompt</h2>';
  html += '</div>';
  html += '<div class="card prompt-card">';
  html +=   '<div class="prompt-chat">';
  html +=     '<div class="prompt-chat-avatar" aria-hidden="true">\u{1F464}</div>';
  html +=     '<div class="prompt-chat-bubble">';
  html +=       '<div class="prompt-chat-label">User</div>';
  html +=       '<div class="prompt-chat-text">' + esc(group.prompt) + '</div>';
  html +=     '</div>';
  html +=   '</div>';
  html += '</div>';
  return html;
}

/* ─────────────────────────────────────────────────────────────────────────
 * 2. Output
 * ─────────────────────────────────────────────────────────────────────────
 */
function renderOutputSection(group, mode){
  var cols;
  if(mode === "regression"){
    cols = [
      { run: group.baseline, variant: "without_skill",   cls: "baseline" },
      { run: group.prev,     variant: "previous_skill",  cls: "previous" },
      { run: group.current,  variant: "current_skill",   cls: "current"  }
    ];
  } else {
    cols = [
      { run: group.wos, variant: "without_skill", cls: "baseline" },
      { run: group.ws,  variant: "current_skill", cls: "current"  }
    ];
  }

  var html = '';
  html += '<div class="sec-heading" id="sec-output">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.output + '</span>';
  html +=   '<h2>Output</h2>';
  html +=   '<div class="variant-pill-row">';
  cols.forEach(function(col){
    var lbl = variantLabelTight(col.variant, mode);
    var full = variantLabelFull(col.variant, mode);
    html += '<span class="variant-pill ' + col.cls + '" title="' + esc(full) + '">' + esc(lbl) + '</span>';
  });
  html +=   '</div>';
  html += '</div>';
  html += '<div class="section-card-body" style="--sc-cols:' + cols.length + '">';

  cols.forEach(function(col){
    html += '<div class="variant-card ' + col.cls + '">';
    html +=   '<div class="variant-card-head">';
    html +=     '<span class="variant-pill ' + col.cls + '">' + esc(variantLabelTight(col.variant, mode)) + '</span>';
    html +=   '</div>';
    html +=   '<div class="variant-card-body">' + renderOutputBody(col.run) + '</div>';
    html += '</div>';
  });

  html += '</div>';
  return html;
}

function renderOutputBody(run){
  if(!run){
    return '<p style="color:var(--text-muted);font-style:italic;font-size:0.82rem">No run data available for this variant.</p>';
  }
  if(!(run.outputs && run.outputs.length)){
    return '<p style="color:var(--text-muted);font-style:italic;font-size:0.82rem">No output files.</p>';
  }
  var html = '<div class="output-preview">';
  if(run.outputs.length > 1){
    html += '<div class="out-tab-bar">';
    run.outputs.forEach(function(o, oi){
      html += '<button class="out-tab' + (oi === 0 ? ' active' : '') + '" data-output-idx="' + oi + '">' +
        esc(o.name || ("Output " + (oi+1))) + '</button>';
    });
    html += '</div>';
  }
  run.outputs.forEach(function(o, oi){
    html += '<div class="out-content" data-output-idx="' + oi + '" style="' + (oi > 0 ? 'display:none' : '') + '">';
    if(o.type === "image" && o.data_uri){
      html += '<img src="' + esc(o.data_uri) + '" alt="' + esc(o.name) + '"/>';
    } else if(o.type === "text" && o.content){
      html += renderMarkdown(o.content);
    } else if(o.type === "pdf" && o.data_uri){
      html += '<embed src="' + esc(o.data_uri) + '" type="application/pdf" width="100%" height="300px"/>';
    } else {
      html += '<p style="color:var(--text-muted);font-style:italic">Binary file: ' + esc(o.name) + '</p>';
    }
    html += '</div>';
  });
  html += '</div>';
  return html;
}

function renderGenerationMetrics(run, usageOnly){
  if(!run) return "";
  var sr = (run.metrics && run.metrics.self_report) || {};
  var ht = (run.metrics && run.metrics.host_telemetry) || {};
  var toolCalls = ht.total_tool_calls != null ? ht.total_tool_calls : sr.total_tool_calls;
  var toolErrors = ht.tool_errors;
  var totalSteps = sr.total_steps;
  var hasUsage = ht.total_tokens != null || ht.model || ht.input_tokens != null ||
    ht.input_cached_tokens != null || ht.input_cache_creation_tokens != null ||
    ht.input_cache_write_tokens != null || ht.output_tokens != null ||
    ht.output_reasoning_tokens != null || ht.source != null;
  var hasExecution = toolCalls != null || totalSteps != null || toolErrors != null ||
    ht.total_duration_seconds != null || ht.turn_count != null;
  var has = usageOnly ? hasUsage : (hasUsage || hasExecution);
  if(!has) return "";
  var out = "";
  if(ht.model) out += '<span>&#129504; <strong>' + esc(ht.model) + '</strong></span>';
  if(!usageOnly && ht.total_duration_seconds != null) out += '<span>&#9202; <strong>' + formatTime(ht.total_duration_seconds) + '</strong></span>';
  if(ht.total_tokens != null){
    out += '<span title="Exact token count: ' + esc(formatNum(ht.total_tokens)) +
      ' tokens.">&#128221; <strong>' + window.__EV.formatTokenCount(ht.total_tokens) +
      '</strong> tokens</span>';
  } else {
    out += '<span>&#128221; Token usage <strong>N/A</strong></span>';
  }
  var inputDetails = [];
  if(ht.input_cached_tokens != null){
    inputDetails.push(
      '<span title="Exact token count: ' + esc(formatNum(ht.input_cached_tokens)) +
      ' tokens.">' + window.__EV.formatTokenCount(ht.input_cached_tokens) + " cached</span>"
    );
  }
  if(ht.input_cache_creation_tokens != null){
    inputDetails.push(
      '<span title="Exact token count: ' +
      esc(formatNum(ht.input_cache_creation_tokens)) + ' tokens.">' +
      window.__EV.formatTokenCount(ht.input_cache_creation_tokens) +
      " cache creation</span>"
    );
  }
  if(ht.input_cache_write_tokens != null){
    inputDetails.push(
      '<span title="Exact token count: ' + esc(formatNum(ht.input_cache_write_tokens)) +
      ' tokens.">' + window.__EV.formatTokenCount(ht.input_cache_write_tokens) +
      " cache write</span>"
    );
  }
  if(ht.input_tokens != null || inputDetails.length){
    out += '<span>&#8595; ';
    if(ht.input_tokens != null){
      out += '<strong title="Exact token count: ' + esc(formatNum(ht.input_tokens)) +
        ' tokens.">' + window.__EV.formatTokenCount(ht.input_tokens) +
        '</strong> input tokens';
    } else {
      out += 'Input details';
    }
    if(inputDetails.length){
      out += ' <small>(' + inputDetails.join('; ') + ')</small>';
    }
    out += '</span>';
  }
  if(ht.output_tokens != null || ht.output_reasoning_tokens != null){
    out += '<span>&#8593; ';
    if(ht.output_tokens != null){
      out += '<strong title="Exact token count: ' + esc(formatNum(ht.output_tokens)) +
        ' tokens.">' + window.__EV.formatTokenCount(ht.output_tokens) +
        '</strong> output tokens';
    } else {
      out += 'Output details';
    }
    if(ht.output_reasoning_tokens != null){
      out += ' <small>(<span title="Exact token count: ' +
        esc(formatNum(ht.output_reasoning_tokens)) + ' tokens.">' +
        window.__EV.formatTokenCount(ht.output_reasoning_tokens) +
        ' reasoning</span>)</small>';
    }
    out += '</span>';
  }
  if(!usageOnly && ht.turn_count != null) out += '<span><strong>' + formatNum(ht.turn_count) + '</strong> LLM turns</span>';
  if(!usageOnly && toolCalls != null) out += '<span>&#128295; <strong>' + formatNum(toolCalls) + '</strong> tool calls</span>';
  if(!usageOnly && totalSteps != null) out += '<span>&#128260; <strong>' + formatNum(totalSteps) + '</strong> steps</span>';
  if(!usageOnly && toolErrors != null && toolErrors > 0) out += '<span style="color:var(--red)">&#9888; <strong>' + formatNum(toolErrors) + '</strong> errors</span>';
  return out;
}

function renderCostRunMetrics(run){
  var sr = (run && run.metrics && run.metrics.self_report) || {};
  var ht = (run && run.metrics && run.metrics.host_telemetry) || {};
  var html = "";
  html += ht.total_duration_seconds != null
    ? '<span>&#9202; Run duration <strong>' + formatTime(ht.total_duration_seconds) + '</strong></span>'
    : '<span>&#9202; Run duration <strong>N/A</strong></span>';
  var toolCalls = ht.total_tool_calls != null ? ht.total_tool_calls : sr.total_tool_calls;
  html += toolCalls != null
    ? '<span>&#128295; Tool calls <strong>' + formatNum(toolCalls) + '</strong></span>'
    : '<span>&#128295; Tool calls <strong>N/A</strong></span>';
  html += sr.total_steps != null
    ? '<span>&#128260; Agent turns <strong>' + formatNum(sr.total_steps) + '</strong></span>'
    : '<span>&#128260; Agent turns <strong>N/A</strong></span>';
  if(ht.turn_count != null){
    html += '<span>LLM turns <strong>' + formatNum(ht.turn_count) + '</strong></span>';
  }
  if(ht.tool_errors != null && ht.tool_errors > 0){
    html += '<span style="color:var(--red)">&#9888; <strong>' +
      formatNum(ht.tool_errors) + '</strong> errors</span>';
  }
  return '<div class="variant-card-foot metrics-inline">' + html + '</div>';
}

function renderCostUsageAgent(agent){
  var role = agent.role.charAt(0).toUpperCase() + agent.role.slice(1);
  var html = '<div class="review-cost-agent">';
  html += '<div class="review-cost-agent-head"><strong>' + esc(role) + '</strong>';
  if(Array.isArray(agent.models) && agent.models.length){
    html += '<span class="iter-model-badge">' + esc(agent.models.join(", ")) + '</span>';
  }
  html += '</div>';
  html += '<div class="review-cost-agent-total">';
  html += agent.total_tokens != null
    ? '<strong title="Exact token count: ' + esc(formatNum(agent.total_tokens)) +
      ' tokens.">' + window.__EV.formatTokenCount(agent.total_tokens) + ' tokens</strong>'
    : '<strong>Token usage N/A</strong>';
  if(agent.total_api_duration_ms != null){
    html += ' · &#9202; API ' + formatTime(agent.total_api_duration_ms / 1000);
  }
  html += '</div>';

  var details = [
    ["input_tokens", "&#8595; Input"],
    ["input_cached_tokens", "&#128279; Cache read"],
    ["input_cache_creation_tokens", "Cache creation"],
    ["input_cache_write_tokens", "&#128221; Cache write"],
    ["output_tokens", "&#8593; Output"],
    ["output_reasoning_tokens", "&#129504; Reasoning"]
  ];
  var creation = agent.input_cache_creation_tokens;
  var write = agent.input_cache_write_tokens;
  details.forEach(function(detail){
    var value = agent[detail[0]];
    if(value == null) return;
    if(detail[0] === "input_cache_write_tokens" &&
       creation != null && creation === write) return;
    html += '<span class="review-cost-agent-detail" title="Exact token count: ' +
      esc(formatNum(value)) + ' tokens.">' + detail[1] + ' ' +
      window.__EV.formatTokenCount(value) + '</span>';
  });
  html += '</div>';
  return html;
}

function renderReviewCostSection(group, mode, reviewUsageContext){
  var cols;
  if(mode === "regression"){
    cols = [
      {run:group.baseline, variant:"without_skill", sourceKey:"baseline", cls:"baseline"},
      {run:group.prev, variant:"previous_skill", sourceKey:"previous", cls:"previous"},
      {run:group.current, variant:"current_skill", sourceKey:"current", cls:"current"}
    ];
  } else {
    cols = [
      {run:group.wos, variant:"without_skill", sourceKey:"baseline", cls:"baseline"},
      {run:group.ws, variant:"current_skill", sourceKey:"current", cls:"current"}
    ];
  }

  var evalId = String(group.eval_id != null ? group.eval_id : group.id);
  if(!/^eval-/.test(evalId)) evalId = "eval-" + evalId;
  var context = reviewUsageContext || {};
  var summaries = context.summaries || {};
  var sources = context.sources || {};
  var html = '';
  html += '<div class="sec-heading" id="sec-cost">';
  html += '<span class="sec-icon">' + NAV_ICONS.cost + '</span>';
  html += '<h2>Cost</h2></div>';
  html += '<div class="section-card-body" style="--sc-cols:' + cols.length + '">';

  cols.forEach(function(col){
    var source = sources[col.sourceKey];
    var summary = source && summaries[String(source.iteration)];
    var sourceVariant = source && source.configuration;
    var agents = (summary && Array.isArray(summary.eval_agents)
      ? summary.eval_agents
      : []
    ).filter(function(agent){
      return agent &&
        agent.eval_id === evalId &&
        agent.variant === sourceVariant &&
        (agent.role === "executor" || agent.role === "grader");
    });
    agents.sort(function(a, b){
      return a.role === b.role ? 0 : (a.role === "executor" ? -1 : 1);
    });

    html += '<div class="variant-card ' + col.cls + '">';
    html += '<div class="variant-card-head">';
    html += '<span class="variant-pill ' + col.cls + '">' +
      esc(variantLabelTight(col.variant, mode)) + '</span>';
    html += '</div>';
    html += '<div class="variant-card-body">';
    if(agents.length){
      agents.forEach(function(agent){ html += renderCostUsageAgent(agent); });
    } else if(!col.run){
      html += '<p class="review-cost-empty">No run data available for this variant.</p>';
    } else {
      var fallback = renderGenerationMetrics(col.run, true);
      if(fallback){
        html += '<div class="metrics-inline">' + fallback + '</div>';
      } else {
        html += '<p class="review-cost-empty">No attributable per-eval usage is available.</p>';
      }
    }
    html += '</div>';
    if(col.run || agents.length){
      html += renderCostRunMetrics(col.run);
    }
    html += '</div>';
  });
  html += '</div>';
  return html;
}

/* ─────────────────────────────────────────────────────────────────────────
 * 4. Strengths & Weaknesses
 * ─────────────────────────────────────────────────────────────────────────
 */
function renderStrengthsWeaknessesSection(group, mode, oqSides){
  var cols;
  if(mode === "regression"){
    var baseSides = group.baseline ? resolveOutputQualitySides(group.baseline.comparison) : null;
    cols = [
      { run: group.baseline, oq: baseSides ? baseSides.wos : null,  variant: "without_skill",  cls: "baseline" },
      { run: group.prev,     oq: oqSides ? oqSides.wos : null,      variant: "previous_skill", cls: "previous" },
      { run: group.current,  oq: oqSides ? oqSides.ws  : null,      variant: "current_skill",  cls: "current"  }
    ];
  } else {
    cols = [
      { run: group.wos, oq: oqSides ? oqSides.wos : null, variant: "without_skill", cls: "baseline" },
      { run: group.ws,  oq: oqSides ? oqSides.ws  : null, variant: "current_skill", cls: "current"  }
    ];
  }

  function pillWithScore(col){
    var lbl = variantLabelTight(col.variant, mode);
    var scoreTxt = col.oq && col.oq.score != null ? '<strong class="pct">' + col.oq.score + '/10</strong>' : '';
    return '<span class="variant-pill ' + col.cls + '">' + esc(lbl) + scoreTxt + '</span>';
  }

  var html = '';
  html += '<div class="sec-heading" id="sec-sw">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.sw + '</span>';
  html +=   '<h2>Strengths &amp; Weaknesses</h2>';
  html +=   '<div class="variant-pill-row">';
  cols.forEach(function(c){ html += pillWithScore(c); });
  html +=   '</div>';
  html += '</div>';
  html += '<div class="section-card-body" style="--sc-cols:' + cols.length + '">';

  cols.forEach(function(col){
    var oq = col.oq;
    var strengths = (oq && oq.strengths) || [];
    var weaknesses = (oq && oq.weaknesses) || [];

    html += '<div class="variant-card ' + col.cls + '">';
    html +=   '<div class="variant-card-head">';
    html +=     pillWithScore(col);
    html +=   '</div>';
    html +=   '<div class="variant-card-body">';
    if(strengths.length || weaknesses.length){
      html += '<ul class="sw-list">';
      strengths.forEach(function(s){
        html += '<li class="strength"><span class="sw-icon">&#10003;</span><span>' + esc(s) + '</span></li>';
      });
      weaknesses.forEach(function(w){
        html += '<li class="weakness"><span class="sw-icon">&#10007;</span><span>' + esc(w) + '</span></li>';
      });
      html += '</ul>';
    } else if(oq){
      html += '<p style="color:var(--text-light);font-style:italic;font-size:0.8rem;margin:0">No strengths or weaknesses recorded.</p>';
    } else {
      html += '<p style="color:var(--text-light);font-style:italic;font-size:0.8rem;margin:0">No comparator output-quality available for this variant.</p>';
    }
    html +=   '</div>';
    html += '</div>';
  });

  html += '</div>';
  return html;
}

function renderABComparisonSection(group, mode){
  var content = buildABComparisonContent(group.comparison, group.baseline);
  if(!content.verdict && !content.body) return "";

  var variants = mode === "regression"
    ? [["without_skill","baseline"],["previous_skill","previous"],["current_skill","current"]]
    : [["without_skill","baseline"],["current_skill","current"]];
  var pills = variants.map(function(p){
    return '<span class="variant-pill ' + p[1] + '">' +
      esc(variantLabelTight(p[0], mode)) + '</span>';
  }).join("");

  var html = '<div class="sec-heading" id="sec-ab-comparison">' +
    '<span class="sec-icon">' + NAV_ICONS["ab-comparison"] + '</span>' +
    '<h2>A/B Comparison</h2>' +
    '<div class="variant-pill-row">' + pills + '</div>' +
    '</div>';
  html += '<div class="card">' + content.verdict + content.body + '</div>';
  return html;
}

/* ─────────────────────────────────────────────────────────────────────────
 * 6. Skill Feedback
 * ─────────────────────────────────────────────────────────────────────────
 */
function renderSkillFeedbackSection(group){
  var run = group.ws || group.current;
  if(!run) return "";
  var body = renderReviewSkillFeedbackBody(run);
  if(!body.html) return "";

  var subtitleParts = [];
  if(body.skillCount) subtitleParts.push(body.skillCount + ' skill issue' + (body.skillCount === 1 ? '' : 's'));
  if(body.riskCount)  subtitleParts.push(body.riskCount + ' risk' + (body.riskCount === 1 ? '' : 's'));
  if(body.missingCount) subtitleParts.push(body.missingCount + ' missing input' + (body.missingCount === 1 ? '' : 's'));
  var subtitle = subtitleParts.join(' · ');

  var html = '';
  html += '<div class="sec-heading" id="sec-feedback">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.feedback + '</span>';
  html +=   '<h2>Skill Feedback</h2>';
  if(subtitle){
    html += '<span class="sec-heading-sub">' + esc(subtitle) + '</span>';
  }
  html += '</div>';
  html += '<div class="card review-skill-feedback-card">' + body.html + '</div>';
  return html;
}

/* Build the per-eval skill feedback body using the Benchmark .sfd-item
   visual. Returns {html, skillCount, riskCount, missingCount}. */
function renderReviewSkillFeedbackBody(run){
  var empty = { html: "", skillCount: 0, riskCount: 0, missingCount: 0 };
  if(!run) return empty;
  var uns = run.metrics && run.metrics.user_notes;
  if(!uns || typeof uns !== "object") return empty;
  /* Older user_notes payloads expose uncertainties/needs_review/workarounds
     instead of the skill_feedback object — silently ignore those. */
  if(!uns.skill_feedback && (uns.uncertainties || uns.needs_review || uns.workarounds)) return empty;

  var sf = uns.skill_feedback || {};
  var risks = uns.response_risks || [];
  var missing = uns.missing_inputs || [];

  var skillCount = SF_CATEGORIES.reduce(function(s, c){ return s + ((sf[c] || []).length); }, 0);
  if(!skillCount && !risks.length && !missing.length) return empty;

  var html = '';

  /* Skill issues — grouped by category but rendered as a flat list. Items use
     .sfd-item markup so styling matches the Benchmark Skill Feedback section. */
  if(skillCount){
    html += '<div class="rsf-group"><div class="rsf-group-head">Skill issues</div>';
    SF_CATEGORIES.forEach(function(cat){
      (sf[cat] || []).forEach(function(it){
        if(!it || typeof it !== "object") return;
        var impact = String(it.impact || "minor").toLowerCase();
        html += '<div class="sfd-item ' + impact + '" data-sfd-cat="' + esc(cat) + '">';
        html += '<div class="sfd-item-topic">' + esc(it.topic || "") + '</div>';
        html += '<div class="sfd-item-meta">';
        html += '<span class="impact-chip ' + impact + '">' + impact + '</span>';
        html += '<span class="cat-tag ' + esc(cat) + '">' + esc(_sfLabel(cat)) + '</span>';
        if(it.reference){
          html += '<span class="ref" title="' + esc(it.reference) + '">' + esc(it.reference) + '</span>';
        }
        html += '</div></div>';
      });
    });
    html += '</div>';
  }

  if(risks.length){
    html += '<div class="rsf-group"><div class="rsf-group-head">Response risks</div>';
    risks.forEach(function(r){
      if(!r || typeof r !== "object") return;
      html += '<div class="sfd-item minor">';
      html += '<div class="sfd-item-topic">' + esc(r.assumption || "") + '</div>';
      html += '<div class="sfd-item-meta">';
      html += '<span class="impact-chip minor">risk</span>';
      if(r.if_wrong) html += '<span>if wrong: ' + esc(r.if_wrong) + '</span>';
      if(r.grounded_in) html += '<span class="ref">' + esc(r.grounded_in) + '</span>';
      html += '</div></div>';
    });
    html += '</div>';
  }

  if(missing.length){
    html += '<div class="rsf-group"><div class="rsf-group-head">Missing inputs</div>';
    missing.forEach(function(m){
      var text = typeof m === "string" ? m : JSON.stringify(m);
      html += '<div class="sfd-item major">';
      html += '<div class="sfd-item-topic">' + esc(text) + '</div>';
      html += '<div class="sfd-item-meta"><span class="impact-chip major">missing</span></div>';
      html += '</div>';
    });
    html += '</div>';
  }

  return {
    html: html,
    skillCount: skillCount,
    riskCount: risks.length,
    missingCount: missing.length
  };
}

/* ─────────────────────────────────────────────────────────────────────────
 * 7. Notes textarea
 * ─────────────────────────────────────────────────────────────────────────
 */
function renderNotesSection(group){
  var fbKey = "eval-" + group.id;
  var existing = state.feedbackMap[fbKey] || "";
  var html = '';
  html += '<div class="sec-heading" id="sec-notes">';
  html +=   '<span class="sec-icon">' + NAV_ICONS.notes + '</span>';
  html +=   '<h2>User Notes</h2>';
  html += '</div>';
  html += '<div class="card notes-card">';
  html +=   '<div class="notes-subtitle">Reviewer feedback for this eval</div>';
  html +=   '<textarea class="feedback-area" data-eval-id="' + group.id +
           '" placeholder="Optional: note what the grader or comparator missed, or any judgement calls you want to revisit later.">' +
           esc(existing) + '</textarea>';
  html +=   '<div class="feedback-status" data-fb-status="' + group.id + '"></div>';
  html +=   '<div class="notes-submit-row">';
  html +=     '<button class="review-submit-btn" type="button" id="submit-feedback-btn">Submit Feedback</button>';
  html +=   '</div>';
  html += '</div>';
  return html;
}

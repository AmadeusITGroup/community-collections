/* Benchmark Contradictions + Skill Regressions panels. Both wrap inside
   the .section-card grammar and share the impact palette
   (red / amber / muted) used elsewhere. */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  function pct01(v){
    if(v == null) return "N/A";
    return (v * 100).toFixed(0) + "%";
  }

  function impactChip(sev){
    var s = String(sev || "minor").toLowerCase();
    var cls = s === "blocking" ? "blocking" : (s === "major" ? "major" : "minor");
    return '<span class="impact-chip ' + cls + '">' + s + '</span>';
  }

  /* Short "w/o 75%" or "prev 88%" inline label, pulled from alternate_variant. */
  function altInline(variant, rate){
    var prefix = variant === "without_skill" ? "w/o" : (variant === "previous_skill" ? "prev" : variant || "alt");
    return '<span style="color:var(--text-muted)">' + prefix + '</span> ' + pct01(rate);
  }

  EV.buildContradictionsCard = function buildContradictionsCard(contradictions){
    if(!contradictions || !contradictions.length) return "";
    var subtitle = contradictions.length + ' item' + (contradictions.length === 1 ? '' : 's') + ' \u00b7 grader vs comparator disagree \u2265 0.20';
    var html = '';
    html += '<div class="sec-heading" id="sec-contradictions" data-section="contradictions">';
    html += '<span class="sec-icon">' + NAV_ICONS.contradictions + '</span>';
    html += '<h2>Contradictions</h2>';
    html += '<span class="sec-heading-sub">' + subtitle + '</span>';
    html += '</div>';
    html += '<div class="card">';
    html += '<div class="bench-info-lead">Evals where the grader pass_rate and the blind comparator disagree.</div>';
    html += '<div style="overflow-x:auto"><table class="bench-generic-table"><thead><tr>';
    html += '<th>#</th><th>Eval</th><th>Current</th><th>Alternate</th><th>Winner</th><th>Sev</th>';
    html += '</tr></thead><tbody>';
    contradictions.forEach(function(c){
      var sev = String(c.severity || "minor").toLowerCase();
      html += '<tr class="clickable" data-eval-id="' + (c.eval_id != null ? c.eval_id : "") + '">';
      html += '<td>' + (c.eval_id != null ? "#" + c.eval_id : "\u2014") + '</td>';
      html += '<td title="' + esc(c.eval_name || "") + '">' +
        esc(c.eval_name || "\u2014") + '</td>';
      html += '<td>' + pct01(c.current_skill_pass_rate) + '</td>';
      html += '<td>' + altInline(c.alternate_variant, c.alternate_pass_rate) + '</td>';
      html += '<td>' + (c.comparator_winner || "tie") + '</td>';
      html += '<td>' + impactChip(sev) + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    html += '</div>'; /* card */
    return html;
  };

  EV.buildSkillRegressionsCard = function buildSkillRegressionsCard(skillRegressions, mode){
    if(!skillRegressions) return "";
    var vsBaseline = skillRegressions.vs_baseline || [];
    var vsPrevious = skillRegressions.vs_previous || [];
    if(!vsBaseline.length && !vsPrevious.length) return "";

    var subtitleParts = [];
    if(vsBaseline.length) subtitleParts.push(vsBaseline.length + ' vs baseline');
    if(vsPrevious.length) subtitleParts.push(vsPrevious.length + ' vs previous');
    var subtitle = subtitleParts.join(' \u00b7 ');

    var html = '';
    html += '<div class="sec-heading" id="sec-skill-regressions" data-section="skill-regressions">';
    html += '<span class="sec-icon">' + NAV_ICONS["skill-regressions"] + '</span>';
    html += '<h2>Skill Regressions</h2>';
    html += '<span class="sec-heading-sub">' + subtitle + '</span>';
    html += '</div>';
    html += '<div class="card">';
    html += '<div class="bench-info-lead">Evals where the blind comparator preferred the alternate over current.</div>';

    function renderBucket(rows, heading, slot){
      var bucketHtml = '<div class="bench-sub-block">';
      bucketHtml += '<div class="bench-sub-block-head">' +
        '<span>' + heading + '</span>' +
        '<span class="variant-pill ' + slot + '">' +
          (slot === "baseline" ? "Baseline" : "Previous") +
          ' <span class="pct">' + rows.length + ' wins vs current</span>' +
        '</span>' +
        '</div>';
      bucketHtml += '<div style="overflow-x:auto"><table class="bench-generic-table"><thead><tr>';
      bucketHtml += '<th>#</th><th>Eval</th><th>Current</th><th>Alt</th><th>\u0394</th><th>Sev</th>';
      bucketHtml += '</tr></thead><tbody>';
      rows.forEach(function(e){
        var deltaVal = e.pass_rate_delta != null ? Number(e.pass_rate_delta) : 0;
        var deltaCls = deltaVal < 0 ? "neg" : (deltaVal > 0 ? "pos" : "flat");
        var deltaStr = (deltaVal > 0 ? "+" : "") + (deltaVal * 100).toFixed(0) + "%";
        var reasoning = (e.comparator_reasoning || "").toString();
        if(reasoning.length > 220) reasoning = reasoning.slice(0, 217) + "\u2026";
        var sev = String(e.severity || "minor").toLowerCase();
        bucketHtml += '<tr class="clickable" data-eval-id="' + (e.eval_id != null ? e.eval_id : "") + '">';
        bucketHtml += '<td>' + (e.eval_id != null ? "#" + e.eval_id : "\u2014") + '</td>';
        bucketHtml += '<td title="' + esc(e.eval_name || "") + '">' +
          esc(e.eval_name || "\u2014") + '</td>';
        bucketHtml += '<td>' + pct01(e.current_pass_rate) + '</td>';
        bucketHtml += '<td>' + pct01(e.alternate_pass_rate) + '</td>';
        bucketHtml += '<td><span class="delta-chip ' + deltaCls + '">' + deltaStr + '</span></td>';
        bucketHtml += '<td>' + impactChip(sev) + '</td>';
        bucketHtml += '</tr>';
        if(reasoning){
          bucketHtml += '<tr class="reasoning-row"><td></td><td colspan="5" class="reasoning-cell">' +
            '<div class="reasoning-card">' + esc(reasoning) + '</div></td></tr>';
        }
      });
      bucketHtml += '</tbody></table></div></div>';
      return bucketHtml;
    }

    if(vsBaseline.length) html += renderBucket(vsBaseline, "VS BASELINE (without_skill)", "baseline");
    if(vsPrevious.length) html += renderBucket(vsPrevious, "VS PREVIOUS (previous_skill)", "previous");

    html += '</div>'; /* card */
    return html;
  };

  EV.bindContradictionsRegressionsNav = function bindContradictionsRegressionsNav(root){
    if(!root) return;
    root.querySelectorAll("tr.clickable[data-eval-id]").forEach(function(tr){
      tr.addEventListener("click", function(){
        var id = this.getAttribute("data-eval-id");
        if(id) _navToReviewEval(parseInt(id, 10));
      });
    });
  };
})();

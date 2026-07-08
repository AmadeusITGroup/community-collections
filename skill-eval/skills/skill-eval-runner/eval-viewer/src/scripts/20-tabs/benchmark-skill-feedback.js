/* Benchmark Skill Feedback drill-down — Shape → Hotspots → Items
   (filterable, group-collapsible).

   Data source: src.skill_feedback_rollup
     • totals: { category → count }
     • by_impact: { impact → count }
     • by_impact_items: { impact → [ {category, topic, reference, eval_ids, eval_names} ] }
     • top_references: [ {reference, count, eval_ids} ] */
(function(){
  "use strict";
  var EV = window.__EV = window.__EV || {};

  function evalChip(id, name){
    var nameSpan = name ? '<span class="eval-chip-name">' + esc(name) + '</span>' : '';
    return '<button type="button" class="eval-chip" data-nav-eval="' + id + '">' +
      '<span class="eval-chip-id">#' + id + '</span>' + nameSpan + '</button>';
  }

  EV.buildBenchmarkSkillFeedbackCard = function buildBenchmarkSkillFeedbackCard(src){
    var rollup = src && src.skill_feedback_rollup;
    if(!rollup) return "";
    var totals = rollup.totals || {};
    var byImpact = rollup.by_impact || {};
    var byImpactItems = rollup.by_impact_items || {};
    var topRefs = rollup.top_references || [];

    var totalCount = SF_CATEGORIES.reduce(function(s,c){ return s + (totals[c] || 0); }, 0);
    if(totalCount === 0){
      /* Preserve a minimal "clean" banner so reviewers know feedback was checked. */
      return '<div class="sec-heading" id="sec-skill-feedback" data-section="skill-feedback">' +
        '<span class="sec-icon">' + NAV_ICONS["skill-feedback"] + '</span>' +
        '<h2>Skill Feedback</h2></div>' +
        '<div class="card"><div class="sfd-subtitle"><strong>No skill feedback flagged</strong> by executor in this iteration.</div></div>';
    }

    /* Subtitle: "N items · 19 missing · 3 ambiguous · 0 broken · 2 outdated" (only non-zero cats listed). */
    var subtitleParts = ['<strong>' + totalCount + '</strong> item' + (totalCount === 1 ? '' : 's')];
    SF_CATEGORIES.forEach(function(c){
      var n = totals[c] || 0;
      if(n > 0){
        subtitleParts.push(n + ' ' + c.split("_")[0]);
      }
    });

    var html = '';
    html += '<div class="sec-heading" id="sec-skill-feedback" data-section="skill-feedback">';
    html += '<span class="sec-icon">' + NAV_ICONS["skill-feedback"] + '</span>';
    html += '<h2>Skill Feedback</h2></div>';
    html += '<div class="card">';
    html += '<div class="sfd-shape">';
    html += '<div class="sfd-subtitle">' + subtitleParts.join(' \u00b7 ') + '</div>';

    /* Impact bar — zero-count swatches collapse out. */
    var totalImpact = SF_IMPACTS.reduce(function(s,l){ return s + (byImpact[l] || 0); }, 0);
    if(totalImpact > 0){
      html += '<div class="sfd-impact-bar">';
      SF_IMPACTS.forEach(function(lvl){
        var count = byImpact[lvl] || 0;
        if(count === 0) return;
        var pct = count / totalImpact * 100;
        html += '<div class="impact-' + lvl + '" style="width:' + pct.toFixed(1) + '%" title="' + lvl + ': ' + count + '"></div>';
      });
      html += '</div>';
      html += '<div class="sfd-impact-legend">';
      SF_IMPACTS.forEach(function(lvl){
        var count = byImpact[lvl] || 0;
        if(count === 0) return;
        html += '<span><span class="swatch ' + lvl + '"></span>' + _sfLabel(lvl) + ' ' + count + '</span>';
      });
      html += '</div>';
    }
    html += '</div>';

    /* Hotspots — only references with count >= 2. */
    var hotspots = topRefs.filter(function(r){ return (r.count || 0) >= 2; });
    if(hotspots.length){
      html += '<div class="sfd-hotspots"><h4>Hotspots \u00b7 references flagged \u2265 2 times</h4>';
      hotspots.forEach(function(r){
        html += '<div class="sfd-hotspot-row">';
        html += '<span class="path" title="' + esc(r.reference) + '">' + esc(r.reference) + '</span>';
        html += '<span>';
        (r.eval_ids || []).forEach(function(id){ html += evalChip(id, ""); });
        html += '</span>';
        html += '<span class="count">' + r.count + '\u00d7</span>';
        html += '</div>';
      });
      html += '</div>';
    }

    /* Items — filters + impact groups. */
    html += '<div class="sfd-controls">';
    html += '<div class="filter-chip-row" data-sfd-filters>';
    html += '<button class="filter-chip active" data-sfd-filter="all">All <span class="count">' + totalCount + '</span></button>';
    SF_IMPACTS.forEach(function(lvl){
      var n = byImpact[lvl] || 0;
      if(n === 0) return;
      html += '<button class="filter-chip impact-' + lvl + '" data-sfd-filter="' + lvl + '">' + _sfLabel(lvl) + ' <span class="count">' + n + '</span></button>';
    });
    html += '</div>';
    html += '<select class="sort-select" data-sfd-category>';
    html += '<option value="all">All categories</option>';
    SF_CATEGORIES.forEach(function(c){
      html += '<option value="' + c + '">' + _sfLabel(c) + '</option>';
    });
    html += '</select>';
    html += '<span class="sfd-count-readout" data-sfd-count>' + totalCount + ' items shown</span>';
    html += '</div>';

    SF_IMPACTS.forEach(function(lvl){
      var group = byImpactItems[lvl] || [];
      if(!group.length) return;
      var collapsedByDefault = (lvl === "minor" && group.length > 3);
      html += '<div class="sfd-impact-group ' + lvl + '" data-sfd-group="' + lvl + '">';
      html += '<div class="sfd-impact-group-head">' + _sfLabel(lvl) + ' <span class="count">(' + group.length + ')</span></div>';
      group.forEach(function(item, i){
        var hidden = collapsedByDefault && i >= 3 ? ' style="display:none"' : '';
        html += '<div class="sfd-item ' + lvl + '" data-sfd-cat="' + (item.category || "") + '"' + hidden + (collapsedByDefault && i >= 3 ? ' data-sfd-extra="1"' : '') + '>';
        html += '<div class="sfd-item-topic">' + esc(item.topic || "") + '</div>';
        html += '<div class="sfd-item-meta">';
        if(item.category) html += '<span class="cat-tag ' + item.category + '">' + _sfLabel(item.category) + '</span>';
        (item.eval_ids || []).forEach(function(id, idx){
          var nm = (item.eval_names && item.eval_names[idx]) || "";
          html += evalChip(id, nm);
        });
        if(item.reference){
          html += '<span class="ref" title="' + esc(item.reference) + '">' + esc(item.reference) + '</span>';
        }
        html += '</div></div>';
      });
      if(collapsedByDefault){
        html += '<button type="button" class="sfd-show-more" data-sfd-show-more="' + lvl + '"><span class="sfd-show-more-glyph">\u25B6</span> Show all ' + group.length + '</button>';
      }
      html += '</div>';
    });

    html += '</div>'; /* card */
    return html;
  };

  EV.bindBenchmarkSkillFeedback = function bindBenchmarkSkillFeedback(root){
    if(!root) return;
    /* The widgets live as siblings under the section's .card; scope all
       binds to that card so a re-render of another tab's panel doesn't
       collide. */
    var filtersWrap = root.querySelector("[data-sfd-filters]");
    if(!filtersWrap) return;
    var card = filtersWrap.closest(".card") || root;
    var activeImpact = "all";
    var activeCat = "all";

    function refresh(){
      var visible = 0;
      card.querySelectorAll(".sfd-impact-group").forEach(function(group){
        var lvl = group.getAttribute("data-sfd-group");
        var showGroup = (activeImpact === "all") || (activeImpact === lvl);
        var any = false;
        group.querySelectorAll(".sfd-item").forEach(function(it){
          var catOk = (activeCat === "all") || (it.getAttribute("data-sfd-cat") === activeCat);
          var extra = it.getAttribute("data-sfd-extra") === "1";
          var expand = group.getAttribute("data-sfd-expanded") === "1";
          var collapsed = extra && !expand;
          var show = showGroup && catOk && !collapsed;
          it.style.display = show ? "" : "none";
          if(show) { any = true; visible++; }
        });
        group.style.display = (showGroup && any) ? "" : "none";
      });
      var readout = card.querySelector("[data-sfd-count]");
      if(readout) readout.textContent = visible + " items shown";
    }

    card.querySelectorAll("[data-sfd-filter]").forEach(function(btn){
      btn.addEventListener("click", function(){
        card.querySelectorAll("[data-sfd-filter]").forEach(function(b){ b.classList.remove("active"); });
        this.classList.add("active");
        activeImpact = this.getAttribute("data-sfd-filter");
        refresh();
      });
    });
    var catSel = card.querySelector("[data-sfd-category]");
    if(catSel){
      catSel.addEventListener("change", function(){ activeCat = this.value; refresh(); });
    }
    card.querySelectorAll("[data-sfd-show-more]").forEach(function(btn){
      btn.addEventListener("click", function(){
        var lvl = this.getAttribute("data-sfd-show-more");
        var group = card.querySelector('.sfd-impact-group[data-sfd-group="' + lvl + '"]');
        if(!group) return;
        group.setAttribute("data-sfd-expanded", "1");
        this.style.display = "none";
        refresh();
      });
    });
    card.querySelectorAll(".eval-chip[data-nav-eval]").forEach(function(chip){
      chip.addEventListener("click", function(e){
        e.stopPropagation();
        var id = this.getAttribute("data-nav-eval");
        if(id) _navToReviewEval(parseInt(id, 10));
      });
    });
    refresh();
  };
})();

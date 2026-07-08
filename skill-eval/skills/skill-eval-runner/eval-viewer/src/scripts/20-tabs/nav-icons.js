/* Single source of truth for sidebar + section-heading icons. Each tab's
   sidebar builder reads from here so an icon change flows through to every
   surface that references the same id. */

var NAV_ICONS = {
  /* Progression tab */
  overview:     "◉",
  trend:        "△",
  health:       "⚠︎",
  heatmap:      "▤",
  resources:    "⚙︎",
  "sf-trend":   "✱",

  /* Benchmark tab */
  headline:           "◆",
  cost:               "$",
  "quality-scores":   "○",
  contradictions:     "⚠︎",
  "skill-regressions":"↘",
  "skill-feedback":   "✱",
  "per-eval":         "≡",
  insights:           "✦",

  /* Review tab — same keys used in section-card heads and the TOC. */
  prompt:             "❯",
  output:             "▤",
  expectations:       "✓",
  sw:                 "⚖︎",
  "ab-comparison":    "◫",
  feedback:           "✶",
  notes:              "✎",
  summary:            "◆"
};
window.__EV = window.__EV || {};
window.__EV.NAV_ICONS = NAV_ICONS;

function buildProgressionSidebar(iters){
  var items = [];
  items.push({id:"overview",  label:"Overview", active:true});
  items.push({id:"trend",     label:"Trend"});

  var anyBench = (iters || []).some(function(it){ return getBenchmarkData(it.iteration); });
  if(anyBench) items.push({id:"health", label:"Health Signals"});

  items.push({id:"heatmap",   label:"Heatmap"});
  items.push({id:"resources", label:"Resources"});

  var benchmarks = D.iteration_benchmarks || {};
  var anyRollup = Object.keys(benchmarks).some(function(k){
    return benchmarks[k] && benchmarks[k].skill_feedback_rollup;
  });
  if(anyRollup) items.push({id:"sf-trend", label:"Skill Feedback Trend"});

  items.forEach(function(it){ it.icon = NAV_ICONS[it.id] || ""; });

  var html = '<ul class="sidebar-nav">';
  items.forEach(function(it){
    html += '<li><a href="#sec-' + it.id + '"' + (it.active ? ' class="active"' : '') +
            '><span class="nav-icon">' + it.icon + '</span>' + it.label + '</a></li>';
  });
  html += '</ul>';
  $sidebar.innerHTML = html;
  bindSidebarLinks();
}

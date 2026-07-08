/* Mode-aware variant labels.

   Canonical variant keys (match on-disk data, run_summary, winner_variant):
     • current_skill   → CSS .ws  — iteration N's skill run
     • without_skill   → CSS .wos — no-skill baseline run
     • previous_skill  → CSS .wos — iteration N-1's current_skill (regression mode)
     • baseline        → CSS .baseline — synthetic "no skill" column in regression mode

   CSS classes .wos/.ws are internal (Variant A / Variant B) and stay stable.
   Only visible text changes with mode. Tooltips always show the full name. */

var VARIANT_CSS_CLASS = {
  current_skill:  "ws",
  without_skill:  "wos",
  previous_skill: "wos",
  baseline:       "baseline"
};

var VARIANT_LABELS_TIGHT = {
  baseline:       "Baseline",
  current_skill:  { baseline: "Skill",    regression: "Current"  },
  without_skill:  { baseline: "Baseline", regression: "Baseline" },
  previous_skill: { baseline: "Previous", regression: "Previous" }
};

var VARIANT_LABELS_FULL = {
  baseline:       "Baseline (no skill)",
  current_skill:  { baseline: "With skill",      regression: "Current version"   },
  without_skill:  { baseline: "Without skill",   regression: "Without skill"     },
  previous_skill: { baseline: "Previous version",regression: "Previous version"  }
};

function getComparisonMode(){
  var bm = getBenchmarkData(state.activeIteration) || {};
  if(bm.metadata && bm.metadata.comparison_mode) return bm.metadata.comparison_mode;
  var it = getIterationData(state.activeIteration) || {};
  return it.comparison_mode || "baseline";
}

function variantCssClass(v){
  return VARIANT_CSS_CLASS[v] || "wos";
}

function variantLabelTight(v, mode){
  var entry = VARIANT_LABELS_TIGHT[v];
  if(entry == null) return v || "";
  return typeof entry === "string" ? entry : (entry[mode] || entry.baseline);
}

function variantLabelFull(v, mode){
  var entry = VARIANT_LABELS_FULL[v];
  if(entry == null) return v || "";
  return typeof entry === "string" ? entry : (entry[mode] || entry.baseline);
}

/* Side-keyed wrappers ("wos" = Variant A, "ws" = Variant B) for call sites
   that don't track the canonical variant name. */
function variantLabelForSide(which, mode){
  if(which === "ws") return variantLabelTight("current_skill", mode);
  return variantLabelTight(mode === "regression" ? "previous_skill" : "without_skill", mode);
}

function variantLabelFullForSide(which, mode){
  if(which === "ws") return variantLabelFull("current_skill", mode);
  return variantLabelFull(mode === "regression" ? "previous_skill" : "without_skill", mode);
}

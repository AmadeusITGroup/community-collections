/* Skill-feedback constants and label/badge helpers shared across the
   Benchmark drill-down, Review per-eval cards, and Progression trend table. */

var SF_CATEGORIES = [
  "missing_from_skill",
  "ambiguous_instructions",
  "broken_references",
  "outdated_or_wrong"
];

var SF_IMPACTS = ["blocking", "major", "minor"];

function _sfLabel(cat){
  return String(cat || "").replace(/_/g, " ").replace(/\b\w/g, function(c){
    return c.toUpperCase();
  });
}

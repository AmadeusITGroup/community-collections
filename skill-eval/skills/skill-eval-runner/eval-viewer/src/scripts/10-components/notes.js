/* Insight-card text helpers shared between progression and benchmark. */

var INSIGHT_ORDER = [
  "regression",
  "contradiction",
  "non_discriminating",
  "cost_saving",
  "new_eval",
  "observation",
  "improvement",
  "skill_value"
];

function insightSeverity(cat){
  var idx = INSIGHT_ORDER.indexOf(cat);
  return idx >= 0 ? idx : 99;
}

function normalizeNote(n){
  if(typeof n === "string") return {category: "observation", text: n};
  return n;
}

function sortNotes(notes){
  if(!notes) return [];
  return notes.map(normalizeNote).sort(function(a, b){
    return insightSeverity(a.category) - insightSeverity(b.category);
  });
}

/* Highlight #N references, numeric runs, and 'quoted' fragments inside note
   bodies so they pop without manual markdown. */
function highlightNote(text){
  if(!text) return "";
  var s = esc(text);
  s = s.replace(/#(\d+)/g, '<span class="eval-ref">#$1</span>');
  s = s.replace(/\b(\d+\.?\d*%?)\b/g, function(m){
    return /\d/.test(m) ? '<span class="hl-number">' + m + '</span>' : m;
  });
  s = s.replace(/'([^']+)'/g, '<span class="hl-quoted">$1</span>');
  return s;
}

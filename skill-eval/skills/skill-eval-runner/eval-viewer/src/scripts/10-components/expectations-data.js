/* Normalize a run's top-level `expectations[]` to an array of text strings.
   The source format is plain strings (from eval_metadata.json), but
   grading.expectations carries objects with a `.text` field — accept either
   shape defensively. */

function normalizeExpectationTexts(list){
  if(!list) return [];
  return list.map(function(e){
    if(typeof e === "string") return e;
    if(e && typeof e.text === "string") return e.text;
    return null;
  }).filter(function(t){ return t != null && t !== ""; });
}

/* Match key for pairing the same expectation across variants. Graders
   occasionally drop or keep the leading `[auto] ` prefix inconsistently
   (canonical eval_metadata.json keeps it; some grading.json files strip it),
   which used to break exact-string matching and render phantom "No data"
   cells. Strip the prefix and collapse whitespace so cross-variant matching
   is prefix- and spacing-insensitive. Display text is kept separately. */
function expectationMatchKey(text){
  return String(text == null ? "" : text)
    .replace(/^\s*\[auto\]\s*/i, "")
    .trim()
    .replace(/\s+/g, " ");
}

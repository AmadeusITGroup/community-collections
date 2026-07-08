/* Render markdown via the vendored `marked` library (GFM + line breaks).
   Wraps the output in a span carrying .md-content so block-element margins
   come from CSS. Falls back to escaped text if marked isn't available. */

function renderMarkdown(text){
  if(!text) return "";
  var src = String(text);
  if(typeof marked === "undefined" || !marked || !marked.parse){
    return '<span class="md-content">' + esc(src).replace(/\n/g, '<br>') + '</span>';
  }
  return '<span class="md-content">' + marked.parse(src, { breaks: true, gfm: true }) + '</span>';
}

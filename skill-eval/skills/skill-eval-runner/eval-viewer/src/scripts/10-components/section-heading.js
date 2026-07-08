/* Render a `<div class="sec-heading">` block. The data-section attribute
   feeds the scroll-spy; the id="sec-…" is the hash navigation target. */

function secHeading(icon, title, id){
  return '<div class="sec-heading" data-section="' + esc(id) + '" id="sec-' + esc(id) + '">' +
    '<span class="sec-icon">' + icon + '</span>' +
    '<h2>' + esc(title) + '</h2>' +
  '</div>';
}

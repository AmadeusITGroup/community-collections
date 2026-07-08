/* Wires the document scroll listener that drives:
     • the thin progress bar at the top of the viewport
     • the "Back to top" button visibility
     • the active-link highlight in the sidebar */

function initScrollListeners(){
  window.addEventListener("scroll", function(){
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var pct = h > 0 ? (window.scrollY / h) * 100 : 0;
    $scrollProg.style.width = pct + "%";
    $backToTop.classList.toggle("visible", window.scrollY > 300);
    updateActiveSidebarLink();
  }, {passive: true});
  $backToTop.addEventListener("click", function(){
    window.scrollTo({top: 0, behavior: "smooth"});
  });
}

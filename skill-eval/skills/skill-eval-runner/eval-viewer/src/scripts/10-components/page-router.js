/* Top-level page tabs (Progression / Benchmark / Review). Toggles
   data-page on <body> so CSS can scope rules per tab, then dispatches to
   the matching renderer. */

function initTabs(){
  document.querySelectorAll(".page-tab").forEach(function(tab){
    tab.addEventListener("click", function(){
      switchPage(this.getAttribute("data-page"));
    });
  });
}

function switchPage(page){
  state.activePage = page;
  document.body.setAttribute("data-page", page);
  /* Publish comparison mode so CSS can remap variant colors (previous vs baseline). */
  document.body.setAttribute("data-comp-mode", getComparisonMode() || "baseline");

  document.querySelectorAll(".page-tab").forEach(function(t){
    t.classList.toggle("active", t.getAttribute("data-page") === page);
  });
  if(page === "progression")     renderProgressionPage();
  else if(page === "benchmark")  renderBenchmarkPage();
  else if(page === "review")     renderReviewPage();
  window.scrollTo({top:0});
}

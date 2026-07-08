/* Wires the compact tab bar shown inside .output-preview when a run produced
   multiple output files. Each tab toggles which .out-content is visible. */

function bindOutputTabs(){
  $main.querySelectorAll(".out-tab-bar").forEach(function(bar){
    var container = bar.parentElement;
    bar.querySelectorAll(".out-tab").forEach(function(tab){
      tab.addEventListener("click", function(){
        var idx = this.getAttribute("data-output-idx");
        bar.querySelectorAll(".out-tab").forEach(function(t){ t.classList.remove("active"); });
        this.classList.add("active");
        container.querySelectorAll(".out-content").forEach(function(c){
          c.style.display = c.getAttribute("data-output-idx") === idx ? "" : "none";
        });
      });
    });
  });
}

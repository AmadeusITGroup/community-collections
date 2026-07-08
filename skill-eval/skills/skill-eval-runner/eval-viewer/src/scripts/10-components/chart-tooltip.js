/* Mouse-follow tooltip for any element carrying [data-tip] inside the main
   content (radar dots, dumbbell dots, trend chart points, …). Re-bound after
   each render so freshly emitted nodes pick it up. */

function bindChartTooltips(){
  $main.querySelectorAll("[data-tip]").forEach(function(el){
    el.addEventListener("mouseenter", function(){
      var tip = this.getAttribute("data-tip");
      if(!tip) return;
      $tooltip.textContent = tip;
      $tooltip.style.opacity = "1";
    });
    el.addEventListener("mousemove", function(e){
      $tooltip.style.left = (e.clientX + 14) + "px";
      $tooltip.style.top  = (e.clientY - 32) + "px";
    });
    el.addEventListener("mouseleave", function(){
      $tooltip.style.opacity = "0";
    });
  });
}

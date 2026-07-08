/* Iteration timeline in the top bar. Builds the dot+connector strip, sizes
   it for the available width (compact mode for >10 iterations), and wires
   click-to-switch handlers. Hidden when there's only one iteration. */

function buildIterTimeline(){
  if(!state.hasMultipleIterations){
    $iterControl.classList.add("hidden");
    return;
  }
  $iterControl.classList.remove("hidden");
  var iters = D.iterations || [];
  var compact = iters.length > 10;

  var html = '<span class="iter-label">Iterations</span>';
  html += '<div class="iter-track' + (compact ? ' compact' : '') + '">';
  for(var i = 0; i < iters.length; i++){
    var num = iters[i].iteration;
    var cls = num < state.activeIteration ? "past"
            : num === state.activeIteration ? "current"
            : "future";
    if(i > 0){
      var connCls = num <= state.activeIteration ? "active" : "inactive";
      html += '<div class="iter-connector ' + connCls + '"></div>';
    }
    html += '<div class="iter-dot ' + cls + '" data-iter="' + num + '" data-tip="Iteration ' + num + '">' + num + '</div>';
  }
  html += '</div>';
  $iterControl.innerHTML = html;

  /* If the strip overflows, switch to scrollable mode and center the current dot. */
  var track = $iterControl.querySelector('.iter-track');
  if(track){
    track.classList.remove('scrollable');
    var contentWidth = 0;
    for(var c = 0; c < track.children.length; c++) contentWidth += track.children[c].offsetWidth;
    var label = $iterControl.querySelector('.iter-label');
    var availableWidth = $iterControl.clientWidth - (label ? label.offsetWidth + 14 : 0);
    if(contentWidth > availableWidth){
      track.classList.add('scrollable');
      var currentDot = track.querySelector('.iter-dot.current');
      if(currentDot){
        var dotCenter = currentDot.offsetLeft - track.offsetLeft + currentDot.offsetWidth / 2;
        var ideal = dotCenter - track.clientWidth / 2;
        var maxScroll = track.scrollWidth - track.clientWidth;
        track.scrollLeft = Math.max(0, Math.min(ideal, maxScroll));
      }
    }
  }
  $iterControl.querySelectorAll(".iter-dot").forEach(function(dot){
    dot.addEventListener("click", function(){
      switchIteration(parseInt(this.getAttribute("data-iter"), 10));
    });
  });
}

function switchIteration(iterNum){
  state.activeIteration = iterNum;
  buildIterTimeline();
  switchPage(state.activePage);
}

/* Re-flow the timeline (compact mode + scroll centering) on resize. */
var _timelineResizeTimer;
window.addEventListener("resize", function(){
  clearTimeout(_timelineResizeTimer);
  _timelineResizeTimer = setTimeout(buildIterTimeline, 150);
});

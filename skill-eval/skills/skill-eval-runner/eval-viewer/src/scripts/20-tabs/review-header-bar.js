/* Review-tab sticky header bar.

     ‹  Eval N / M:  <name>  [▾]  ›             [Submit FB]

   Picker panel lists every eval (id, pass/fail dot, name, delta chip) and
   drives selection. localStorage persists the active eval per-skill so a
   reload restores the previous position. The document-level listeners
   (outside-click + keyboard nav) are wired exactly once via
   `_reviewHeaderInitGlobalListeners` — `buildReviewHeaderBar` only owns the
   per-render bar markup. */

var REVIEW_HEADER_KEY = "eval-viewer:last-viewed-eval:";

function _reviewHeaderStorageKey(){
  return REVIEW_HEADER_KEY + ((D && D.skill_name) || "default");
}

function _reviewHeaderRestore(){
  try{
    var raw = localStorage.getItem(_reviewHeaderStorageKey());
    if(raw == null) return null;
    var n = parseInt(raw, 10);
    return isNaN(n) ? null : n;
  }catch(_){ return null; }
}

function _reviewHeaderPersist(id){
  try{ localStorage.setItem(_reviewHeaderStorageKey(), String(id)); }catch(_){}
}

/* Resolve the initial eval id given the ordered list. Honors the persisted
   value when it still maps to an eval; otherwise falls back to the first. */
function _reviewHeaderResolveInitial(evalOrder){
  if(!evalOrder || !evalOrder.length) return null;
  var saved = _reviewHeaderRestore();
  if(saved != null){
    for(var i = 0; i < evalOrder.length; i++){
      if(evalOrder[i].id === saved) return saved;
    }
  }
  return evalOrder[0].id;
}

function _reviewHeaderBuildPanel(evalOrder, deltaByEval, mode){
  var html = '<div class="review-picker-panel" hidden role="listbox"><ul>';
  evalOrder.forEach(function(ev){
    var sum = ev.mainRun && ev.mainRun.grading && ev.mainRun.grading.summary;
    var pass = sum && sum.pass_rate === 1.0;
    var dotCls = pass ? "pass" : "fail";
    var passed = sum ? (sum.passed != null ? sum.passed : "?") : "?";
    var total  = sum ? (sum.total  != null ? sum.total  : "?") : "?";
    var dotTip = sum
      ? "With-skill: " + passed + "/" + total + " expectations passed"
      : "No grading summary available";
    var deltaHtml = '';
    if(deltaByEval && deltaByEval[ev.id] != null){
      var d = deltaByEval[ev.id], eps = 0.001;
      var cls = Math.abs(d) < eps ? "flat" : (d > 0 ? "up" : "down");
      var glyph = cls === "up" ? "▲" : (cls === "down" ? "▼" : "·");
      var prefix = mode === "regression" ? "Δ vs previous: " : "Δ vs without skill: ";
      var tip = prefix + (d >= 0 ? "+" : "") + (d * 100).toFixed(0) + "%";
      deltaHtml = '<span class="picker-delta ' + cls + '" title="' + tip + '">' +
        glyph + ' ' + (d >= 0 ? "+" : "") + (d * 100).toFixed(0) + '%</span>';
    }
    html += '<li role="option" data-eval-id="' + ev.id + '" tabindex="-1">' +
      '<span class="nav-dot ' + dotCls + '" title="' + esc(dotTip) + '"></span>' +
      '<span class="picker-id">#' + ev.id + '</span>' +
      '<span class="picker-name">' + esc(ev.name || "") + '</span>' +
      deltaHtml +
      '</li>';
  });
  html += '</ul></div>';
  return html;
}

/* Wire the document-level listeners exactly once — they read live state via
   `state._reviewEvalOrder` so they don't capture per-render closures. */
var _reviewHeaderGlobalListenersBound = false;

function _reviewHeaderInitGlobalListeners(){
  if(_reviewHeaderGlobalListenersBound) return;
  _reviewHeaderGlobalListenersBound = true;

  document.addEventListener("click", function(e){
    var panel = document.querySelector(".review-picker-panel");
    if(!panel || panel.hasAttribute("hidden")) return;
    var pickerBtn = document.querySelector(".review-picker");
    if(panel.contains(e.target) || (pickerBtn && pickerBtn.contains(e.target))) return;
    _reviewHeaderClosePanel(panel, pickerBtn);
  });

  document.addEventListener("keydown", function(e){
    var panel = document.querySelector(".review-picker-panel");
    var pickerBtn = document.querySelector(".review-picker");
    /* Esc closes panel. */
    if(e.key === "Escape" && panel && !panel.hasAttribute("hidden")){
      _reviewHeaderClosePanel(panel, pickerBtn);
      if(pickerBtn) pickerBtn.focus();
      return;
    }
    /* Arrow keys navigate evals when focus isn't in a textarea/input/select. */
    if(state.activePage !== "review") return;
    if(e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    var t = e.target || document.activeElement;
    var tag = t && t.tagName ? t.tagName.toLowerCase() : "";
    if(tag === "textarea" || tag === "input" || tag === "select") return;
    if(t && t.isContentEditable) return;
    /* Don't fight the picker panel's own keyboard handlers. */
    if(panel && !panel.hasAttribute("hidden")) return;
    e.preventDefault();
    _reviewHeaderShift(e.key === "ArrowLeft" ? -1 : +1);
  });
}

/* Mount the header bar and picker panel inside `container`. evalOrder is a
   list of {id, name, mainRun} sorted ascending by id. mode is the comparison
   mode at render time (drives the delta chip prefix). */
function buildReviewHeaderBar(container, evalOrder, deltaByEval, mode){
  if(!container || !evalOrder || !evalOrder.length) return;
  _reviewHeaderInitGlobalListeners();

  var html  = '<div class="review-header-bar">';
  html += '<button class="review-prev"  type="button" aria-label="Previous eval" title="Previous (←)">‹</button>';
  html += '<span class="review-pos">Eval <strong class="review-pos-cur">1</strong> / <strong>' + evalOrder.length + '</strong>:</span>';
  html += '<button class="review-picker" type="button" aria-haspopup="listbox" aria-expanded="false">';
  html +=   '<span class="review-picker-name"></span>';
  html +=   '<span class="review-picker-caret">▾</span>';
  html += '</button>';
  html += '<button class="review-next"  type="button" aria-label="Next eval" title="Next (→)">›</button>';
  html += '</div>';
  html += _reviewHeaderBuildPanel(evalOrder, deltaByEval, mode);
  container.insertAdjacentHTML("afterbegin", html);

  state._reviewEvalOrder = evalOrder;

  var bar = container.querySelector(".review-header-bar");
  var panel = container.querySelector(".review-picker-panel");
  var pickerBtn = bar.querySelector(".review-picker");

  bar.querySelector(".review-prev").addEventListener("click", function(){ _reviewHeaderShift(-1); });
  bar.querySelector(".review-next").addEventListener("click", function(){ _reviewHeaderShift(+1); });

  pickerBtn.addEventListener("click", function(e){
    e.stopPropagation();
    if(panel.hasAttribute("hidden")) _reviewHeaderOpenPanel(panel, pickerBtn);
    else                             _reviewHeaderClosePanel(panel, pickerBtn);
  });
  panel.querySelectorAll("li[data-eval-id]").forEach(function(li){
    li.addEventListener("click", function(){
      var id = parseInt(this.getAttribute("data-eval-id"), 10);
      _reviewHeaderClosePanel(panel, pickerBtn);
      if(!isNaN(id)) _renderActiveEval(id);
    });
  });
}

function _reviewHeaderOpenPanel(panel, pickerBtn){
  var btnRect = pickerBtn.getBoundingClientRect();
  panel.style.top  = (btnRect.bottom + window.scrollY + 4) + "px";
  panel.style.left = (btnRect.left   + window.scrollX) + "px";
  panel.removeAttribute("hidden");
  pickerBtn.setAttribute("aria-expanded", "true");

  var active = state.activeEvalId;
  panel.querySelectorAll("li").forEach(function(li){
    var id = parseInt(li.getAttribute("data-eval-id"), 10);
    li.classList.toggle("active", id === active);
  });
  var activeLi = panel.querySelector("li.active");
  if(activeLi) activeLi.scrollIntoView({block:"nearest"});
}

function _reviewHeaderClosePanel(panel, pickerBtn){
  panel.setAttribute("hidden", "");
  if(pickerBtn) pickerBtn.setAttribute("aria-expanded", "false");
}

function _reviewHeaderShift(delta){
  var order = state._reviewEvalOrder || [];
  if(!order.length) return;
  var idx = -1;
  for(var i = 0; i < order.length; i++){
    if(order[i].id === state.activeEvalId){ idx = i; break; }
  }
  if(idx < 0) idx = 0;
  var ni = idx + delta;
  if(ni < 0 || ni >= order.length) return;
  _renderActiveEval(order[ni].id);
}

function updateReviewHeaderBar(activeId){
  var order = state._reviewEvalOrder || [];
  if(!order.length) return;
  var idx = -1;
  for(var i = 0; i < order.length; i++){
    if(order[i].id === activeId){ idx = i; break; }
  }
  if(idx < 0) return;
  var ev = order[idx];
  var bar = document.querySelector(".review-header-bar");
  if(!bar) return;
  var posCur = bar.querySelector(".review-pos-cur");
  if(posCur) posCur.textContent = String(idx + 1);
  var nameSpan = bar.querySelector(".review-picker-name");
  if(nameSpan){
    var idLabel = ev.id != null ? "#" + ev.id + "  " : "";
    nameSpan.textContent = idLabel + (ev.name || "(unnamed)");
    nameSpan.title = ev.name || "";
  }
  var prev = bar.querySelector(".review-prev");
  var next = bar.querySelector(".review-next");
  if(prev) prev.disabled = (idx === 0);
  if(next) next.disabled = (idx === order.length - 1);
  /* Update active row marker if the panel is open. */
  var panel = document.querySelector(".review-picker-panel");
  if(panel && !panel.hasAttribute("hidden")){
    panel.querySelectorAll("li").forEach(function(li){
      var liId = parseInt(li.getAttribute("data-eval-id"), 10);
      li.classList.toggle("active", liId === activeId);
    });
  }
  _reviewHeaderPersist(activeId);
}

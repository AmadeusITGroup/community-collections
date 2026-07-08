/* User Notes / Submit Feedback wiring. Notes per eval are stored locally
   under the key "eval-feedback-<skill>"; submit pushes the bundle to the
   server-side feedback API (a no-op when serving from file://). */

function loadFeedback(){
  try{
    var raw = localStorage.getItem("eval-feedback-" + (D.skill_name || ""));
    if(raw) state.feedbackMap = JSON.parse(raw);
  }catch(_){}
}

function saveFeedback(){
  try{
    localStorage.setItem(
      "eval-feedback-" + (D.skill_name || ""),
      JSON.stringify(state.feedbackMap)
    );
  }catch(_){}
}

function submitFeedback(){
  var payload = {
    skill_name: D.skill_name,
    iteration: state.activeIteration,
    feedback: state.feedbackMap
  };
  fetch("/api/feedback", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  }).catch(function(){});
}

/* Auto-save reviewer notes inline as they type — debounced 500ms. */
function bindFeedbackAreas(){
  $main.querySelectorAll(".feedback-area").forEach(function(ta){
    var evalId = ta.getAttribute("data-eval-id");
    var statusEl = $main.querySelector('[data-fb-status="' + evalId + '"]');
    var timer = null;
    ta.addEventListener("input", function(){
      state.feedbackMap["eval-" + evalId] = ta.value;
      if(statusEl) statusEl.textContent = "Saving…";
      clearTimeout(timer);
      timer = setTimeout(function(){
        saveFeedback();
        if(statusEl) statusEl.textContent = "Saved to local storage";
        setTimeout(function(){ if(statusEl) statusEl.textContent = ""; }, 2000);
      }, 500);
    });
  });
}

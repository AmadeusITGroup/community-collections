/* Review-tab sidebar — flat 7-anchor list (Prompt … Notes), matching
   Progression's grammar. Scroll-spy uses one IntersectionObserver against
   the 7 anchors of the active eval (whichever exist — A/B Comparison, Skill
   feedback, Notes may be absent for some evals). Eval selection lives in
   the sticky header bar (review-header-bar.js); this file no longer cares
   about evals at all. */

var REVIEW_SUBSECTIONS = [
  { slot: "prompt",        label: "Prompt",          iconKey: "prompt"        },
  { slot: "output",        label: "Output",          iconKey: "output"        },
  { slot: "expectations",  label: "Expectations",    iconKey: "expectations"  },
  { slot: "sw",            label: "S&W",             iconKey: "sw"            },
  { slot: "ab-comparison", label: "A/B comparison",  iconKey: "ab-comparison" },
  { slot: "feedback",      label: "Skill feedback",  iconKey: "feedback"      },
  { slot: "notes",         label: "Notes",           iconKey: "notes"         }
];

function buildReviewSidebar(){
  var html = '<ul class="sidebar-nav">';
  REVIEW_SUBSECTIONS.forEach(function(sub, i){
    var icon = (NAV_ICONS && sub.iconKey && NAV_ICONS[sub.iconKey]) || "";
    var iconHtml = icon ? '<span class="nav-icon">' + icon + '</span>' : '';
    html += '<li data-section-slot="' + sub.slot + '">' +
      '<a href="#sec-' + sub.slot + '"' + (i === 0 ? ' class="active"' : '') + '>' +
      iconHtml + esc(sub.label) +
      '</a></li>';
  });
  html += '</ul>';
  $sidebar.innerHTML = html;
  _bindReviewSidebarLinks();
}

function _bindReviewSidebarLinks(){
  $sidebar.querySelectorAll("a[href^='#sec-']").forEach(function(a){
    a.addEventListener("click", function(e){
      e.preventDefault();
      var target = document.querySelector(this.getAttribute("href"));
      if(target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      $sidebar.classList.remove("mobile-open");
    });
  });
}

var _reviewScrollSpyObserver = null;

function _bindReviewScrollSpy(){
  if(_reviewScrollSpyObserver){
    _reviewScrollSpyObserver.disconnect();
    _reviewScrollSpyObserver = null;
  }
  if(typeof IntersectionObserver === "undefined") return;

  var anchors = REVIEW_SUBSECTIONS
    .map(function(sub){ return document.getElementById("sec-" + sub.slot); })
    .filter(Boolean);
  if(!anchors.length) return;

  var chromeH = (getComputedStyle(document.documentElement).getPropertyValue("--chrome-h") || "103px").trim();

  _reviewScrollSpyObserver = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(!entry.isIntersecting) return;
      var slot = entry.target.id.replace(/^sec-/, "");
      $sidebar.querySelectorAll("li[data-section-slot]").forEach(function(li){
        li.classList.toggle("active", li.getAttribute("data-section-slot") === slot);
      });
      $sidebar.querySelectorAll("a[href^='#sec-']").forEach(function(a){
        a.classList.toggle("active", a.getAttribute("href") === "#sec-" + slot);
      });
    });
  }, {
    rootMargin: "-" + chromeH + " 0px -60% 0px",
    threshold: 0
  });
  anchors.forEach(function(el){ _reviewScrollSpyObserver.observe(el); });
}

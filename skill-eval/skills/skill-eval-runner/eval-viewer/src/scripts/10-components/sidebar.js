/* Sidebar mobile toggle + the shared link-binder + the scroll-spy that
   highlights the section currently centered in the viewport. */

function initSidebarToggle(){
  document.getElementById("sidebar-toggle").addEventListener("click", function(){
    $sidebar.classList.toggle("mobile-open");
  });
}

function bindSidebarLinks(){
  $sidebar.querySelectorAll("a[href^='#sec-']").forEach(function(a){
    a.addEventListener("click", function(e){
      e.preventDefault();
      var target = document.querySelector(this.getAttribute("href"));
      /* Target is a non-sticky .eval-anchor placed just above each sticky
         .eval-header — scroll-margin-top offsets for the chrome. */
      if(target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      $sidebar.classList.remove("mobile-open");
    });
  });
}

function updateActiveSidebarLink(){
  var sections = $main.querySelectorAll("[data-section]");
  if(!sections.length) return;
  var active = null;
  sections.forEach(function(s){
    if(s.getBoundingClientRect().top <= 160) active = s.getAttribute("data-section");
  });
  /* At page bottom, force-activate the last section. */
  var atBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 50;
  if(atBottom){
    active = sections[sections.length - 1].getAttribute("data-section");
  }
  if(active){
    $sidebar.querySelectorAll(".sidebar-nav a").forEach(function(a){
      a.classList.toggle("active", a.getAttribute("href") === "#sec-" + active);
    });
  }
}

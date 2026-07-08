/* Light/dark theme toggle. Persists choice to localStorage and updates the
   toggle button glyph (☀ in dark mode, ☽ in light mode). */

function initTheme(){
  var btn = document.getElementById("theme-toggle");
  var saved = localStorage.getItem("eval-theme");
  if(saved) document.documentElement.setAttribute("data-theme", saved);
  function paintGlyph(){
    var cur = document.documentElement.getAttribute("data-theme");
    btn.textContent = cur === "dark" ? "☀" : "☽";
  }
  btn.addEventListener("click", function(){
    var cur = document.documentElement.getAttribute("data-theme");
    var next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("eval-theme", next);
    paintGlyph();
  });
  paintGlyph();
}

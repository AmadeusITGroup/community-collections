/* HTML escaping + numeric formatters used everywhere in the bundle. Hoisted
   inside the outer IIFE so call sites can use the bare name. */

function esc(s){
  if(!s) return "";
  var d = document.createElement("div");
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}

function formatStatPct(v){
  if(v == null) return "N/A";
  return (v * 100).toFixed(1) + "%";
}

function formatTime(v){
  if(v == null) return "N/A";
  return parseFloat(v).toFixed(1) + "s";
}

function formatNum(v){
  if(v == null) return "N/A";
  return Math.round(parseFloat(v)).toLocaleString();
}

function formatDelta(v){
  if(v == null) return "N/A";
  var n = parseFloat(v);
  return (n >= 0 ? "+" : "") + (n * 100).toFixed(1) + "%";
}

function formatDeltaTime(v){
  if(v == null) return "N/A";
  var n = parseFloat(v);
  return (n >= 0 ? "+" : "") + n.toFixed(1) + "s";
}

function formatDeltaNum(v){
  if(v == null) return "N/A";
  var n = parseFloat(v);
  return (n >= 0 ? "+" : "") + Math.round(n).toLocaleString();
}


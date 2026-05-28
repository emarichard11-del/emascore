function applyTheme() {
  var mode = localStorage.getItem('ema_theme') || 'dark';
  if (mode === 'dark') { applyColors(false); return; }
  if (mode === 'auto') {
    navigator.geolocation.getCurrentPosition(function(pos) {
      var hour = new Date().getHours();
      var sunrise = pos.coords.latitude > 0 ? 6 : 7;
      var sunset = pos.coords.latitude > 0 ? 18 : 17;
      applyColors(hour >= sunrise && hour < sunset);
    }, function() { applyColors(new Date().getHours() >= 6 && new Date().getHours() < 18); });
    return;
  }
  if (mode === 'manual') {
    var start = localStorage.getItem('ema_time_start') || '06:00';
    var end = localStorage.getItem('ema_time_end') || '18:00';
    var cur = new Date().getHours() * 60 + new Date().getMinutes();
    var s = parseInt(start.split(':')[0]) * 60 + parseInt(start.split(':')[1]);
    var e = parseInt(end.split(':')[0]) * 60 + parseInt(end.split(':')[1]);
    applyColors(cur >= s && cur < e);
  }
}
function applyColors(isLight) {
  var existing = document.getElementById('theme-style');
  if (existing) existing.remove();
  var style = document.createElement('style');
  style.id = 'theme-style';
  if (isLight) {
    style.innerHTML = 'body{background:#f0f4f8!important;color:#0a0e1a!important}.header,.bottom-nav{background:#ffffff!important;border-color:#ddd!important}.menu-item,.match-card,.section,.league-section{background:#ffffff!important;border-color:#ddd!important;color:#0a0e1a!important}.menu-name,.header-title,.match-teams,.league-name{color:#0a0e1a!important}.menu-sub,.match-time,.bnav-lbl{color:#666!important}.sec-title{color:#888!important}';
  } else {
    style.innerHTML = 'body{background:#0a0e1a!important;color:#fff!important}.header,.bottom-nav{background:#0f1923!important;border-color:#1a2a2a!important}.menu-item,.match-card{background:#0f1923!important;border-color:#1a2a2a!important}.menu-name,.header-title{color:#fff!important}.menu-sub,.bnav-lbl{color:#556!important}.sec-title{color:#556!important}';
  }
  document.head.appendChild(style);
}
applyTheme();

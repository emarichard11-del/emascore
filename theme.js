function applyTheme() {
  var mode = localStorage.getItem('ema_theme') || 'dark';
  var isLight = false;

  if (mode === 'dark') {
    applyColors(false);
    return;
  }

  if (mode === 'auto') {
    navigator.geolocation.getCurrentPosition(function(pos) {
      var lat = pos.coords.latitude;
      var hour = new Date().getHours();
      var sunrise = lat > 0 ? 6 : 7;
      var sunset = lat > 0 ? 18 : 17;
      applyColors(hour >= sunrise && hour < sunset);
    }, function() {
      var hour = new Date().getHours();
      applyColors(hour >= 6 && hour < 18);
    });
    return;
  }

  if (mode === 'manual') {
    var start = localStorage.getItem('ema_time_start') || '06:00';
    var end = localStorage.getItem('ema_time_end') || '18:00';
    var now = new Date();
    var cur = now.getHours() * 60 + now.getMinutes();
    var s = parseInt(start.split(':')[0]) * 60 + parseInt(start.split(':')[1]);
    var e = parseInt(end.split(':')[0]) * 60 + parseInt(end.split(':')[1]);
    applyColors(cur >= s && cur < e);
  }
}

function applyColors(isLight) {
  var r = document.documentElement;
  if (isLight) {
    document.body.style.background = '#f0f4f8';
    document.body.style.color = '#0a0e1a';
    document.querySelectorAll('.header, .bottom-nav').
for f in /c/EMASCORE/frontend/*.html; do
  sed -i 's|</head>|<script src="theme.js"></script>\n</head>|' "$f"
done
cd /c/EMASCORE/frontend
git add .
git commit -m "ajout theme.js mode clair/sombre toutes les pages"
git push

// Apply the saved theme before first paint to avoid a light/dark flash. A file rather than an
// inline <script>, so the Content-Security-Policy can forbid inline scripts.
try {
  var t = localStorage.getItem("theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
} catch (e) {}

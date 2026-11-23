/* Runs before the bundle so the splash matches the saved theme. script-src is 'self', so this cannot be inline. */
(function () {
  var theme = "system";
  try { theme = localStorage.getItem("studio.theme") || "system"; } catch (e) {}
  var dark = theme === "dark" || (theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  var bg = dark ? "#0f1115" : "#f6f7f9";
  var fg = dark ? "#e9ecf2" : "#15181e";
  var root = document.documentElement;
  root.dataset.theme = dark ? "dark" : "light";
  root.style.background = bg;
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", dark ? "#0f1115" : "#ffffff");
  var el = document.getElementById("splash");
  if (!el) return;
  el.style.background = bg;
  el.style.color = fg;
  el.style.setProperty("--accent", dark ? "#7c9cff" : "#3d5afe");
})();

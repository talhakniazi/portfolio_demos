/* PureSpace - site behaviour. Everything works without JavaScript; this only improves it. */
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.remove("no-js");
  root.classList.add("js");

  document.addEventListener("DOMContentLoaded", function () {
    // Mobile navigation
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.getElementById("site-nav");
    if (toggle && nav) {
      var close = function () { nav.classList.remove("is-open"); toggle.setAttribute("aria-expanded", "false"); };
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) { var first = nav.querySelector("a"); if (first) first.focus(); }
      });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("is-open")) { close(); toggle.focus(); } });
      document.addEventListener("click", function (e) { if (nav.classList.contains("is-open") && !nav.contains(e.target) && !toggle.contains(e.target)) close(); });
      window.matchMedia("(min-width: 961px)").addEventListener("change", close);
    }

    // Hero: the cloths settle onto the stack once, on page load
    var cloths = document.querySelector(".hero-cloths");
    if (cloths) requestAnimationFrame(function () { requestAnimationFrame(function () { cloths.classList.add("is-in"); }); });

    // Forms: move focus to the error summary; stop double submissions
    var summary = document.getElementById("error-summary");
    if (summary) summary.focus();
    document.querySelectorAll("form[data-validate], form[data-once]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (form.dataset.sending === "1") { e.preventDefault(); return; }
        form.dataset.sending = "1";
        var btn = form.querySelector("button[type=submit]");
        if (btn) { btn.disabled = true; btn.dataset.label = btn.textContent; btn.textContent = "Sending..."; }
        // If the browser goes back to this page (bfcache), re-enable the button
        window.addEventListener("pageshow", function () {
          form.dataset.sending = "";
          if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label; }
        }, { once: true });
      });
    });
  });
})();

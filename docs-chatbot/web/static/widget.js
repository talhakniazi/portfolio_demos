/* Kestrel help widget. Embed with:
 *   <link rel="stylesheet" href="https://YOUR-HOST/static/widget.css">
 *   <script src="https://YOUR-HOST/static/widget.js" defer></script>
 *   <div id="kc-chat" data-title="Help" data-api="https://YOUR-HOST/api/chat"></div>
 */
(function () {
  "use strict";
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  document.addEventListener("DOMContentLoaded", function () {
    var host = document.getElementById("kc-chat");
    if (!host) return;
    var api = host.dataset.api || "/api/chat";
    var history = [];

    var launch = el("button", "kc-launch", "Ask a question");
    launch.type = "button"; launch.setAttribute("aria-expanded", "false"); launch.setAttribute("aria-controls", "kc-panel");
    var panel = el("section", "kc-panel"); panel.id = "kc-panel"; panel.hidden = true; panel.setAttribute("aria-label", "Help assistant");
    var top = el("div", "kc-top");
    var title = el("div"); title.appendChild(el("b", null, host.dataset.title || "Help")); title.appendChild(el("small", null, "Answers from our policies, with sources"));
    var close = el("button", "kc-close", "×"); close.type = "button"; close.setAttribute("aria-label", "Close help assistant");
    top.append(title, close);
    var log = el("div", "kc-log"); log.setAttribute("role", "log"); log.setAttribute("aria-live", "polite");
    var form = el("form", "kc-form");
    var input = el("input"); input.type = "text"; input.name = "q"; input.maxLength = 500; input.placeholder = "Type your question"; input.setAttribute("aria-label", "Your question"); input.autocomplete = "off";
    var send = el("button", null, "Send"); send.type = "submit";
    form.append(input, send);
    var foot = el("p", "kc-foot", "AI assistant. It can make mistakes, so check anything important with our team.");
    panel.append(top, log, form, foot);
    document.body.append(launch, panel);

    function add(role, text, sources) {
      var m = el("div", "kc-msg " + (role === "user" ? "kc-user" : "kc-bot"), text);
      if (sources && sources.length) {
        var s = el("div", "kc-src");
        sources.forEach(function (src, i) { s.appendChild(el("span", null, "[" + (i + 1) + "] " + src.file.replace(/\.[a-z]+$/, "").replace(/-/g, " ") + ", " + src.where)); });
        m.appendChild(s);
      }
      log.appendChild(m); log.scrollTop = log.scrollHeight; return m;
    }

    var greeted = false;
    function open() {
      panel.hidden = false; launch.hidden = true; launch.setAttribute("aria-expanded", "true"); input.focus();
      if (!greeted) {
        greeted = true;
        add("bot", "Hi! I can answer questions about returns, warranties, servicing, delivery and our stores.");
        var sg = (host.dataset.suggestions || "").split("|").filter(Boolean);
        if (sg.length) {
          var box = el("div", "kc-suggest");
          sg.forEach(function (q) { var b = el("button", null, q); b.type = "button"; b.addEventListener("click", function () { box.remove(); ask(q); }); box.appendChild(b); });
          log.appendChild(box);
        }
      }
    }
    function shut() { panel.hidden = true; launch.hidden = false; launch.setAttribute("aria-expanded", "false"); launch.focus(); }
    launch.addEventListener("click", open);
    close.addEventListener("click", shut);
    panel.addEventListener("keydown", function (e) { if (e.key === "Escape") shut(); });

    function ask(q) {
      add("user", q);
      var typing = add("bot", "Checking our documents…"); typing.classList.add("kc-typing");
      send.disabled = true; input.disabled = true;
      fetch(api, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: q, history: history }) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          typing.remove();
          if (!res.ok) { add("bot", res.j.error || "Sorry, something went wrong. Please try again."); return; }
          add("bot", res.j.answer, res.j.sources);
          history.push({ role: "user", content: q }, { role: "assistant", content: res.j.answer });
          history = history.slice(-6);
        })
        .catch(function () { typing.remove(); add("bot", "Sorry, I couldn't connect. Please check your connection and try again."); })
        .finally(function () { send.disabled = false; input.disabled = false; input.focus(); });
    }
    form.addEventListener("submit", function (e) { e.preventDefault(); var q = input.value.trim(); if (!q) return; input.value = ""; ask(q); });
  });
})();

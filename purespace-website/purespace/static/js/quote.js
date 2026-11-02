/* Quote form: show the right questions for homes or businesses, and a live guide price.
   The price rules come from the server (pricing.py) so the two can never disagree;
   the server recalculates the estimate itself when the form is sent. */
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("quote-form");
    var dataEl = document.getElementById("pricing-data");
    if (!form || !dataEl) return;
    var P = JSON.parse(dataEl.textContent);
    var service = form.elements.service, freq = form.elements.frequency;
    var out = document.getElementById("est-value"), per = document.getElementById("est-per");
    var allFreq = Array.prototype.slice.call(freq.options);

    function sector() { var c = form.querySelector("input[name=sector]:checked"); return c ? c.value : ""; }
    function num(name) { var v = parseInt(String(form.elements[name].value).replace(/[,\s]/g, ""), 10); return isNaN(v) ? null : v; }
    function round5(x) { return Math.round(x / 5) * 5; }

    function applySector() {
      var s = sector();
      form.querySelectorAll("[data-for]").forEach(function (el) { el.hidden = el.dataset.for !== s; });
      service.querySelectorAll("optgroup").forEach(function (g) { g.hidden = !!s && g.dataset.sector !== s; g.disabled = !!s && g.dataset.sector !== s; });
      var cur = service.selectedOptions[0];
      if (s && cur && cur.dataset.sector && cur.dataset.sector !== s) service.value = "";
      allFreq.forEach(function (o) { var ok = !s || o.dataset.sector === "both" || o.dataset.sector === s; o.hidden = !ok; o.disabled = !ok; });
      if (freq.selectedOptions[0] && freq.selectedOptions[0].disabled) freq.value = "one_off";
      update();
    }

    function update() {
      var s = sector(), svc = service.value, price = null, label = "per visit";
      if (s === "residential" && P.residential[svc]) {
        var r = P.residential[svc];
        price = r[0] + r[1] * (num("bedrooms") || 0) + r[2] * (num("bathrooms") || 0);
      } else if (s === "commercial" && P.commercial[svc]) {
        var c = P.commercial[svc], area = num("floor_area");
        if (area && area >= 100) price = c[0] * Math.max(c[2], area / c[1]);
        else { out.textContent = "Enter the floor area"; per.textContent = "to see a price"; return; }
      }
      if (price === null) { out.textContent = "Choose a clean"; per.textContent = "to see a price"; return; }
      price *= 1 - (P.frequency[freq.value] || 0);
      if (s === "residential") form.querySelectorAll("input[name=extras]:checked").forEach(function (x) { price += P.extras[x.value] || 0; });
      out.textContent = "£" + round5(price * (1 - P.range)) + " to £" + round5(price * (1 + P.range));
      per.textContent = freq.value === "one_off" ? "for this clean" : label;
    }

    form.addEventListener("change", function (e) { if (e.target.name === "sector") applySector(); else update(); });
    form.addEventListener("input", function (e) { if (e.target.name === "floor_area") update(); });
    // Pre-select the sector from a chosen service (links like /quote?service=deep)
    if (!sector() && service.selectedOptions[0] && service.selectedOptions[0].dataset.sector) {
      var r = form.querySelector("input[name=sector][value=" + service.selectedOptions[0].dataset.sector + "]");
      if (r) r.checked = true;
    }
    applySector();
  });
})();

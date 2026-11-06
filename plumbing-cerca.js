(function () {
  var input = document.getElementById("pp-q");
  var status = document.getElementById("pp-status");
  var box = document.getElementById("pp-results");
  var form = document.getElementById("pp-form");
  var pages = [];
  var ready = false;
  var LIMIT = 60;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch];
    });
  }

  function fold(s) {
    return String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function readQuery() {
    try {
      var u = new URL(window.location.href);
      return (u.searchParams.get("q") || "").trim();
    } catch (e) {
      return "";
    }
  }

  function render(q, hits, more) {
    if (!q) {
      box.innerHTML = "";
      status.textContent = pages.length.toLocaleString("it-IT") +
        " pagine indicizzate. Digita almeno 2 lettere.";
      return;
    }
    if (!hits.length) {
      box.innerHTML = "";
      status.textContent = "Nessun risultato per “" + q + "”.";
      return;
    }
    status.textContent = (more
      ? "Prime " + hits.length + " corrispondenze"
      : hits.length + (hits.length === 1 ? " risultato" : " risultati")) +
      " per “" + q + "”.";
    var html = '<ul class="pp-result-list">';
    for (var i = 0; i < hits.length; i++) {
      var p = hits[i];
      html += "<li><a href=\"" + esc(p[0]) + "\">" + esc(p[1] || p[0]) + "</a>";
      if (p[2]) html += '<span class="pp-snippet">' + esc(p[2]) + "</span>";
      html += "</li>";
    }
    html += "</ul>";
    box.innerHTML = html;
  }

  function search(q) {
    if (!ready) return;
    q = (q || "").trim();
    if (q.length < 2) {
      render("", [], false);
      return;
    }
    var nq = fold(q);
    var titleHits = [];
    var extraHits = [];
    for (var i = 0; i < pages.length; i++) {
      var p = pages[i];
      var f = fold(p[0]);
      var t = fold(p[1]);
      if (t.indexOf(nq) !== -1 || f.indexOf(nq) !== -1) {
        titleHits.push(p);
      } else if (fold(p[2]).indexOf(nq) !== -1) {
        extraHits.push(p);
      }
      if (titleHits.length >= LIMIT) break;
    }
    var hits = titleHits.concat(extraHits).slice(0, LIMIT);
    var more = titleHits.length + extraHits.length > LIMIT || titleHits.length >= LIMIT;
    render(q, hits, more);
  }

  fetch("search-index.json")
    .then(function (res) { return res.json(); })
    .then(function (data) {
      pages = data.pages || [];
      ready = true;
      var preset = input.value.trim() || readQuery();
      if (preset) {
        input.value = preset;
        search(preset);
      } else {
        render("", [], false);
      }
    })
    .catch(function () {
      status.textContent = "Indice di ricerca non disponibile in questa copia.";
    });

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = input.value.trim();
    search(q);
    if (history.replaceState) {
      var next = q ? "cerca.htm?q=" + encodeURIComponent(q) : "cerca.htm";
      history.replaceState(null, "", next);
    }
  });

  var timer = null;
  input.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(function () { search(input.value); }, 160);
  });
})();

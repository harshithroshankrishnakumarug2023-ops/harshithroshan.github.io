/* Progressive enhancement only: the site is fully readable without this file. */

(function () {
  "use strict";

  /* --- Mobile navigation ------------------------------------------------ */

  var toggle = document.querySelector(".nav-toggle");
  var navList = document.getElementById("primary-navigation");

  function setMenu(open) {
    if (!toggle || !navList) return;
    navList.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  if (toggle && navList) {
    toggle.addEventListener("click", function () {
      setMenu(toggle.getAttribute("aria-expanded") !== "true");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setMenu(false);
        toggle.focus();
      }
    });

    document.addEventListener("click", function (event) {
      if (!navList.contains(event.target) && !toggle.contains(event.target)) {
        setMenu(false);
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 736) setMenu(false);
    });
  }

  /* --- Document library: search and filters ----------------------------- */

  var filters = document.getElementById("doc-filters");
  if (!filters) return;

  var rows = Array.prototype.slice.call(document.querySelectorAll("[data-doc]"));
  var search = document.getElementById("doc-search");
  var category = document.getElementById("doc-category");
  var year = document.getElementById("doc-year");
  var type = document.getElementById("doc-type");
  var reset = document.getElementById("doc-reset");
  var count = document.getElementById("doc-count");
  var results = document.getElementById("doc-results");

  if (!rows.length || !results) return;

  var empty = document.createElement("p");
  empty.className = "empty-state";
  empty.id = "doc-empty";
  empty.textContent = "No documents match your search.";
  empty.hidden = true;
  results.appendChild(empty);

  function pluralise(number) {
    return number === 1 ? "1 document" : number + " documents";
  }

  function apply() {
    var term = (search.value || "").trim().toLowerCase();
    var wantedCategory = category.value;
    var wantedYear = year.value;
    var wantedType = type.value;
    var visible = 0;

    rows.forEach(function (row) {
      var matches =
        (!term || row.dataset.title.indexOf(term) !== -1) &&
        (!wantedCategory || row.dataset.category === wantedCategory) &&
        (!wantedYear || row.dataset.year === wantedYear) &&
        (!wantedType || row.dataset.type === wantedType);
      row.hidden = !matches;
      if (matches) visible += 1;
    });

    empty.hidden = visible !== 0;
    if (count) {
      count.textContent = pluralise(visible) + (visible === rows.length ? "" : " shown");
    }
  }

  [search, category, year, type].forEach(function (control) {
    control.addEventListener("input", apply);
    control.addEventListener("change", apply);
  });

  if (reset) {
    reset.addEventListener("click", function () {
      search.value = "";
      category.value = "";
      year.value = "";
      type.value = "";
      apply();
      search.focus();
    });
  }

  if (count) {
    count.hidden = false;
    count.textContent = pluralise(rows.length);
  }
})();
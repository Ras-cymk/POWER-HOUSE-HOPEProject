(function () {
  const overlays = document.querySelectorAll(".overlay");

  function closeAll() {
    overlays.forEach((o) => o.classList.remove("open"));
    document.body.style.overflow = "";
  }

  function openModal(name) {
    closeAll();
    const modal = document.getElementById(name + "Modal");
    if (!modal) return;
    modal.classList.add("open");
    document.body.style.overflow = "hidden";
    const first = modal.querySelector("input");
    if (first) first.focus();
  }

  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open]");
    const switcher = e.target.closest("[data-switch]");
    if (opener) openModal(opener.dataset.open);
    if (switcher) {
      e.preventDefault();
      openModal(switcher.dataset.switch);
    }
    if (e.target.closest("[data-close]") || e.target.classList.contains("overlay")) closeAll();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  // The forms are not connected to the backend yet.
  // Replace this handler with a fetch() to the real login/register endpoints.
  document.querySelectorAll("form[data-form]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const note = form.querySelector(".note");
      note.textContent = "This form isn't connected to the backend yet.";
      note.hidden = false;
    });
  });
})();

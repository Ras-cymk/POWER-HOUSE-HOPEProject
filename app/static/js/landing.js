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

  // Register form -> POST /api/register (login is not connected yet)
  document.querySelectorAll("form[data-form]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (form.dataset.form !== "register") return;

      const note = form.querySelector(".note");
      const button = form.querySelector("button[type=submit]");
      const data = Object.fromEntries(new FormData(form));

      button.disabled = true;
      try {
        const response = await fetch("/api/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const result = await response.json();

        note.hidden = false;
        if (result.ok) {
          note.textContent = "Registered. Wait for an admin to approve your account.";
          form.reset();
        } else {
          note.textContent = result.error || "Registration failed.";
        }
      } catch (err) {
        note.hidden = false;
        note.textContent = "Could not reach the server. Please try again.";
      } finally {
        button.disabled = false;
      }
    });
  });
})();
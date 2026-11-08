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

  async function logout() {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (err) {
      // Go back to the landing page either way
    }
    window.location.href = "/";
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
    if (e.target.closest("[data-logout]")) logout();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  // Which API each form posts to, and what to say when it succeeds without a redirect
  const FORMS = {
    register: {
      url: "/api/register",
      success: "Registered. Wait for an admin to approve your account.",
    },
    login: { url: "/api/login", success: "Signed in." },
    "set-password": { url: "/api/set-password", success: "Password saved." },
  };

  document.querySelectorAll("form[data-form]").forEach((form) => {
    const config = FORMS[form.dataset.form];
    if (!config) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const note = form.querySelector(".note");
      const button = form.querySelector("button[type=submit]");
      const data = Object.fromEntries(new FormData(form));

      button.disabled = true;
      try {
        const response = await fetch(config.url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const result = await response.json();

        if (result.ok && result.redirect) {
          window.location.href = result.redirect;
          return;
        }

        note.hidden = false;
        if (result.ok) {
          note.textContent = config.success;
          form.reset();
        } else {
          note.textContent = result.error || "Something went wrong.";
        }
      } catch (err) {
        note.hidden = false;
        note.textContent = "Could not reach the server. Please try again.";
      } finally {
        button.disabled = false;
      }
    });
  });

  // After a logout, a blocked account or the set-password page, send people to the sign-in box
  if (new URLSearchParams(window.location.search).has("signin")) openModal("login");
})();   
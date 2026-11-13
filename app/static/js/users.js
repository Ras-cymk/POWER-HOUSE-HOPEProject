(function () {
  const body = document.getElementById("usersBody");
  if (!body) return; // not the User Management page

  const search = document.getElementById("userSearch");
  const pageNote = document.getElementById("usersNote");
  const empty = document.getElementById("usersEmpty");
  const addModal = document.getElementById("addUserModal");
  const editModal = document.getElementById("editUserModal");
  const addForm = addModal.querySelector("form");
  const editForm = editModal.querySelector("form");

  const ROLE_NAMES = { superadmin: "Superadmin", admin: "Admin", user: "User" };
  const STATUS_NAMES = { active: "Active", pending: "Pending approval" };
  let users = [];

  // All text from the server goes in with textContent, never as HTML.

  function showPageNote(text) {
    pageNote.textContent = text;
    pageNote.hidden = false;
  }

  async function callApi(url, method, data) {
    const options = { method, headers: { "Content-Type": "application/json" } };
    if (data !== undefined) options.body = JSON.stringify(data);
    const response = await fetch(url, options);
    if (response.status === 401) {
      window.location.href = "/?signin=1"; // the session ended
      return { ok: false, error: "Please sign in." };
    }
    return response.json();
  }

  function openModal(modal) {
    modal.classList.add("open");
    document.body.style.overflow = "hidden";
    const first = modal.querySelector("input:not([disabled]):not([type=hidden])");
    if (first) first.focus();
  }

  function closeModal(modal) {
    modal.classList.remove("open");
    document.body.style.overflow = "";
  }

  function cell(text) {
    const td = document.createElement("td");
    td.textContent = text;
    return td;
  }

  function tag(text, extraClass) {
    const span = document.createElement("span");
    span.className = "tag" + (extraClass ? " " + extraClass : "");
    span.textContent = text;
    return span;
  }

  function button(label, onClick) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn btn-outline";
    b.textContent = label;
    b.addEventListener("click", onClick);
    return b;
  }

  function row(u) {
    const tr = document.createElement("tr");
    tr.appendChild(cell(u.first_name + " " + u.last_name + (u.is_self ? " (you)" : "")));
    tr.appendChild(cell(u.email));
    tr.appendChild(cell(ROLE_NAMES[u.role_code] || u.role_code));

    const status = document.createElement("td");
    status.appendChild(tag(STATUS_NAMES[u.account_status] || u.account_status));
    if (u.is_blocked) status.appendChild(tag("Blocked", "tag-blocked"));
    tr.appendChild(status);

    const actions = document.createElement("td");
    actions.className = "users-actions";
    actions.appendChild(button("Edit", () => openEdit(u)));
    if (!u.is_self) actions.appendChild(button(u.is_blocked ? "Unblock" : "Block", () => toggleBlock(u)));
    tr.appendChild(actions);
    return tr;
  }

  function render() {
    const term = search.value.trim().toLowerCase();
    const shown = users.filter((u) =>
      (u.first_name + " " + u.last_name + " " + u.email).toLowerCase().includes(term)
    );
    body.replaceChildren();
    shown.forEach((u) => body.appendChild(row(u)));
    empty.hidden = shown.length > 0;
  }

  async function load() {
    try {
      const result = await callApi("/api/users", "GET");
      if (!result.ok) {
        showPageNote(result.error || "Could not load the users.");
        return;
      }
      users = result.users;
      render();
    } catch (err) {
      showPageNote("Could not reach the server. Please try again.");
    }
  }

  async function toggleBlock(u) {
    const blocking = !u.is_blocked;
    const name = u.first_name + " " + u.last_name;
    if (blocking && !window.confirm("Block " + name + "? They will be signed out right away.")) return;
    try {
      const result = await callApi("/api/users/" + u.user_id + (blocking ? "/block" : "/unblock"), "POST");
      if (!result.ok) {
        showPageNote(result.error || "Something went wrong.");
        return;
      }
      showPageNote(name + (blocking ? " is blocked." : " is unblocked."));
      await load();
    } catch (err) {
      showPageNote("Could not reach the server. Please try again.");
    }
  }

  // Sends a form, shows any error inside the dialog, and calls onSuccess when it worked
  async function submitForm(form, send, onSuccess) {
    const note = form.querySelector(".note");
    const submit = form.querySelector("button[type=submit]");
    submit.disabled = true;
    try {
      const result = await send(Object.fromEntries(new FormData(form)));
      if (result.ok) {
        onSuccess(result);
        await load();
      } else {
        note.hidden = false;
        note.textContent = result.error || "Something went wrong.";
      }
    } catch (err) {
      note.hidden = false;
      note.textContent = "Could not reach the server. Please try again.";
    } finally {
      submit.disabled = false;
    }
  }

  document.getElementById("addUserButton").addEventListener("click", () => {
    addForm.reset();
    addForm.querySelector(".note").hidden = true;
    openModal(addModal);
  });

  addForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(
      addForm,
      (data) => callApi("/api/users", "POST", data),
      (result) => {
        closeModal(addModal);
        showPageNote(
          result.email_configured
            ? "User added. A set-password link was emailed to " + result.user.email + "."
            : "User added. Email is not set up here, so the set-password link was printed in the Flask terminal."
        );
      }
    );
  });

  function openEdit(u) {
    editForm.reset();
    editForm.querySelector(".note").hidden = true;
    editForm.elements.user_id.value = u.user_id;
    editForm.elements.first_name.value = u.first_name;
    editForm.elements.last_name.value = u.last_name;
    document.getElementById("editEmail").value = u.email;
    openModal(editModal);
  }

  editForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(
      editForm,
      (data) =>
        callApi("/api/users/" + data.user_id, "PATCH", {
          first_name: data.first_name,
          last_name: data.last_name,
        }),
      () => {
        closeModal(editModal);
        showPageNote("Changes saved.");
      }
    );
  });

  search.addEventListener("input", render);
  load();
})();

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
  const rightsModal = document.getElementById("rightsModal");
  const rightsForm = document.getElementById("rightsForm");
  const rightsBody = document.getElementById("rightsBody");
  let rightsUserId = null;

  const ROLE_NAMES = { superadmin: "Superadmin", admin: "Admin", user: "User" };
  const STATUS_NAMES = { active: "Active", pending: "Pending approval" };
  let users = [];
  let viewerRole = "";

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

  function button(label, onClick, style) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn " + (style || "btn-outline");
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
    if (u.is_last_superadmin) status.appendChild(tag("Last superadmin"));
    tr.appendChild(status);

    const actions = document.createElement("td");
    actions.className = "users-actions";
    // Approving and choosing admins are superadmin actions. The server checks this again.
    if (viewerRole === "superadmin") {
      if (u.account_status === "pending") {
        actions.appendChild(button("Approve", () => approve(u), "btn-solid"));
      } else if (!u.is_self && (u.role_code === "user" || u.role_code === "admin")) {
        actions.appendChild(
          button(u.role_code === "admin" ? "Remove admin" : "Make admin", () => changeRole(u))
        );
      }
    }
    if (u.can_set_rights) actions.appendChild(button("Rights", () => openRights(u)));
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
      viewerRole = result.viewer_role;
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

  async function approve(u) {
    const name = u.first_name + " " + u.last_name;
    if (!window.confirm("Approve " + name + "? We will email them a link to choose a password.")) return;
    try {
      const result = await callApi("/api/users/" + u.user_id + "/approve", "POST");
      if (!result.ok) {
        showPageNote(result.error || "Something went wrong.");
        return;
      }
      let message = name + " is approved.";
      if (result.link_sent) {
        message += result.email_configured
          ? " A set-password link was emailed to " + result.email + "."
          : " Email is not set up here, so the set-password link was printed in the Flask terminal.";
      }
      showPageNote(message);
      await load();
    } catch (err) {
      showPageNote("Could not reach the server. Please try again.");
    }
  }

  async function changeRole(u) {
    const makeAdmin = u.role_code !== "admin";
    const name = u.first_name + " " + u.last_name;
    const question = makeAdmin
      ? "Make " + name + " an admin? They will be able to manage users."
      : "Remove admin rights from " + name + "? They will become a regular user.";
    if (!window.confirm(question)) return;
    try {
      const result = await callApi("/api/users/" + u.user_id + "/role", "POST", {
        role_code: makeAdmin ? "admin" : "user",
      });
      if (!result.ok) {
        showPageNote(result.error || "Something went wrong.");
        return;
      }
      showPageNote(name + (makeAdmin ? " is now an admin." : " is now a regular user."));
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

  // ---- Rights dialog: five modules, a box per action, a box per module, All and None ----

  function rightsBoxes() {
    return Array.from(rightsBody.querySelectorAll("input[data-perm]"));
  }

  function setAllRights(checked) {
    rightsBoxes().forEach((box) => {
      box.checked = checked;
      box.dispatchEvent(new Event("change")); // keeps each module box and counter in step
    });
  }

  function checkLabel(box, text) {
    const label = document.createElement("label");
    label.className = "rights-check";
    const span = document.createElement("span");
    span.textContent = text;
    label.append(box, span);
    return label;
  }

  function renderRights(modules) {
    rightsBody.replaceChildren();
    modules.forEach((m) => {
      const group = document.createElement("div");
      group.className = "rights-module";

      const head = document.createElement("div");
      head.className = "rights-module-head";
      const moduleBox = document.createElement("input");
      moduleBox.type = "checkbox";
      const count = document.createElement("span");
      count.className = "rights-count";
      head.append(checkLabel(moduleBox, m.module_name), count);

      const grid = document.createElement("div");
      grid.className = "rights-grid";
      const boxes = m.rights.map((r) => {
        const box = document.createElement("input");
        box.type = "checkbox";
        box.value = r.perm_code;
        box.dataset.perm = r.perm_code;
        box.checked = r.granted;
        grid.appendChild(checkLabel(box, r.perm_name));
        return box;
      });

      function sync() {
        const ticked = boxes.filter((b) => b.checked).length;
        moduleBox.checked = boxes.length > 0 && ticked === boxes.length;
        moduleBox.indeterminate = ticked > 0 && ticked < boxes.length;
        count.textContent = ticked + " of " + boxes.length;
      }
      boxes.forEach((b) => b.addEventListener("change", sync));
      moduleBox.addEventListener("change", () => {
        boxes.forEach((b) => {
          b.checked = moduleBox.checked;
        });
        sync();
      });
      sync();

      group.append(head, grid);
      rightsBody.appendChild(group);
    });
  }

  async function openRights(u) {
    try {
      const result = await callApi("/api/users/" + u.user_id + "/rights", "GET");
      if (!result.ok) {
        showPageNote(result.error || "Could not load the rights.");
        return;
      }
      rightsUserId = u.user_id;
      document.getElementById("rightsTitle").textContent =
        "Rights: " + result.user.first_name + " " + result.user.last_name;
      document.getElementById("rightsSub").textContent =
        "Tick what this " + (ROLE_NAMES[result.user.role_code] || "person").toLowerCase() + " may do. Nothing changes until you save.";
      rightsForm.querySelector(".note").hidden = true;
      renderRights(result.modules);
      openModal(rightsModal);
    } catch (err) {
      showPageNote("Could not reach the server. Please try again.");
    }
  }

  document.getElementById("rightsAll").addEventListener("click", () => setAllRights(true));
  document.getElementById("rightsNone").addEventListener("click", () => setAllRights(false));

  rightsForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(
      rightsForm,
      () =>
        callApi("/api/users/" + rightsUserId + "/rights", "PUT", {
          rights: rightsBoxes()
            .filter((box) => box.checked)
            .map((box) => box.value),
        }),
      (result) => {
        closeModal(rightsModal);
        const parts = [];
        if (result.granted) parts.push(result.granted + " added");
        if (result.revoked) parts.push(result.revoked + " removed");
        showPageNote(parts.length ? "Rights saved (" + parts.join(", ") + ")." : "No changes to save.");
      }
    );
  });

  search.addEventListener("input", render);
  load();
})();

# Sprint 1 — UI/UX deliverables (S1-UIX-01 → S1-UIX-04)

Project: POWER-HOUSE HOPE Project — Hope, Inc. ERP
Prepared by: UI/UX Designer · Sprint 1 · November 2026
Figma links: *paste link in the folders below* (exports are committed here so the repo is self-contained)

Everything below is based on the code as it stands in Sprint 1: the tokens in
`app/static/css/landing.css`, the fonts linked in `app/templates/base.html`, the auth flows in
`partials/_auth_modals.html` / `forgot_password.html` / `reset_password.html` / `set_password.html`,
the User Management page (`users.html`, `users.js`) and the roles / modules / rights seed data in
`supabase/migrations/20261102000200_seed_roles_modules_rights.sql` (36 rights · 5 modules).

---

## S1-UIX-01 — Design system (`S1-UIX-01_design-system/`)

| File | Contents |
|---|---|
| `S1-UIX-01_tokens.png` | Color palette (12 tokens, hex + usage — 11 exist in landing.css, `--warn`/`--warn-bg` are new), typography scale (Bricolage Grotesque + IBM Plex Sans), spacing, radii, strokes, focus states |
| `S1-UIX-01_components.png` | Buttons (variants/hover/sizes/disabled), inputs (default/focus/error/disabled), chips (status + roles), checkbox & rights row, table specimen, dialog specimen, proposed sidebar item + dashboard tile |

Done when: devs can implement buttons/inputs/table/dialog from this sheet alone.
Class names match `landing.css`, so the sheets need no code redesign.

## S1-UIX-02 — Wireframes: auth flows (`S1-UIX-02_wireframes-auth/`)

Lo-fi, grayscale, annotated with numbered callouts + states.

| File | Screen / flow |
|---|---|
| `wf-01-login.png` | Landing with sign-in dialog: fields, inline errors, forgot-password and register switches |
| `wf-02-register.png` | Landing with register dialog: name fields, email uniqueness, "pending" hint, success path |
| `wf-03-set-password-flow.png` | First-password flow: admin issues link (script/Add User) → email → set-password form → expired link |
| `wf-04-reset-password-flow.png` | Forgot-password flow: request form → email (30-min link) → choose new password → expired link |

Done when: flows reviewed and approved as input for S1-UIX-04 hi-fi mockups.

## S1-UIX-03 — Wireframes: core screens (`S1-UIX-03_wireframes-core/`)

| File | Screen |
|---|---|
| `wf-01-main-page.png` | Signed-in dashboard for S1-DEV-08: rights-driven sidebar (module table), KPI tiles, recent-activity panel, role variations |
| `wf-02-user-management.png` | User Management list: search, Add User, status/role chips, Edit / Rights / Block / Approve actions, admin-vs-superadmin row rules, empty state |
| `wf-03-rights-dialog.png` | Rights dialog: per-user rights, one group per module, all 36 catalogue rights, "All" shortcut, save rules |

Done when: reviewed and approved; unblocks S1-UIX-04 and S1-DEV-08.

## S1-UIX-04 — Hi-fi mockups (`S1-UIX-04_hifi-mockups/`)

Clean mockups (no annotations) applying the S1-UIX-01 system: teal primary, paper background,
Bricolage Grotesque headings, IBM Plex Sans UI, status chips incl. the new warn tokens.

| File | Screen |
|---|---|
| `hifi-01-login.png` | Sign-in dialog on landing |
| `hifi-02-register.png` | Register dialog on landing |
| `hifi-03-main-page.png` | Dashboard (superadmin view) |
| `hifi-04-user-management.png` | User Management list |
| `hifi-05-rights-dialog.png` | Rights dialog (all 36 rights) |

Done when: devs confirm the mockups are implementable for S1-DEV-03 → DEV-08.

---

### Notes for review

- Wireframes are intentionally grayscale — structure first, then color in hi-fi.
- The **Rights button** on user rows and the **Approve** action on pending rows are new proposals
  this sprint: Rights is required by the rights model already in the DB (`user_permission`);
  Approve is the S1-DEV-06 approval flow surfaced in the UI.
- Tokens `--warn` / `--warn-bg` are the only additions to the palette (used for "Pending approval").
- One task = one PR: `S1-UIX-01`, `S1-UIX-02`, `S1-UIX-03`, `S1-UIX-04` (each folder above maps to one PR).

let ME = null;

// --------- utils ----------
async function api(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || "Ошибка запроса";
    throw new Error(msg);
  }
  return data;
}

function toast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.style.display = "block";
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => (el.style.display = "none"), 2600);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.setAttribute("aria-hidden", "false");
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.setAttribute("aria-hidden", "true");
}

function fillServiceSelect(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "Любая";
  if (selectId === "serviceSelectProfile" || selectId === "serviceSelectAdmin") {
    // в профиле/админке нельзя "Любая"
  } else {
    sel.appendChild(emptyOpt);
  }
  window.SERVICE_TYPES.forEach((t) => {
    const o = document.createElement("option");
    o.value = t;
    o.textContent = t;
    sel.appendChild(o);
  });
}

function setAuthUI() {
  const authBox = document.getElementById("authBox");
  const navProfile = document.getElementById("navProfile");
  const navAdmin = document.getElementById("navAdmin");

  if (!authBox) return;

  if (!ME) {
    authBox.innerHTML = `
      <button class="btn btn--ghost" id="btnOpenLogin">Войти</button>
      <button class="btn" id="btnOpenRegister">Регистрация</button>
    `;
    navProfile && (navProfile.style.display = "none");
    navAdmin && (navAdmin.style.display = "none");

    document.getElementById("btnOpenLogin")?.addEventListener("click", () => openModal("modalLogin"));
    document.getElementById("btnOpenRegister")?.addEventListener("click", () => openModal("modalRegister"));
  } else {
    authBox.innerHTML = `
      <div class="row">
        <span class="muted small">Привет,</span>
        <span class="mono">${ME.login || ""}</span>
        <a class="btn btn--ghost" href="/profile">Профиль</a>
      </div>
    `;
    navProfile && (navProfile.style.display = "inline-block");
    navAdmin && (navAdmin.style.display = ME.is_admin ? "inline-block" : "none");
  }
}

// --------- boot ----------
async function loadMe() {
  const r = await api("/api/auth/me");
  ME = r.user;
  setAuthUI();
}

function bindGlobalModalClose() {
  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.getAttribute("data-close")));
  });
  document.querySelectorAll(".modal").forEach((m) => {
    m.addEventListener("click", (e) => {
      if (e.target === m) m.setAttribute("aria-hidden", "true");
    });
  });
}

function bindAuthForms() {
  const formLogin = document.getElementById("formLogin");
  const formRegister = document.getElementById("formRegister");

  formLogin?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(formLogin);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ login: fd.get("login"), password: fd.get("password") }),
      });
      closeModal("modalLogin");
      await loadMe();
      toast("Вход выполнен");
    } catch (err) {
      toast(err.message);
    }
  });

  formRegister?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(formRegister);
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ login: fd.get("login"), password: fd.get("password") }),
      });
      closeModal("modalRegister");
      await loadMe();
      toast("Аккаунт создан. Заполни анкету в профиле.");
      window.location.href = "/profile";
    } catch (err) {
      toast(err.message);
    }
  });
}

// --------- page: index ----------
let searchPage = 1;

async function loadProfiles(page = 1) {
  const form = document.getElementById("formSearch");
  const results = document.getElementById("results");
  const meta = document.getElementById("resultMeta");
  if (!form || !results) return;

  const fd = new FormData(form);
  const params = new URLSearchParams();
  ["name","service_type","exp_min","exp_max","price_min","price_max"].forEach((k) => {
    const v = (fd.get(k) || "").toString().trim();
    if (v) params.set(k, v);
  });
  params.set("page", String(page));

  const r = await api(`/api/profiles?${params.toString()}`);
  results.innerHTML = "";

  r.items.forEach((p) => {
    const div = document.createElement("div");
    div.className = "profile";
    div.innerHTML = `
      <h3>${escapeHtml(p.name || "Без имени")}</h3>
      <div class="badges">
        <span class="badge">${escapeHtml(p.service_type || "—")}</span>
        <span class="badge">Стаж: ${p.experience_years ?? "—"} лет</span>
        <span class="badge">Цена: ${p.price ?? "—"} ₽</span>
      </div>
      <div class="muted">${escapeHtml(p.about || "Описание не указано.")}</div>
    `;
    results.appendChild(div);
  });

  meta.textContent = `Найдено: ${r.total}. Страница: ${r.page}.`;

  document.getElementById("btnPrev").disabled = !r.has_prev;
  document.getElementById("btnNext").disabled = !r.has_next;

  searchPage = r.page;
}

function bindIndex() {
  const form = document.getElementById("formSearch");
  if (!form) return;

  fillServiceSelect("serviceSelect");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await loadProfiles(1);
    } catch (err) {
      toast(err.message);
    }
  });

  document.getElementById("btnReset")?.addEventListener("click", async () => {
    form.reset();
    try {
      await loadProfiles(1);
    } catch (err) {
      toast(err.message);
    }
  });

  document.getElementById("btnPrev")?.addEventListener("click", () => loadProfiles(searchPage - 1).catch(e => toast(e.message)));
  document.getElementById("btnNext")?.addEventListener("click", () => loadProfiles(searchPage + 1).catch(e => toast(e.message)));

  loadProfiles(1).catch((e) => toast(e.message));
}

// --------- page: profile ----------
async function bindProfile() {
  const form = document.getElementById("formProfile");
  if (!form) return;

  if (!ME) {
    toast("Нужна авторизация");
    openModal("modalLogin");
    return;
  }

  fillServiceSelect("serviceSelectProfile");

  document.getElementById("meLogin").textContent = ME.login || "—";

  // загрузка текущих данных
  form.name.value = ME.name || "";
  document.getElementById("serviceSelectProfile").value = ME.service_type || window.SERVICE_TYPES[0];
  form.experience_years.value = ME.experience_years ?? 0;
  form.price.value = ME.price ?? 1000;
  form.about.value = ME.about || "";
  document.getElementById("chkHidden").checked = !!ME.is_hidden;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: form.name.value,
        service_type: form.service_type.value,
        experience_years: form.experience_years.value,
        price: form.price.value,
        about: form.about.value,
      };
      await api("/api/me/profile", { method: "PUT", body: JSON.stringify(payload) });
      // обновим ME
      await loadMe();
      toast("Сохранено");
    } catch (err) {
      toast(err.message);
    }
  });

  document.getElementById("chkHidden").addEventListener("change", async (e) => {
    try {
      await api("/api/me/hide", { method: "PATCH", body: JSON.stringify({ is_hidden: e.target.checked }) });
      await loadMe();
      toast(e.target.checked ? "Анкета скрыта" : "Анкета видна в поиске");
    } catch (err) {
      toast(err.message);
    }
  });

  document.getElementById("btnLogout")?.addEventListener("click", async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
      ME = null;
      setAuthUI();
      toast("Вы вышли");
      window.location.href = "/";
    } catch (err) {
      toast(err.message);
    }
  });

  document.getElementById("btnDeleteMe")?.addEventListener("click", async () => {
    if (!confirm("Точно удалить аккаунт?")) return;
    try {
      await api("/api/me", { method: "DELETE" });
      ME = null;
      setAuthUI();
      toast("Аккаунт удалён");
      window.location.href = "/";
    } catch (err) {
      toast(err.message);
    }
  });
}

// --------- page: admin ----------
let adminPage = 1;

function renderAdminTable(items) {
  const tbody = document.querySelector("#adminTable tbody");
  tbody.innerHTML = "";
  items.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.id}</td>
      <td class="mono">${escapeHtml(u.login)}</td>
      <td>${escapeHtml(u.name || "")}</td>
      <td>${escapeHtml(u.service_type || "")}</td>
      <td>${u.experience_years ?? ""}</td>
      <td>${u.price ?? ""}</td>
      <td>${u.is_hidden ? "да" : "нет"}</td>
      <td>
        <button class="btn btn--ghost" data-edit="${u.id}">Править</button>
        <button class="btn btn--danger" data-del="${u.id}">Удалить</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadAdminUsers(page = 1) {
  const meta = document.getElementById("adminMeta");
  const r = await api(`/api/admin/users?page=${page}`);
  renderAdminTable(r.items);
  meta.textContent = `Всего: ${r.total}. Страница: ${r.page}.`;

  document.getElementById("btnPrevA").disabled = !r.has_prev;
  document.getElementById("btnNextA").disabled = !r.has_next;
  adminPage = r.page;

  // handlers
  document.querySelectorAll("[data-edit]").forEach((b) => {
    b.addEventListener("click", () => openEditUser(r.items.find(x => x.id == b.getAttribute("data-edit"))));
  });
  document.querySelectorAll("[data-del]").forEach((b) => {
    b.addEventListener("click", () => deleteUser(b.getAttribute("data-del")));
  });
}

function openEditUser(u) {
  fillServiceSelect("serviceSelectAdmin");
  const form = document.getElementById("formEditUser");
  form.id.value = u.id;
  form.name.value = u.name || "";
  document.getElementById("serviceSelectAdmin").value = u.service_type || window.SERVICE_TYPES[0];
  form.experience_years.value = u.experience_years ?? 0;
  form.price.value = u.price ?? 1000;
  form.about.value = u.about || "";
  form.is_hidden.checked = !!u.is_hidden;
  openModal("modalEditUser");
}

async function deleteUser(id) {
  if (!confirm("Удалить пользователя?")) return;
  try {
    await api(`/api/admin/users/${id}`, { method: "DELETE" });
    toast("Удалено");
    await loadAdminUsers(adminPage);
  } catch (err) {
    toast(err.message);
  }
}

async function bindAdmin() {
  const table = document.getElementById("adminTable");
  if (!table) return;

  if (!ME || !ME.is_admin) {
    toast("Нужны права администратора");
    window.location.href = "/";
    return;
  }

  fillServiceSelect("serviceSelectAdmin");

  document.getElementById("btnPrevA")?.addEventListener("click", () => loadAdminUsers(adminPage - 1).catch(e => toast(e.message)));
  document.getElementById("btnNextA")?.addEventListener("click", () => loadAdminUsers(adminPage + 1).catch(e => toast(e.message)));

  const form = document.getElementById("formEditUser");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: form.name.value,
        service_type: form.service_type.value,
        experience_years: form.experience_years.value,
        price: form.price.value,
        about: form.about.value,
        is_hidden: form.is_hidden.checked,
      };
      await api(`/api/admin/users/${form.id.value}`, { method: "PUT", body: JSON.stringify(payload) });
      closeModal("modalEditUser");
      toast("Сохранено");
      await loadAdminUsers(adminPage);
    } catch (err) {
      toast(err.message);
    }
  });

  loadAdminUsers(1).catch((e) => toast(e.message));
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// --------- старт ----------
(async function main() {
  bindGlobalModalClose();
  bindAuthForms();
  fillServiceSelect("serviceSelect");
  fillServiceSelect("serviceSelectProfile");
  fillServiceSelect("serviceSelectAdmin");

  try {
    await loadMe();
  } catch {
    ME = null;
    setAuthUI();
  }

  // инициализация страниц
  bindIndex();
  bindProfile();
  bindAdmin();
})();

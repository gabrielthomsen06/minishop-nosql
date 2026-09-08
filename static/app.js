const state = {
  sessionId: localStorage.getItem("minishop_session_id") || null,
  userId: localStorage.getItem("minishop_user_id") || null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.sessionId) headers["X-Session-Id"] = state.sessionId;

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearSession();
    showLogin("Sessão expirada. Faça login novamente.");
    throw new Error("unauthorized");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

function money(v) {
  return `€ ${Number(v).toFixed(2).replace(".", ",")}`;
}

function saveSession(sessionId, userId) {
  state.sessionId = sessionId;
  state.userId = userId;
  localStorage.setItem("minishop_session_id", sessionId);
  localStorage.setItem("minishop_user_id", userId);
}

function clearSession() {
  state.sessionId = null;
  state.userId = null;
  localStorage.removeItem("minishop_session_id");
  localStorage.removeItem("minishop_user_id");
}

function showLogin(error) {
  $("#loginView").classList.remove("hidden");
  $("#appView").classList.add("hidden");
  $("#userBox").classList.add("hidden");
  const errEl = $("#loginError");
  if (error) {
    errEl.textContent = error;
    errEl.classList.remove("hidden");
  } else {
    errEl.classList.add("hidden");
  }
}

function showApp() {
  $("#loginView").classList.add("hidden");
  $("#appView").classList.remove("hidden");
  $("#userBox").classList.remove("hidden");
  $("#userLabel").textContent = `${state.userId} · sessão ${state.sessionId.slice(0, 12)}…`;
}

// -------------------------
// Tabs
// -------------------------
function initTabs() {
  $$(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".tab").forEach((b) => b.classList.remove("active"));
      $$(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      $(`#tab-${btn.dataset.tab}`).classList.add("active");

      if (btn.dataset.tab === "cart") loadCart();
      if (btn.dataset.tab === "events") loadEvents();
      if (btn.dataset.tab === "metrics") loadMetrics();
    });
  });
}

// -------------------------
// Catálogo / busca
// -------------------------
function productCard(p, onAdd) {
  const div = document.createElement("div");
  div.className = "product-card";
  div.innerHTML = `
    <h3>${p.name}</h3>
    <div class="muted">${p.sku} · ${p.category}</div>
    <div class="price">${p.price_fmt}</div>
    <div class="add-row">
      <input type="number" min="1" value="1" class="qty-input" />
      <button class="btn btn-primary btn-sm add-btn">Adicionar</button>
    </div>
  `;
  div.querySelector(".add-btn").addEventListener("click", () => {
    const qty = parseInt(div.querySelector(".qty-input").value, 10) || 1;
    onAdd(p, qty);
  });
  return div;
}

async function addToCart(product, qty) {
  try {
    await api("/api/cart/add", { method: "POST", body: { sku: product.sku, qty } });
    await refreshCartBadge();
    flash(`${product.name} adicionado ao carrinho.`);
  } catch (e) {
    flash(e.message, true);
  }
}

async function loadCatalog() {
  const products = await api("/api/catalog");
  const grid = $("#catalogGrid");
  grid.innerHTML = "";
  products.forEach((p) => grid.appendChild(productCard(p, addToCart)));
}

async function doSearch(query) {
  const results = await api(`/api/search?q=${encodeURIComponent(query)}`);
  const grid = $("#searchGrid");
  grid.innerHTML = "";
  if (!results.length) {
    grid.innerHTML = '<p class="empty">Nenhum resultado.</p>';
    return;
  }
  results.forEach((p) => grid.appendChild(productCard(p, addToCart)));
}

// -------------------------
// Carrinho
// -------------------------
async function refreshCartBadge() {
  const cart = await api("/api/cart");
  const badge = $("#cartBadge");
  if (cart.count > 0) {
    badge.textContent = cart.count;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
  return cart;
}

async function loadCart() {
  const cart = await refreshCartBadge();
  const wrap = $("#cartTableWrap");
  $("#checkoutMsg").classList.add("hidden");

  if (!cart.items.length) {
    wrap.innerHTML = '<p class="empty">Carrinho vazio.</p>';
    $("#cartTotal").textContent = money(0);
    return;
  }

  const rows = cart.items
    .map(
      (i) => `
      <tr>
        <td>${i.sku}</td>
        <td>${i.name}</td>
        <td>${i.unit_price_fmt}</td>
        <td>${i.qty}</td>
        <td>${i.line_total_fmt}</td>
        <td><button class="btn btn-ghost btn-sm remove-btn" data-sku="${i.sku}">Remover</button></td>
      </tr>`
    )
    .join("");

  wrap.innerHTML = `
    <table class="cart-table">
      <thead>
        <tr><th>SKU</th><th>Produto</th><th>Preço</th><th>Qtd</th><th>Subtotal</th><th></th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
  $("#cartTotal").textContent = cart.total_fmt;

  $$(".remove-btn").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api("/api/cart/remove", { method: "POST", body: { sku: btn.dataset.sku, qty: 1 } });
      loadCart();
    })
  );
}

async function checkout() {
  try {
    const order = await api("/api/checkout", { method: "POST" });
    $("#checkoutMsg").textContent = `Pedido ${order.order_id} concluído! Total ${order.total_fmt}.`;
    $("#checkoutMsg").classList.remove("hidden");
    loadCart();
  } catch (e) {
    flash(e.message, true);
  }
}

// -------------------------
// Eventos
// -------------------------
async function loadEvents() {
  const events = await api("/api/events");
  const list = $("#eventsList");
  list.innerHTML = "";
  if (!events.length) {
    list.innerHTML = '<p class="empty">Nenhum evento ainda.</p>';
    return;
  }
  events
    .slice()
    .reverse()
    .forEach((e) => {
      const div = document.createElement("div");
      div.className = "list-item";
      div.innerHTML = `
        <div class="meta">${new Date(e.ts).toLocaleString()} · <strong>${e.event_type}</strong></div>
        <pre>${JSON.stringify(e.payload, null, 2)}</pre>
      `;
      list.appendChild(div);
    });
}

// -------------------------
// Métricas
// -------------------------
async function loadMetrics() {
  const data = await api("/api/metrics");

  const countersGrid = $("#countersGrid");
  countersGrid.innerHTML = "";
  const counterEntries = Object.entries(data.counters || {});
  if (!counterEntries.length) {
    countersGrid.innerHTML = '<p class="empty">Nenhum contador ainda.</p>';
  } else {
    counterEntries.sort().forEach(([name, value]) => {
      const div = document.createElement("div");
      div.className = "stat-card";
      div.innerHTML = `<div class="value">${value}</div><div class="label">${name}</div>`;
      countersGrid.appendChild(div);
    });
  }

  const pointsList = $("#pointsList");
  pointsList.innerHTML = "";
  if (!data.points.length) {
    pointsList.innerHTML = '<p class="empty">Nenhum ponto de métrica ainda.</p>';
    return;
  }
  data.points.forEach((p) => {
    const div = document.createElement("div");
    div.className = "list-item";
    div.innerHTML = `<div class="meta">${new Date(p.ts).toLocaleString()} · <strong>${p.metric}</strong> = ${p.value.toFixed(2)}</div><pre>${JSON.stringify(p.tags)}</pre>`;
    pointsList.appendChild(div);
  });
}

// -------------------------
// Feedback simples
// -------------------------
function flash(message, isError) {
  const el = document.createElement("div");
  el.textContent = message;
  el.style.position = "fixed";
  el.style.bottom = "20px";
  el.style.right = "20px";
  el.style.background = isError ? "#d64545" : "#1f9d55";
  el.style.color = "#fff";
  el.style.padding = "10px 16px";
  el.style.borderRadius = "8px";
  el.style.fontSize = "0.85rem";
  el.style.boxShadow = "0 2px 8px rgba(0,0,0,0.15)";
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

// -------------------------
// Bootstrap
// -------------------------
async function init() {
  initTabs();

  $("#loginForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const userId = $("#userIdInput").value.trim() || "u123";
    try {
      const data = await api("/api/login", { method: "POST", body: { user_id: userId } });
      saveSession(data.session_id, data.user_id);
      showApp();
      await loadCatalog();
      await refreshCartBadge();
    } catch (e) {
      showLogin(e.message);
    }
  });

  $("#logoutBtn").addEventListener("click", async () => {
    try {
      await api("/api/logout", { method: "POST" });
    } catch (e) {
      /* ignore */
    }
    clearSession();
    showLogin();
  });

  $("#searchForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    doSearch($("#searchInput").value.trim());
  });

  $("#checkoutBtn").addEventListener("click", checkout);
  $("#refreshEvents").addEventListener("click", loadEvents);
  $("#refreshMetrics").addEventListener("click", loadMetrics);

  if (state.sessionId && state.userId) {
    try {
      showApp();
      await loadCatalog();
      await refreshCartBadge();
      return;
    } catch (e) {
      clearSession();
    }
  }
  showLogin();
}

init();

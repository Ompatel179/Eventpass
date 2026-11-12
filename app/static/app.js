// Shared helpers used by every EventPass page.
"use strict";

const TOKEN_KEY = "eventpass_token";
let currentUser = null;

// ---------- Token (per-tab, cleared when the tab closes) ----------
function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

// ---------- Small DOM helpers ----------
function $(id) {
  return document.getElementById(id);
}

function show(id, visible) {
  $(id).classList.toggle("hidden", !visible);
}

// Builds an element safely: text is always added as text, never as HTML.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// ---------- API calls ----------
function goToLogin() {
  const here = location.pathname + location.search;
  location.href = `/?next=${encodeURIComponent(here)}#account`;
}

// Calls our API with the token attached. Pass `json` to send a JSON body.
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const init = { ...options, headers };
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.json);
    delete init.json;
  }
  const response = await fetch(path, init);
  if (response.status === 401 && token) {
    // Token expired (30 min): forget it and send the user to log in again.
    clearToken();
    goToLogin();
    throw new Error("Your session expired. Please log in again.");
  }
  return response;
}

// Turns an API error into a sentence a person can read.
async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      const first = body.detail[0];
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  } catch {
    // Not JSON: fall through to the generic message.
  }
  if (response.status === 429) return "Too many requests. Wait a minute and try again.";
  return `Something went wrong (${response.status}).`;
}

async function logIn(email, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    body: new URLSearchParams({ username: email, password }),
  });
  if (response.status === 429) throw new Error("Too many attempts. Wait a minute and try again.");
  if (!response.ok) throw new Error("Wrong email or password.");
  setToken((await response.json()).access_token);
}

async function signUp(email, password) {
  const response = await fetch("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  await logIn(email, password);
}

function logOut() {
  clearToken();
  location.href = "/";
}

async function loadMe() {
  if (!getToken()) return null;
  try {
    const response = await api("/auth/me");
    currentUser = response.ok ? await response.json() : null;
  } catch {
    currentUser = null;
  }
  return currentUser;
}

function isOrganizer() {
  return currentUser !== null && currentUser.role === "organizer";
}

// Only allow redirects to our own pages ("/organizer"), never "//evil.com".
function safeNext() {
  const next = new URLSearchParams(location.search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return null;
  return next;
}

// Fetches a protected file (QR code, CSV) and returns a temporary local URL for it.
async function fetchBlobUrl(path) {
  const response = await api(path);
  if (!response.ok) throw new Error(await errorMessage(response));
  return URL.createObjectURL(await response.blob());
}

async function downloadFile(path, filename) {
  const url = await fetchBlobUrl(path);
  const link = el("a", { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Times ----------
// "2030-03-01T15:00:00Z" -> "Mar 1, 2030, 10:00 AM" in the viewer's own time zone.
function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function formatDay(iso) {
  return new Date(iso).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function isPast(event) {
  return Date.parse(event.starts_at) < Date.now();
}

// Upcoming events first (soonest first), then past events (most recent first).
function sortEvents(events) {
  return [...events].sort((a, b) => {
    const pastA = isPast(a);
    const pastB = isPast(b);
    if (pastA !== pastB) return pastA ? 1 : -1;
    const diff = Date.parse(a.starts_at) - Date.parse(b.starts_at);
    return pastA ? -diff : diff;
  });
}

// ---------- Toast messages ----------
let toastTimer = null;

function showMessage(text, kind = "ok") {
  let box = $("toast");
  if (!box) {
    box = el("div", { id: "toast", role: "status", "aria-live": "polite" });
    document.body.append(box);
  }
  box.textContent = text;
  box.className = `toast message ${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.className = "hidden"; }, 5000);
}

// ---------- Navigation bar ----------
function renderNav() {
  document.querySelectorAll("[data-auth]").forEach((node) => node.classList.toggle("hidden", !currentUser));
  document.querySelectorAll("[data-organizer]").forEach((node) => node.classList.toggle("hidden", !isOrganizer()));

  const area = $("nav-auth");
  area.replaceChildren();
  if (currentUser) {
    area.append(
      el("span", { class: "nav-user", title: currentUser.email }, currentUser.email),
      el("button", { class: "btn btn-light btn-sm", onclick: logOut }, "Log out"),
    );
  } else {
    area.append(
      el("a", { class: "btn btn-light btn-sm", href: "/#account" }, "Log in"),
      el("a", { class: "btn btn-sm", href: "/#signup" }, "Sign up"),
    );
  }
}

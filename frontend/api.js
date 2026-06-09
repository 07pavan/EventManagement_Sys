/**
 * frontend/api.js — GoAttend Centralized API Client
 *
 * REQUIRES: config.js must be loaded BEFORE this file on every page.
 *   <script src="config.js"></script>
 *   <script src="api.js"></script>
 *
 * ARCHITECTURE:
 * ─────────────────────────────────────────────────────────────────────
 *   config.js    → sets window.GOATTEND_API (the backend base URL)
 *   api.js       → reads it, all fetch calls go through apiFetch()
 *   *.html pages → call the exported functions (login, fetchEvents, etc.)
 *
 * WHY CENTRALIZED:
 *   Every page previously had its own fetch logic scattered inline.
 *   Centralizing means: fix auth bug once → fixed everywhere.
 *   Add a header once → present on all requests.
 *
 * TOKEN STORAGE:
 *   Tokens are stored in localStorage under namespaced keys.
 *   WHY localStorage (not cookies):
 *     - No CSRF risk since the API uses Bearer tokens, not cookies
 *     - Simpler to implement without httpOnly cookie setup
 *     - Accessible across tabs for the same origin
 *   RISK: Vulnerable to XSS. Mitigated by not using eval(), avoiding
 *   innerHTML with user content, and keeping the frontend simple.
 */

// ── API base URL (from config.js) ─────────────────────────────────────────
// Falls back to localhost if config.js was not loaded (safety net only)
const API = window.GOATTEND_API || 'http://127.0.0.1:8001/api';

// Request timeout in milliseconds.
// Render free tier can have slow cold starts — 15s is generous but safe.
const REQUEST_TIMEOUT_MS = 15000;

// ── Token storage (namespaced to avoid collisions) ────────────────────────
const KEYS = {
  token:   'goattend_token',
  refresh: 'goattend_refresh',
  user:    'goattend_user',
  liked:   'goattend_liked',
};

function getToken()    { return localStorage.getItem(KEYS.token); }
function getRefresh()  { return localStorage.getItem(KEYS.refresh); }
function setToken(t)   { localStorage.setItem(KEYS.token, t); }
function setRefresh(t) { localStorage.setItem(KEYS.refresh, t); }
function clearAuth() {
  localStorage.removeItem(KEYS.token);
  localStorage.removeItem(KEYS.refresh);
  localStorage.removeItem(KEYS.user);
}
function getUser()  {
  try { return JSON.parse(localStorage.getItem(KEYS.user)); }
  catch { return null; }
}
function setUser(u) { localStorage.setItem(KEYS.user, JSON.stringify(u)); }
function isLoggedIn() { return !!getToken(); }

// ── Error normalization ───────────────────────────────────────────────────
/**
 * Extracts a human-readable error message from any DRF error shape.
 *
 * DRF returns errors in several formats:
 *   { "detail": "Not found." }
 *   { "email": ["Enter a valid email address."] }
 *   { "non_field_errors": ["Passwords do not match."] }
 *
 * This function collapses all of them into a single string.
 */
function extractErrorMessage(errorBody) {
  if (!errorBody || typeof errorBody !== 'object') return 'An unexpected error occurred.';
  if (typeof errorBody.detail === 'string') return errorBody.detail;
  const messages = [];
  for (const [field, val] of Object.entries(errorBody)) {
    const text = Array.isArray(val) ? val.join(' ') : String(val);
    messages.push(field === 'non_field_errors' ? text : `${field}: ${text}`);
  }
  return messages.join(' | ') || 'An unexpected error occurred.';
}

// ── Silent token refresh ──────────────────────────────────────────────────
/**
 * Attempts to get a new access token using the stored refresh token.
 * Called automatically when a 401 is received.
 *
 * ROTATE_REFRESH_TOKENS=True is set on the backend, so every successful
 * refresh returns a NEW refresh token. We must store it immediately or
 * the user will be logged out on the next refresh attempt.
 *
 * Returns: true if refresh succeeded, false if session is fully expired.
 */
async function tryRefreshToken() {
  const refresh = getRefresh();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API}/auth/token/refresh/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh }),
      signal:  AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!res.ok) {
      clearAuth();
      return false;
    }
    const data = await res.json();
    setToken(data.access);
    // IMPORTANT: store the rotated refresh token immediately
    if (data.refresh) setRefresh(data.refresh);
    return true;
  } catch {
    // Network error or timeout — don't clear auth, let the page handle it
    return false;
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────────────
/**
 * Central request function used by all API calls.
 *
 * Features:
 *  - Injects Authorization: Bearer <token> automatically
 *  - On 401: silently refreshes token and retries once
 *  - On second 401: clears auth and redirects to login
 *  - Normalizes all error responses
 *  - Enforces REQUEST_TIMEOUT_MS timeout on every request
 *  - Handles 204 No Content (returns empty object)
 *
 * @param {string} path    - API path e.g. '/events/'
 * @param {object} opts    - fetch options (method, body, headers, etc.)
 * @param {boolean} _retried - internal flag to prevent infinite refresh loops
 */
async function apiFetch(path, opts = {}, _retried = false) {
  const headers = {
    'Content-Type': 'application/json',
    ...(opts.headers || {}),
  };

  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(API + path, {
      ...opts,
      headers,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (err) {
    // Network failure or timeout — throw a user-friendly error
    if (err.name === 'TimeoutError' || err.name === 'AbortError') {
      throw { detail: 'Request timed out. The server may be starting up — please try again.' };
    }
    throw { detail: 'Cannot reach the server. Check your internet connection.' };
  }

  // ── 401 handling: try silent token refresh ────────────────────────────
  if (res.status === 401 && !_retried) {
    const refreshed = await tryRefreshToken();
    if (refreshed) return apiFetch(path, opts, true);
    clearAuth();
    window.location.href = 'login.html';
    return;
  }

  // ── Parse response ────────────────────────────────────────────────────
  // 204 No Content has no body — return empty object
  let data;
  try {
    data = res.status === 204 ? {} : await res.json();
  } catch {
    // Response was not JSON (e.g., HTML error page from server crash)
    throw { detail: `Server error (HTTP ${res.status}). Please try again later.` };
  }

  if (!res.ok) throw data;
  return data;
}

// ── Multipart upload wrapper (for FormData — images, files) ──────────────
/**
 * Used for file uploads (event images, avatars).
 * DO NOT set Content-Type manually — the browser sets it with the
 * correct multipart boundary when body is a FormData object.
 *
 * Also handles 401 → refresh → retry like apiFetch.
 */
async function apiFetchMultipart(path, method, formData, _retried = false) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers,
      body: formData,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (err) {
    if (err.name === 'TimeoutError' || err.name === 'AbortError') {
      throw { detail: 'Upload timed out. Please try again.' };
    }
    throw { detail: 'Cannot reach the server. Check your internet connection.' };
  }

  if (res.status === 401 && !_retried) {
    const refreshed = await tryRefreshToken();
    if (refreshed) return apiFetchMultipart(path, method, formData, true);
    clearAuth();
    window.location.href = 'login.html';
    return;
  }

  let data;
  try {
    data = res.status === 204 ? {} : await res.json();
  } catch {
    throw { detail: `Server error (HTTP ${res.status}). Please try again later.` };
  }

  if (!res.ok) throw data;
  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────

async function login(username, password) {
  const data = await apiFetch('/auth/token/', {
    method: 'POST',
    body:   JSON.stringify({ username, password }),
  });
  setToken(data.access);
  setRefresh(data.refresh);
  const profile = await apiFetch('/auth/profile/');
  setUser(profile);
  return profile;
}

async function register(payload) {
  return apiFetch('/auth/register/', {
    method: 'POST',
    body:   JSON.stringify(payload),
  });
}

async function logout() {
  const refresh = getRefresh();
  if (refresh) {
    try {
      await apiFetch('/auth/logout/', {
        method: 'POST',
        body:   JSON.stringify({ refresh }),
      });
    } catch {
      // Server-side blacklist failed — still clear locally
      // The access token will expire on its own (2h TTL)
    }
  }
  clearAuth();
  window.location.href = 'login.html';
}

/**
 * Request a password reset email.
 * Sends { email } to POST /api/auth/password-reset/
 * Always resolves (anti-enumeration: backend always returns 200).
 */
async function requestPasswordReset(email) {
  return apiFetch('/auth/password-reset/', {
    method: 'POST',
    body:   JSON.stringify({ email }),
  });
}

/**
 * Confirm a password reset with the token from the email link.
 * Sends { uid, token, new_password } to POST /api/auth/password-reset/confirm/
 * Throws on bad/expired token or weak password.
 */
async function confirmPasswordReset(uid, token, new_password) {
  return apiFetch('/auth/password-reset/confirm/', {
    method: 'POST',
    body:   JSON.stringify({ uid, token, new_password }),
  });
}

async function getSecurityQuestion(email) {
  const qs = new URLSearchParams({ email }).toString();
  return apiFetch(`/auth/security-question/?${qs}`);
}

async function resetPasswordWithQuestion(email, answer, newPassword) {
  return apiFetch('/auth/password-reset-question/', {
    method: 'POST',
    body:   JSON.stringify({ email, security_answer: answer, new_password: newPassword }),
  });
}


/**
 * Update the currently logged-in user's profile.
 * Uses multipart/form-data so the avatar image file can be included.
 * Accepts a FormData object containing any of:
 *   first_name, last_name, bio, avatar (File)
 *
 * After a successful update, refreshes the localStorage cache with the
 * latest profile returned from GET /auth/profile/ so the UI stays in sync.
 */
async function updateProfile(formData) {
  const updated = await apiFetchMultipart('/auth/profile/', 'PATCH', formData);
  // Refresh localStorage cache so pages that read getUser() stay consistent
  setUser(updated);
  return updated;
}

async function changePassword(oldPassword, newPassword) {
  return apiFetch('/auth/change-password/', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}



// ── Events ────────────────────────────────────────────────────────────────

function fetchEvents(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiFetch('/events/' + (qs ? '?' + qs : ''));
}

function fetchEvent(id) {
  return apiFetch(`/events/${id}/`);
}

// ── Event mutations (multipart — supports image uploads) ──────────────────

function createEvent(formData) {
  return apiFetchMultipart('/events/', 'POST', formData);
}

function updateEvent(id, formData) {
  return apiFetchMultipart(`/events/${id}/`, 'PATCH', formData);
}

function deleteEvent(id) {
  return apiFetch(`/events/${id}/`, { method: 'DELETE' });
}

// ── Tickets ───────────────────────────────────────────────────────────────

function purchaseTicket(eventId) {
  return apiFetch('/tickets/purchase/', {
    method: 'POST',
    body:   JSON.stringify({ event: eventId }),
  });
}

function fetchMyTickets() {
  return apiFetch('/user/tickets/');
}

function verifyTicket(ticketHash) {
  return apiFetch('/tickets/verify/', {
    method: 'POST',
    body:   JSON.stringify({ ticket_hash: ticketHash }),
  });
}

// ── Organizer ─────────────────────────────────────────────────────────────

function checkIsOrganizer() {
  return apiFetch('/auth/is-organizer/');
}

function fetchOrganizerEvents(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiFetch('/organizer/events/' + (qs ? '?' + qs : ''));
}

function fetchOrganizerAttendees(eventId) {
  return apiFetch(`/organizer/events/${eventId}/attendees/`);
}

// ── Format helpers ────────────────────────────────────────────────────────

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtPrice(p) {
  return parseFloat(p) === 0 ? 'FREE' : '₹' + parseFloat(p).toFixed(0);
}

function getImageUrl(url) {
  const fallback = typeof PLACEHOLDER !== 'undefined' ? PLACEHOLDER : 'https://lh3.googleusercontent.com/aida-public/AB6AXuBBG0kETVkyKmuooroSqWkqUKcaDZjoUS446cKpcRrRBQoMUtbw8EgGnXqVe8fTqIWuGOHGJQlyx6Y1yoMQ0kM3GNKRnsoU4gQqMVfEswZ7Cp2tyrV2eyiVdN0b3MkbP9p7T7STCiMh_PqsWcYYK0Q55EXcRAtKXe3Rn2-kjEI8unDAKB7ui5SCRNch9rIOJ-6ug1jlhYkMk3mZ9NsRQ3ZdzjOIncfg4JBH1NRg7OMERIGdPX3UljTD8DDXr8otuRPzv6F-6ImKBYo';
  if (!url) return fallback;
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url;
  const backendHost = (window.GOATTEND_API || 'http://127.0.0.1:8001/api').replace(/\/api\/?$/, '');
  const relativePath = url.startsWith('/') ? url : '/' + url;
  return backendHost + relativePath;
}

const CATEGORY_EMOJI = { music: '🎵', tech: '💻', food: '🍜', arts: '🎨' };

// ── Liked Events (client-side only — no backend) ──────────────────────────
// Stores full event objects so liked.html works without a backend refetch.

function getLikedMap()     {
  try { return JSON.parse(localStorage.getItem(KEYS.liked) || '{}'); }
  catch { return {}; }
}
function saveLikedMap(map) { localStorage.setItem(KEYS.liked, JSON.stringify(map)); }
function isLiked(id)       { return !!getLikedMap()[id]; }
function toggleLike(eventObj) {
  const map = getLikedMap();
  const id  = eventObj.id;
  if (map[id]) { delete map[id]; saveLikedMap(map); return false; }
  else         { map[id] = eventObj; saveLikedMap(map); return true; }
}
function getLikedEvents()  { return Object.values(getLikedMap()); }

// ── Debug helper (only in development) ───────────────────────────────────
if (window.GOATTEND_ENV === 'development') {
  window.__goattend = {
    API,
    getToken,
    getUser,
    clearAuth,
    extractErrorMessage,
    // Usage: __goattend.API → shows current backend URL in console
    // Usage: __goattend.getToken() → shows current JWT for debugging
  };
  console.debug('[GoAttend] API client loaded.', { env: window.GOATTEND_ENV, api: API });
}

/**
 * API Client — handles all communication with the backend.
 *
 * KEY CHANGES (Auth System Completion):
 *
 * BEFORE: Access token in localStorage, no refresh, frontend-only logout
 * AFTER:  Access token in memory, auto-refresh on 401, server-side logout
 *
 * All fetch calls now include credentials: "include" so cookies are sent.
 */

const API_BASE = "http://localhost:9000";
const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`;
import { getBrowserTimeZone } from "./date";

// ─── Token Storage (in memory, NOT localStorage) ──────────
// This variable holds the current access token. Only this module can access it.
// On page reload it resets to null — we recover via silentRefresh().
let _accessToken = null;

/**
 * Set the in-memory access token (called after login, refresh, or OAuth callback).
 */
export function setAccessToken(token) {
    _accessToken = token;
}

function getToken() {
    return _accessToken;
}

// ─── Helpers ──────────────────────────────────────────────

function resetThemeOnSignout() {
    if (typeof document !== "undefined") {
        document.documentElement.classList.remove("dark", "theme-switching");
    }
    localStorage.removeItem("theme");
}

function redirectToSigninOnUnauthorized() {
    _accessToken = null;
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    resetThemeOnSignout();
    if (typeof window !== "undefined" && window.location.pathname !== "/sign-in") {
        window.location.replace("/sign-in");
    }
}

function extractErrorMessage(data, fallback) {
    const detail = data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === "string" && first) return first;
        if (first && typeof first.msg === "string" && first.msg) return first.msg;
    }
    if (detail && typeof detail === "object") {
        if (typeof detail.code === "string" && detail.code) return detail.code;
        if (typeof detail.message === "string" && detail.message) return detail.message;
    }
    if (typeof data?.message === "string" && data.message) return data.message;
    return fallback;
}

// ─── Refresh Logic ────────────────────────────────────────
// "Refresh lock" — if multiple API calls fail with 401 at the same time,
// only ONE refresh request is sent. The others wait for it.
let _refreshPromise = null;

/**
 * Try to get a new access token using the HttpOnly cookie.
 * Returns true if successful, false if not.
 */
async function attemptRefresh() {
    if (_refreshPromise) return _refreshPromise;

    _refreshPromise = (async () => {
        try {
            const res = await fetch(`${API_BASE}/auth/refresh`, {
                method: "POST",
                credentials: "include",
                headers: { "X-Timezone": getBrowserTimeZone() },
            });
            if (!res.ok) return false;
            const data = await res.json();
            _accessToken = data.access_token;
            return true;
        } catch {
            return false;
        } finally {
            _refreshPromise = null;
        }
    })();

    return _refreshPromise;
}

/**
 * Silent refresh — called on app startup to restore session after page reload.
 */
export async function silentRefresh() {
    return attemptRefresh();
}

// ─── Core Request Function ────────────────────────────────

async function request(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        "X-Timezone": getBrowserTimeZone(),
        ...(options.headers || {}),
    };

    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
    });

    // If 401 and we haven't retried yet, attempt refresh then retry
    if (res.status === 401 && !options._retried) {
        const refreshed = await attemptRefresh();
        if (refreshed) {
            return request(path, { ...options, _retried: true });
        }
        redirectToSigninOnUnauthorized();
        throw new Error("auth.session_expired");
    }

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        if (res.status === 401) {
            redirectToSigninOnUnauthorized();
        }
        const msg = extractErrorMessage(data, `Request failed: ${res.status}`);
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    return data;
}

// ─── Auth Functions ───────────────────────────────────────

export async function getHealth() {
    return request("/health", { method: "GET" });
}

export async function signin(email, password) {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const res = await fetch(`${API_BASE}/users/sign-in`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Timezone": getBrowserTimeZone(),
        },
        body,
        credentials: "include",
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = extractErrorMessage(data, `Sign-in failed: ${res.status}`);
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    const token = data?.access_token;
    if (!token) throw new Error("Sign-in succeeded but no token returned");

    // Store in memory, clean up legacy localStorage
    _accessToken = token;
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");

    return data;
}

export async function signup(username, email, password) {
    return request("/users/sign-up", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });
}

export async function forgotPassword(email) {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Timezone": getBrowserTimeZone(),
        },
        body: JSON.stringify({ email }),
        credentials: "include",
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = extractErrorMessage(data, `Forgot-password failed: ${res.status}`);
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    return data;
}

export async function resendVerification(email) {
    const res = await fetch(`${API_BASE}/auth/resend-verification`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Timezone": getBrowserTimeZone(),
        },
        body: JSON.stringify({ email }),
        credentials: "include",
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = extractErrorMessage(data, `Resend-verification failed: ${res.status}`);
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    return data;
}

export async function verifyEmail(token) {
    const params = new URLSearchParams({ token });
    const res = await fetch(`${API_BASE}/auth/verify-email?${params.toString()}`, {
        method: "GET",
        headers: { "X-Timezone": getBrowserTimeZone() },
        credentials: "include",
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = extractErrorMessage(data, `Verify-email failed: ${res.status}`);
        throw new Error(msg);
    }

    return data;
}

export async function resetPassword(token, new_password) {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Timezone": getBrowserTimeZone(),
        },
        body: JSON.stringify({ token, new_password }),
        credentials: "include",
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = extractErrorMessage(data, `Reset-password failed: ${res.status}`);
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    return data;
}

/**
 * Logout — calls backend to revoke refresh token, then clears local state.
 */
export async function logout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: "POST",
            credentials: "include",
            headers: { "X-Timezone": getBrowserTimeZone() },
        });
    } catch {
        // Network error is OK — token will expire on its own
    }

    _accessToken = null;
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    resetThemeOnSignout();
}

/**
 * Check if user is logged in (checks memory, not localStorage).
 */
export function isLoggedIn() {
    return !!_accessToken;
}

export function getGoogleLoginUrl() {
    return GOOGLE_LOGIN_URL;
}

// ─── Data Fetching Functions ──────────────────────────────

export async function getCurrentUser() {
    return request("/users/me", { method: "GET" });
}

export async function getBudgets() {
    return request("/budgets/", { method: "GET" });
}

export async function createBudget(category, monthly_limit, budget_year, budget_month) {
    return request("/budgets/", {
        method: "POST",
        body: JSON.stringify({ category, monthly_limit, budget_year, budget_month }),
    });
}

export async function updateBudget(category, monthly_limit, budget_year, budget_month) {
    return request(`/budgets/${encodeURIComponent(budget_year)}/${encodeURIComponent(budget_month)}/${encodeURIComponent(category)}`, {
        method: "PATCH",
        body: JSON.stringify({ monthly_limit }),
    });
}

export async function deleteBudget(category, budget_year, budget_month) {
    return request(`/budgets/${encodeURIComponent(budget_year)}/${encodeURIComponent(budget_month)}/${encodeURIComponent(category)}`, {
        method: "DELETE",
    });
}

export async function getThisMonthStats() {
    return request("/analytics/this-month-stats", { method: "GET" });
}

export async function getCategories() {
    return request("/meta/categories", { method: "GET" });
}

export async function getExpenses(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        searchParams.set(key, String(value));
    });
    const query = searchParams.toString();
    return request(`/expenses${query ? `?${query}` : ""}`, { method: "GET" });
}

export async function deleteExpense(id) {
    return request(`/expenses/${id}`, { method: "DELETE" });
}

export async function createExpense(payload) {
    return request("/expenses/", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function updateExpense(id, payload) {
    return request(`/expenses/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
}

export async function getDailyTrend(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        searchParams.set(key, String(value));
    });
    const query = searchParams.toString();
    return request(`/analytics/daily-trend${query ? `?${query}` : ""}`, { method: "GET" });
}

export async function getAnalyticsHistory() {
    return request("/analytics/history", { method: "GET" });
}

export async function getMonthToDateTrend() {
    return request("/analytics/month-to-date-trend", { method: "GET" });
}

export async function getCategoryBreakdown(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        searchParams.set(key, String(value));
    });
    const query = searchParams.toString();
    return request(`/analytics/category-breakdown${query ? `?${query}` : ""}`, { method: "GET" });
}

export async function exportExpensesCsv(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        searchParams.set(key, String(value));
    });
    const query = searchParams.toString();

    const token = getToken();
    const headers = {
        "X-Timezone": getBrowserTimeZone(),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const res = await fetch(`${API_BASE}/expenses/export${query ? `?${query}` : ""}`, {
        method: "GET",
        headers,
        credentials: "include",
    });

    if (!res.ok) {
        if (res.status === 401) {
            const refreshed = await attemptRefresh();
            if (refreshed) {
                const retryHeaders = {
                    "X-Timezone": getBrowserTimeZone(),
                    Authorization: `Bearer ${_accessToken}`,
                };
                const retryRes = await fetch(`${API_BASE}/expenses/export${query ? `?${query}` : ""}`, {
                    method: "GET",
                    headers: retryHeaders,
                    credentials: "include",
                });
                if (retryRes.ok) {
                    const blob = await retryRes.blob();
                    const contentDisposition = retryRes.headers.get("Content-Disposition") || "";
                    const fileNameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
                    const filename = fileNameMatch?.[1] || "expenses.csv";
                    return { blob, filename };
                }
            }
            redirectToSigninOnUnauthorized();
        }
        const text = await res.text();
        let msg = `Export failed: ${res.status}`;
        if (text) {
            try {
                const data = JSON.parse(text);
                msg = extractErrorMessage(data, msg);
            } catch {
                msg = text;
            }
        }
        const err = new Error(msg);
        err.status = res.status;
        const retryAfter = res.headers.get("Retry-After");
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                err.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        throw err;
    }

    const blob = await res.blob();
    const contentDisposition = res.headers.get("Content-Disposition") || "";
    const fileNameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
    const filename = fileNameMatch?.[1] || "expenses.csv";

    return { blob, filename };
}

const API_BASE = "http://localhost:9000"
const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`
import { getBrowserTimeZone } from "./date";

function getToken() {
    return localStorage.getItem("access_token");
}

function resetThemeOnSignout() {
    if (typeof document !== "undefined") {
        document.documentElement.classList.remove("dark", "theme-switching");
    }
    localStorage.removeItem("theme");
}

function redirectToSigninOnUnauthorized() {
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

export function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    resetThemeOnSignout();
}

async function request(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        "X-Timezone": getBrowserTimeZone(),
        ...(options.headers || {}),
    };

    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    // Try to parse JSON if possible
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
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        if (res.status === 401) {
            redirectToSigninOnUnauthorized();
        }
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

    localStorage.removeItem("token");
    localStorage.setItem("access_token", token);
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
        headers: {
            "X-Timezone": getBrowserTimeZone(),
        },
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


export function isLoggedIn() {
    return !!localStorage.getItem("access_token");
}

export function getGoogleLoginUrl() {
    return GOOGLE_LOGIN_URL;
}

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
    });

    if (!res.ok) {
        if (res.status === 401) {
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

const API_BASE = "http://127.0.0.1:9000"

function getToken() {
    return localStorage.getItem("access_token");
}

function getBrowserTimeZone() {
    try {
        return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    } catch {
        return "UTC";
    }
}

function redirectToSigninOnUnauthorized() {
    localStorage.removeItem("access_token");
    if (typeof window !== "undefined" && window.location.pathname !== "/sign-in") {
        window.location.replace("/sign-in");
    }
}

// function setToken(token) {
//     localStorage.setItem("token", token);
// }

export function logout() {
    localStorage.removeItem("access_token");
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
        const msg = data?.detail || data?.message || `Request failed: ${res.status}`;
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
    // x-www-form-urlencoded (common for FastAPI OAuth2PasswordRequestForm)
    const body = new URLSearchParams();
    body.append("username", email);   // FastAPI often uses "username" even if it's an email
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
        const msg = data?.detail || data?.message || `Sign-in failed: ${res.status}`;
        throw new Error(msg);
    }

    const token = data?.access_token || data?.token;
    if (!token) throw new Error("Sign-in succeeded but no token returned");

    localStorage.setItem("access_token", token);
    return data;
}

export async function signup(username, email, password) {
    return request("/users/sign-up", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });
}


export function isLoggedIn() {
    return !!localStorage.getItem("access_token");
}

export async function getCurrentUser() {
    return request("/users/me", { method: "GET" });
}

export async function getBudgets() {
    return request("/budgets/", { method: "GET" });
}

export async function createBudget(category, monthly_limit) {
    return request("/budgets/", {
        method: "POST",
        body: JSON.stringify({ category, monthly_limit }),
    });
}

export async function updateBudget(category, monthly_limit) {
    return request(`/budgets/${encodeURIComponent(category)}`, {
        method: "PUT",
        body: JSON.stringify({ monthly_limit }),
    });
}

export async function deleteBudget(category) {
    return request(`/budgets/${encodeURIComponent(category)}`, {
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
                msg = data?.detail || data?.message || msg;
            } catch {
                msg = text;
            }
        }
        throw new Error(msg);
    }

    const blob = await res.blob();
    const contentDisposition = res.headers.get("Content-Disposition") || "";
    const fileNameMatch = /filename=\"?([^\";]+)\"?/i.exec(contentDisposition);
    const filename = fileNameMatch?.[1] || "expenses.csv";

    return { blob, filename };
}

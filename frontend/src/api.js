const API_BASE = "https://expense-tracker-s8ma.onrender.com";

function getToken() {
    return localStorage.getItem("token");
}

// function setToken(token) {
//     localStorage.setItem("token", token);
// }

export function logout() {
    localStorage.removeItem("token");
}

async function request(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };

    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    // Try to parse JSON if possible
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = data?.detail || data?.message || `Request failed: ${res.status}`;
        throw new Error(msg);
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
        },
        body,
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const msg = data?.detail || data?.message || `Sign-in failed: ${res.status}`;
        throw new Error(msg);
    }

    const token = data?.access_token || data?.token;
    if (!token) throw new Error("Sign-in succeeded but no token returned");

    localStorage.setItem("token", token);
    return data;
}

export async function signup(username, email, password) {
    return request("/users/sign-up", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });
}


export function isLoggedIn() {
    return !!getToken();
}
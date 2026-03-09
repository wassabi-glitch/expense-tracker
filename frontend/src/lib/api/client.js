import axios from "axios";
import { getBrowserTimeZone } from "../date";

export const API_BASE = "http://localhost:9000";
const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`;

let accessToken = null;
let refreshPromise = null;

function resetThemeOnSignout() {
    if (typeof document !== "undefined") {
        document.documentElement.classList.remove("dark", "theme-switching");
    }
    localStorage.removeItem("theme");
}

function clearLegacyStoredTokens() {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
}

function clearAuthState() {
    accessToken = null;
    clearLegacyStoredTokens();
    resetThemeOnSignout();
}

function redirectToSigninOnUnauthorized() {
    clearAuthState();
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

function toApiError(error) {
    if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const fallback = status ? `Request failed: ${status}` : "Network request failed";
        const message = extractErrorMessage(error.response?.data, fallback);
        const normalized = new Error(message);
        if (status) normalized.status = status;

        const retryAfter = error.response?.headers?.["retry-after"];
        if (retryAfter) {
            const parsed = Number(retryAfter);
            if (Number.isFinite(parsed) && parsed > 0) {
                normalized.retryAfterSeconds = Math.ceil(parsed);
            }
        }
        return normalized;
    }
    return error instanceof Error ? error : new Error("Unexpected API error");
}

async function attemptRefresh() {
    if (refreshPromise) return refreshPromise;

    refreshPromise = (async () => {
        try {
            const response = await rawApiClient.post("/auth/refresh", null, {
                skipAuthRefresh: true,
            });
            const token = response?.data?.access_token;
            if (!token) return false;
            accessToken = token;
            return true;
        } catch {
            return false;
        } finally {
            refreshPromise = null;
        }
    })();

    return refreshPromise;
}

function addTimezoneHeader(config) {
    const next = config;
    const headers = next.headers || {};
    headers["X-Timezone"] = getBrowserTimeZone();
    next.headers = headers;
    return next;
}

export const rawApiClient = axios.create({
    baseURL: API_BASE,
    timeout: 15000,
    withCredentials: true,
});

rawApiClient.interceptors.request.use((config) => addTimezoneHeader(config));
rawApiClient.interceptors.response.use(
    (response) => response,
    (error) => Promise.reject(toApiError(error)),
);

export const apiClient = axios.create({
    baseURL: API_BASE,
    timeout: 15000,
    withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
    const next = addTimezoneHeader(config);
    const headers = next.headers || {};

    if (!next.skipAuthToken && accessToken && !headers.Authorization) {
        headers.Authorization = `Bearer ${accessToken}`;
    }
    next.headers = headers;
    return next;
});

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const status = error?.response?.status;
        const originalRequest = error?.config || {};

        if (status === 401 && !originalRequest._retried && !originalRequest.skipAuthRefresh) {
            originalRequest._retried = true;
            const refreshed = await attemptRefresh();
            if (refreshed) {
                const headers = originalRequest.headers || {};
                if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
                originalRequest.headers = headers;
                return apiClient.request(originalRequest);
            }
            redirectToSigninOnUnauthorized();
        }

        if (status === 401 && !originalRequest.skipAuthRefresh) {
            redirectToSigninOnUnauthorized();
        }

        return Promise.reject(toApiError(error));
    },
);

export function setAccessToken(token) {
    accessToken = token || null;
}

export function getAccessToken() {
    return accessToken;
}

export function clearAuthData() {
    clearAuthState();
}

export function isLoggedIn() {
    return !!accessToken;
}

export async function silentRefresh() {
    return attemptRefresh();
}

export function getGoogleLoginUrl() {
    return GOOGLE_LOGIN_URL;
}

export { toApiError };

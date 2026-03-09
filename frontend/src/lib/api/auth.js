import { clearAuthData, getGoogleLoginUrl, rawApiClient, setAccessToken } from "./client";

export async function signin(email, password) {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const response = await rawApiClient.post("/users/sign-in", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        skipAuthRefresh: true,
    });

    const token = response?.data?.access_token;
    if (!token) throw new Error("Sign-in succeeded but no token returned");

    setAccessToken(token);
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    return response.data;
}

export async function signup(username, email, password) {
    const response = await rawApiClient.post("/users/sign-up", { username, email, password }, { skipAuthRefresh: true });
    return response.data;
}

export async function forgotPassword(email) {
    const response = await rawApiClient.post("/auth/forgot-password", { email }, { skipAuthRefresh: true });
    return response.data;
}

export async function resendVerification(email) {
    const response = await rawApiClient.post("/auth/resend-verification", { email }, { skipAuthRefresh: true });
    return response.data;
}

export async function verifyEmail(token) {
    const response = await rawApiClient.get("/auth/verify-email", {
        params: { token },
        skipAuthRefresh: true,
    });
    return response.data;
}

export async function resetPassword(token, new_password) {
    const response = await rawApiClient.post("/auth/reset-password", { token, new_password }, { skipAuthRefresh: true });
    return response.data;
}

export async function logout() {
    try {
        await rawApiClient.post("/auth/logout", null, { skipAuthRefresh: true });
    } catch {
        // Ignore network/logout errors and clear client auth state anyway.
    }
    clearAuthData();
}

export { getGoogleLoginUrl };

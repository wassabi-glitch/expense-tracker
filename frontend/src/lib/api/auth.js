import { clearAuthData, getGoogleLoginUrl, rawApiClient, apiClient, setAccessToken } from "./client";

export async function signin(email, password) {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const response = await rawApiClient.post("/users/sign-in", body, {
        headers: { 
            "Content-Type": "application/x-www-form-urlencoded",
            "Idempotency-Key": crypto.randomUUID()
        },
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
    const response = await rawApiClient.post("/users/sign-up", 
        { username, email, password }, 
        { 
            skipAuthRefresh: true,
            headers: {
                "Idempotency-Key": crypto.randomUUID()
            }
        }
    );
    return response.data;
}

export async function forgotPassword(email, captchaToken) {
    const payload = { email };
    if (captchaToken) payload.captcha_token = captchaToken;
    const response = await rawApiClient.post("/auth/forgot-password", payload, { 
        skipAuthRefresh: true,
        headers: { "Idempotency-Key": crypto.randomUUID() }
    });
    return response.data;
}

export async function resendVerification(email) {
    const response = await rawApiClient.post("/auth/resend-verification", { email }, { 
        skipAuthRefresh: true,
        headers: { "Idempotency-Key": crypto.randomUUID() }
    });
    return response.data;
}

export async function verifyEmail(token) {
    const response = await rawApiClient.post("/auth/verify-email", { token }, {
        skipAuthRefresh: true,
        headers: { "Idempotency-Key": crypto.randomUUID() }
    });
    return response.data;
}

export async function resetPassword(token, new_password, captchaToken) {
    const payload = { token, new_password };
    if (captchaToken) payload.captcha_token = captchaToken;
    const response = await rawApiClient.post("/auth/reset-password", payload, { 
        skipAuthRefresh: true,
        headers: { "Idempotency-Key": crypto.randomUUID() }
    });
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

export async function logoutAll() {
    try {
        await rawApiClient.post("/auth/logout-all", null, { skipAuthRefresh: true });
    } catch {
        // Ignore network/logout errors and clear client auth state anyway.
    }
    clearAuthData();
}

export async function changePassword(current_password, new_password) {
    const response = await apiClient.post("/auth/change-password", {
        current_password,
        new_password
    }, {
        headers: { "Idempotency-Key": crypto.randomUUID() }
    });
    
    // The backend returns a new access token on success
    const token = response?.data?.access_token;
    if (token) {
        setAccessToken(token);
    }
    
    return response.data;
}

export { getGoogleLoginUrl };

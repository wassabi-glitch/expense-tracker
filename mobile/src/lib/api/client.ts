/* eslint-disable import/no-named-as-default-member */
import axios from 'axios';
import * as Localization from 'expo-localization';
import { getRefreshToken, saveRefreshToken, deleteRefreshToken } from '../auth/secure-store';

export const apiClient = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let accessToken: string | null = null;
let refreshPromise: Promise<{ success: boolean; detail?: string }> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function clearAuthState(errorDetail?: string) {
  accessToken = null;
  deleteRefreshToken().catch(() => {});
  try {
    const { useAuthStore } = require('../features/auth/hooks/use-auth-store');
    useAuthStore.getState().setUnauthenticated();
    if (errorDetail) {
      const { router } = require('expo-router');
      router.replace({ pathname: '/(auth)/sign-in', params: { error: errorDetail } });
    }
  } catch (e) {}
}

async function attemptRefresh() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const refreshToken = await getRefreshToken();
      if (!refreshToken) return { success: false };

      const response = await axios.post(`${process.env.EXPO_PUBLIC_API_URL}/auth/mobile/refresh`, {
        refresh_token: refreshToken
      });
      
      const newAccess = response.data?.access_token;
      const newRefresh = response.data?.refresh_token;
      if (!newAccess || !newRefresh) return { success: false };
      
      accessToken = newAccess;
      await saveRefreshToken(newRefresh);
      return { success: true };
    } catch (error: any) {
      return { success: false, detail: error?.response?.data?.detail };
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

apiClient.interceptors.request.use((config) => {
  const calendars = Localization.getCalendars();
  const timeZone = calendars[0]?.timeZone;
  
  if (timeZone) {
    config.headers['X-Timezone'] = timeZone;
  }
  
  if (accessToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const originalRequest = error?.config || {};

    if (status === 401 && !originalRequest._retried) {
      originalRequest._retried = true;
      const refreshResult = await attemptRefresh();
      if (refreshResult?.success) {
        if (accessToken) originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient.request(originalRequest);
      }
      clearAuthState(refreshResult?.detail);
      // Throw the error with the refresh failure detail so UI can pick it up
      if (refreshResult?.detail) {
        if (error.response && error.response.data) {
          error.response.data.detail = refreshResult.detail;
        }
      }
    }

    // Extract Retry-After header so forms can implement opaque rate-limit handling
    const retryAfter = error.response?.headers?.['retry-after'];
    if (retryAfter) {
      const parsed = Number(retryAfter);
      if (Number.isFinite(parsed) && parsed > 0) {
        (error as any).retryAfterSeconds = Math.ceil(parsed);
      }
    }

    return Promise.reject(error);
  }
);

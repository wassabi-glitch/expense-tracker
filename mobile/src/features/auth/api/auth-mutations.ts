import { useMutation } from '@tanstack/react-query';
import * as Crypto from 'expo-crypto';
import { AxiosError } from 'axios';
import { apiClient } from '@/lib/api/client';
import { SignUpValues } from '../screens/sign-up-screen';

export type SignUpResponse = {
  user: {
    id: string;
    email: string;
    username: string;
  };
  access_token: string;
  token_type: string;
  verification_email_sent: boolean;
};

export function useSignUpMutation() {
  return useMutation<SignUpResponse, AxiosError, SignUpValues>({
    mutationFn: async (credentials) => {
      const response = await apiClient.post<SignUpResponse>('/users/sign-up', credentials, {
        headers: {
          'Idempotency-Key': Crypto.randomUUID()
        }
      });
      return response.data;
    },
  });
}

export function useResendVerificationMutation() {
  return useMutation<void, AxiosError, { email: string }>({
    mutationFn: async ({ email }) => {
      const response = await apiClient.post('/auth/resend-verification', { email }, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export function useVerifyEmailMutation() {
  return useMutation<void, AxiosError, { token: string }>({
    mutationFn: async ({ token }) => {
      const response = await apiClient.post('/auth/verify-email', { token }, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export type NativeSignInResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export function useNativeSignInMutation() {
  return useMutation<NativeSignInResponse, AxiosError, { email: string; password: string }>({
    mutationFn: async (credentials) => {
      const response = await apiClient.post<NativeSignInResponse>('/auth/mobile/sign-in', credentials, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export function useNativeLogoutMutation() {
  return useMutation<void, AxiosError, { refresh_token: string }>({
    mutationFn: async ({ refresh_token }) => {
      const response = await apiClient.post('/auth/mobile/logout', { refresh_token });
      return response.data;
    },
  });
}

export function useNativeLogoutAllMutation() {
  return useMutation<void, AxiosError>({
    mutationFn: async () => {
      const response = await apiClient.post('/auth/logout-all');
      return response.data;
    },
  });
}

export function useForgotPasswordMutation() {
  return useMutation<{ message: string }, AxiosError, { email: string }>({
    mutationFn: async ({ email }) => {
      const response = await apiClient.post('/auth/forgot-password', { email }, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export function useResetPasswordMutation() {
  return useMutation<{ message: string }, AxiosError, { token: string; new_password: string }>({
    mutationFn: async ({ token, new_password }) => {
      const response = await apiClient.post('/auth/reset-password', { token, new_password }, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export function useGoogleNativeAuthMutation() {
  return useMutation<NativeSignInResponse, AxiosError, { id_token: string; nonce?: string }>({
    mutationFn: async (credentials) => {
      const response = await apiClient.post<NativeSignInResponse>('/auth/google/native', credentials, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export function useChangePasswordMutation() {
  return useMutation<NativeSignInResponse, AxiosError, { current_password: string; new_password: string }>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<NativeSignInResponse>('/auth/mobile/change-password', payload, {
        headers: { 'Idempotency-Key': Crypto.randomUUID() }
      });
      return response.data;
    },
  });
}

export type VerifyPasswordResponse = {
  verified: boolean;
};

export function useVerifyPasswordMutation() {
  return useMutation<VerifyPasswordResponse, AxiosError, { password: string }>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<VerifyPasswordResponse>(
        '/auth/verify-password',
        payload,
        {
          headers: { 'Idempotency-Key': Crypto.randomUUID() },
        },
      );
      return response.data;
    },
  });
}

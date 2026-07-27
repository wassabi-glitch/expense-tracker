/* eslint-disable testing-library/no-unnecessary-act */
import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react-native';
import { renderWithProviders } from '../../../../tests/test-utils';
import { ChangePasswordForm } from '../components/change-password-form';
import { apiClient } from '@/lib/api/client';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock('@/lib/api/client', () => ({
  apiClient: {
    post: jest.fn(),
  },
}));

let mockIsRateLimited = false;
const mockOnRateLimitError = jest.fn();
jest.mock('@/hooks/useRateLimitGate', () => ({
  useRateLimitGate: (_opts: { onExpire?: () => void } = {}) => {
    return {
      isRateLimited: mockIsRateLimited,
      onRateLimitError: (error: any) => {
        mockOnRateLimitError(error);
        if (error?.retryAfterSeconds > 0) {
          mockIsRateLimited = true;
        }
      },
    };
  },
}));

describe('ChangePasswordForm Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockIsRateLimited = false;
  });

  afterEach(async () => {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
  });

  it('renders correctly', async () => {
    await renderWithProviders(<ChangePasswordForm />);
    expect(await screen.findByText('settings.changePassword')).toBeTruthy();
    expect(await screen.findByTestId('current-password-input')).toBeTruthy();
    expect(await screen.findByTestId('new-password-input')).toBeTruthy();
    expect(await screen.findByTestId('confirm-password-input')).toBeTruthy();
  });

  it('submits successfully', async () => {
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
      }
    });

    await renderWithProviders(<ChangePasswordForm />);

    await act(async () => {
      const currentInput = await screen.findByTestId('current-password-input');
      const newInput = await screen.findByTestId('new-password-input');
      const confirmInput = await screen.findByTestId('confirm-password-input');

      fireEvent.changeText(currentInput, 'OldPass1!');
      fireEvent.changeText(newInput, 'NewStrong2@');
      fireEvent.changeText(confirmInput, 'NewStrong2@');
    });

    await act(async () => {
      fireEvent.press(screen.getByLabelText('settings.updatePassword'));
    });

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/auth/mobile/change-password', {
        current_password: 'OldPass1!',
        new_password: 'NewStrong2@',
      }, expect.anything());
    });
  });

  it('shows API error on failure', async () => {
    (apiClient.post as jest.Mock).mockRejectedValueOnce({
      response: {
        data: {
          detail: 'auth.incorrect_current_password'
        }
      }
    });

    await renderWithProviders(<ChangePasswordForm />);

    await act(async () => {
      const currentInput = await screen.findByTestId('current-password-input');
      const newInput = await screen.findByTestId('new-password-input');
      const confirmInput = await screen.findByTestId('confirm-password-input');

      fireEvent.changeText(currentInput, 'WrongPass1!');
      fireEvent.changeText(newInput, 'NewStrong2@');
      fireEvent.changeText(confirmInput, 'NewStrong2@');
    });

    await act(async () => {
      fireEvent.press(screen.getByLabelText('settings.updatePassword'));
    });

    await waitFor(() => {
      expect(screen.getByText('auth.incorrect_current_password')).toBeTruthy();
    });
  });

  it('calls onRateLimitError when rate-limited with Retry-After', async () => {
    (apiClient.post as jest.Mock).mockRejectedValueOnce({
      response: {
        data: {
          detail: 'auth.change_password_rate_limited'
        },
        headers: {
          'retry-after': '45'
        }
      },
      retryAfterSeconds: 45
    });

    await renderWithProviders(<ChangePasswordForm />);

    await act(async () => {
      const currentInput = await screen.findByTestId('current-password-input');
      const newInput = await screen.findByTestId('new-password-input');
      const confirmInput = await screen.findByTestId('confirm-password-input');

      fireEvent.changeText(currentInput, 'OldPass1!');
      fireEvent.changeText(newInput, 'NewStrong2@');
      fireEvent.changeText(confirmInput, 'NewStrong2@');
    });

    await act(async () => {
      fireEvent.press(screen.getByLabelText('settings.updatePassword'));
    });

    await waitFor(() => {
      expect(mockOnRateLimitError).toHaveBeenCalled();
      expect(screen.getByText('auth.change_password_rate_limited')).toBeTruthy();
    });
  });
});

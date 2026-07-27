import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Signup from '../Signup';
import * as useAuthMutations from '../hooks/useAuthMutations';

// Mock react-i18next so we just return the translation key
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

// Mock the hook that returns the mutation
vi.mock('../hooks/useAuthMutations', () => ({
  useSignupMutation: vi.fn(),
}));

describe('Signup Logic & Translations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderSignup = () => {
    return render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>
    );
  };

  it('displays auth.signupGlobalRateLimited when backend returns 429 global rate limit', async () => {
    // Setup the mock to simulate a mutation that fails with the specific error string
    const mutateAsyncMock = vi.fn().mockRejectedValue(new Error('auth.signup_global_rate_limited'));
    
    useAuthMutations.useSignupMutation.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
    });

    renderSignup();

    // Fill step 1
    const emailInput = screen.getByPlaceholderText('auth.email');
    const usernameInput = screen.getByPlaceholderText('auth.username');
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser123' } });

    // Click continue
    const continueBtn = screen.getByRole('button', { name: 'auth.continue' });
    fireEvent.click(continueBtn);

    // Wait for step 2 (password input appears)
    await waitFor(() => {
      expect(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder')).toBeInTheDocument();
    });

    // Fill password
    const passwordInput = screen.getByPlaceholderText('auth.createNewPasswordPlaceholder');
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } });

    // Submit the form
    const createBtn = screen.getByRole('button', { name: 'auth.createAccount' });
    fireEvent.click(createBtn);

    // Wait for the mutation to be called and the error text to appear
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalled();
      expect(screen.getByText('auth.signupGlobalRateLimited')).toBeInTheDocument();
    });
  });

  it('displays auth.signupConflict when backend returns 409 conflict', async () => {
    const mutateAsyncMock = vi.fn().mockRejectedValue(new Error('auth.signup_conflict'));
    
    useAuthMutations.useSignupMutation.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
    });

    renderSignup();

    // Fill step 1
    fireEvent.change(screen.getByPlaceholderText('auth.email'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('auth.username'), { target: { value: 'testuser123' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.continue' }));

    // Wait for step 2
    await waitFor(() => {
      expect(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder')).toBeInTheDocument();
    });

    // Submit
    fireEvent.change(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder'), { target: { value: 'StrongPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.createAccount' }));

    // Wait for error text
    await waitFor(() => {
      expect(screen.getByText('auth.signupConflict')).toBeInTheDocument();
    });
  });

  it('displays auth.captchaFailed when backend returns auth.captcha_failed', async () => {
    const mutateAsyncMock = vi.fn().mockRejectedValue(new Error('auth.captcha_failed'));
    
    useAuthMutations.useSignupMutation.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
    });

    renderSignup();

    // Fill step 1
    fireEvent.change(screen.getByPlaceholderText('auth.email'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('auth.username'), { target: { value: 'testuser123' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.continue' }));

    // Wait for step 2
    await waitFor(() => {
      expect(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder')).toBeInTheDocument();
    });

    // Submit
    fireEvent.change(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder'), { target: { value: 'StrongPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.createAccount' }));

    // Wait for error text
    await waitFor(() => {
      expect(screen.getByText('auth.captchaFailed')).toBeInTheDocument();
    });
  });

  it('displays auth.idempotencyConflictInProgress when backend returns auth.idempotency_conflict_in_progress', async () => {
    const mutateAsyncMock = vi.fn().mockRejectedValue(new Error('auth.idempotency_conflict_in_progress'));
    
    useAuthMutations.useSignupMutation.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
    });

    renderSignup();

    // Fill step 1
    fireEvent.change(screen.getByPlaceholderText('auth.email'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('auth.username'), { target: { value: 'testuser123' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.continue' }));

    // Wait for step 2
    await waitFor(() => {
      expect(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder')).toBeInTheDocument();
    });

    // Submit
    fireEvent.change(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder'), { target: { value: 'StrongPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.createAccount' }));

    // Wait for error text
    await waitFor(() => {
      expect(screen.getByText('auth.idempotencyConflictInProgress')).toBeInTheDocument();
    });
  });

  it('displays auth.disposableEmailBlocked when backend returns auth.disposable_email_blocked', async () => {
    const mutateAsyncMock = vi.fn().mockRejectedValue(new Error('auth.disposable_email_blocked'));
    
    useAuthMutations.useSignupMutation.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
    });

    renderSignup();

    // Fill step 1
    fireEvent.change(screen.getByPlaceholderText('auth.email'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('auth.username'), { target: { value: 'testuser123' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.continue' }));

    // Wait for step 2
    await waitFor(() => {
      expect(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder')).toBeInTheDocument();
    });

    // Submit
    fireEvent.change(screen.getByPlaceholderText('auth.createNewPasswordPlaceholder'), { target: { value: 'StrongPass123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'auth.createAccount' }));

    // Wait for error text
    const errorElements = await screen.findAllByText('auth.disposableEmailBlocked');
    expect(errorElements.length).toBeGreaterThan(0);
  });
});


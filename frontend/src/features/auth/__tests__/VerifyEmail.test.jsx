import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import VerifyEmail from "../VerifyEmail";
import { useVerifyEmailMutation } from "../hooks/useAuthMutations";
import { MemoryRouter } from "react-router-dom";

// Mock the hook and its return value
vi.mock("../hooks/useAuthMutations", () => ({
  useVerifyEmailMutation: vi.fn(),
}));

// Mock useTranslation
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

describe("VerifyEmail component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (search = "") => {
    // Mock window.location
    delete window.location;
    window.location = new URL(`http://localhost${search}`);

    return render(
      <MemoryRouter>
        <VerifyEmail />
      </MemoryRouter>
    );
  };

  it("should show missing token error if no token is in URL", async () => {
    const mutateAsync = vi.fn();
    useVerifyEmailMutation.mockReturnValue({ mutateAsync, isPending: false });

    renderComponent();

    // Click verify
    fireEvent.click(screen.getByRole("button", { name: "auth.verifyEmailAction" }));

    // Should not call mutation
    expect(mutateAsync).not.toHaveBeenCalled();

    // Should show error state
    expect(screen.getByText("auth.verifyEmailMissingToken")).toBeInTheDocument();
  });

  it("should show success state when verification succeeds", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ message: "Email verified successfully." });
    useVerifyEmailMutation.mockReturnValue({ mutateAsync, isPending: false });

    renderComponent("?token=valid_token");

    // Click verify
    fireEvent.click(screen.getByRole("button", { name: "auth.verifyEmailAction" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith("valid_token");
    });

    // Should show success state and a Back to Sign In button
    expect(screen.getByText("auth.verifyEmailSuccess")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "auth.backToSignIn" })).toBeInTheDocument();
  });

  it("should show invalid token error if mutation rejects", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("auth.verify_email_token_invalid_or_expired"));
    useVerifyEmailMutation.mockReturnValue({ mutateAsync, isPending: false });

    renderComponent("?token=invalid_token");

    fireEvent.click(screen.getByRole("button", { name: "auth.verifyEmailAction" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith("invalid_token");
    });

    // Should show invalid token text and resend link
    expect(screen.getByText("auth.verifyEmailInvalidToken")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "auth.resendVerificationAction" })).toBeInTheDocument();
  });

  it("should show rate limited error if mutation rejects with rate limit", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("auth.verify_email_rate_limited"));
    useVerifyEmailMutation.mockReturnValue({ mutateAsync, isPending: false });

    renderComponent("?token=valid_token_but_spammed");

    fireEvent.click(screen.getByRole("button", { name: "auth.verifyEmailAction" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith("valid_token_but_spammed");
    });

    // Should show rate limited text
    expect(screen.getByText("auth.verifyEmailRateLimited")).toBeInTheDocument();
  });
});

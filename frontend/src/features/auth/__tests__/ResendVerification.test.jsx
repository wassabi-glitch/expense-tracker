import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { vi } from "vitest";
import ResendVerification from "../ResendVerification";
import { useResendVerificationMutation } from "../hooks/useAuthMutations";
import { MemoryRouter } from "react-router-dom";

vi.mock("../hooks/useAuthMutations", () => ({
  useResendVerificationMutation: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

describe("ResendVerification component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (search = "") => {
    delete window.location;
    window.location = new URL(`http://localhost${search}`);

    return render(
      <MemoryRouter>
        <ResendVerification />
      </MemoryRouter>
    );
  };

  it("shows signup success message when redirected from signup with sent=1", () => {
    useResendVerificationMutation.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    renderComponent("?signup=1&email=test@example.com&sent=1");
    expect(screen.getByText("auth.signupCheckEmail")).toBeInTheDocument();
  });

  it("shows signup failed message as error when redirected from signup with sent=0", () => {
    useResendVerificationMutation.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    renderComponent("?signup=1&email=test@example.com&sent=0");
    expect(screen.getByText("auth.signupEmailFailed")).toBeInTheDocument();
  });



  it("handles successful resend submission", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ message: "verification link sent" });
    useResendVerificationMutation.mockReturnValue({ mutateAsync, isPending: false });
    
    renderComponent();

    const input = screen.getByPlaceholderText("auth.email");
    fireEvent.change(input, { target: { value: "test@example.com" } });
    
    const button = screen.getByRole("button", { name: "auth.resendVerificationAction" });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith("test@example.com");
      expect(screen.getByText("auth.resendVerificationSuccess")).toBeInTheDocument();
    });
    
    // Should trigger cooldown
    expect(screen.getByText(/auth.resendVerificationWait/)).toBeInTheDocument();
  });

  it("handles rate limited API response", async () => {
    const mutateAsync = vi.fn().mockRejectedValue({
      message: "auth.resend_verification_rate_limited",
      retryAfterSeconds: 45
    });
    useResendVerificationMutation.mockReturnValue({ mutateAsync, isPending: false });
    
    renderComponent();

    const input = screen.getByPlaceholderText("auth.email");
    fireEvent.change(input, { target: { value: "test@example.com" } });
    
    fireEvent.click(screen.getByRole("button", { name: "auth.resendVerificationAction" }));

    await waitFor(() => {
      expect(screen.getByText("auth.resendVerificationTooManyWait")).toBeInTheDocument();
    });
  });
});

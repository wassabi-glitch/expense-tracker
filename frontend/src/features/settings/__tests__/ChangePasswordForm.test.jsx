import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ChangePasswordForm } from "../components/ChangePasswordForm";

// Mock the react-i18next hook
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

// Mock the mutation hook
const mockMutateAsync = vi.fn();
vi.mock("../hooks/useSettingsMutations", () => ({
  useChangePasswordMutation: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

// Mock useRateLimitGate — tested separately; here we control isRateLimited
const mockOnRateLimitError = vi.fn();
let mockIsRateLimited = false;
vi.mock("@/hooks/useRateLimitGate", () => ({
  useRateLimitGate: (_opts) => ({
    isRateLimited: mockIsRateLimited,
    onRateLimitError: (...args) => {
      mockOnRateLimitError(...args);
      if (args[0]?.retryAfterSeconds > 0) {
        mockIsRateLimited = true;
      }
    },
  }),
}));

describe("ChangePasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsRateLimited = false;
  });

  it("renders the form fields correctly", () => {
    render(<ChangePasswordForm />);
    expect(screen.getByLabelText("settings.currentPassword")).toBeInTheDocument();
    expect(screen.getByLabelText("settings.newPassword")).toBeInTheDocument();
    expect(screen.getByLabelText("settings.confirmNewPassword")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "settings.updatePassword" })).toBeInTheDocument();
  });

  it("shows validation errors for invalid password", async () => {
    render(<ChangePasswordForm />);
    
    fireEvent.change(screen.getByLabelText("settings.currentPassword"), { target: { value: "old" } });
    fireEvent.change(screen.getByLabelText("settings.newPassword"), { target: { value: "weak" } });
    fireEvent.change(screen.getByLabelText("settings.confirmNewPassword"), { target: { value: "mismatch" } });
    
    fireEvent.click(screen.getByRole("button", { name: "settings.updatePassword" }));
    
    await waitFor(() => {
      expect(screen.getByText("auth.validation.password.min")).toBeInTheDocument();
      expect(screen.getByText("auth.validation.password.mismatch")).toBeInTheDocument();
    });
    
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("submits the form successfully and shows success message", async () => {
    mockMutateAsync.mockResolvedValueOnce({});
    
    render(<ChangePasswordForm />);
    
    fireEvent.change(screen.getByLabelText("settings.currentPassword"), { target: { value: "OldPass1!" } });
    fireEvent.change(screen.getByLabelText("settings.newPassword"), { target: { value: "NewStrong2@" } });
    fireEvent.change(screen.getByLabelText("settings.confirmNewPassword"), { target: { value: "NewStrong2@" } });
    
    fireEvent.click(screen.getByRole("button", { name: "settings.updatePassword" }));
    
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        current_password: "OldPass1!",
        new_password: "NewStrong2@",
      });
      expect(screen.getByText("settings.changePasswordSuccess")).toBeInTheDocument();
    });
  });

  it("shows error when new password is the same as current", async () => {
    render(<ChangePasswordForm />);
    
    fireEvent.change(screen.getByLabelText("settings.currentPassword"), { target: { value: "OldPass1!" } });
    fireEvent.change(screen.getByLabelText("settings.newPassword"), { target: { value: "OldPass1!" } });
    fireEvent.change(screen.getByLabelText("settings.confirmNewPassword"), { target: { value: "OldPass1!" } });
    
    fireEvent.click(screen.getByRole("button", { name: "settings.updatePassword" }));
    
    await waitFor(() => {
      expect(screen.getByText("auth.validation.password.must_differ")).toBeInTheDocument();
    });
    
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("shows API error on failure", async () => {
    mockMutateAsync.mockRejectedValueOnce(new Error("auth.incorrect_current_password"));

    render(<ChangePasswordForm />);

    fireEvent.change(screen.getByLabelText("settings.currentPassword"), { target: { value: "WrongPass1!" } });
    fireEvent.change(screen.getByLabelText("settings.newPassword"), { target: { value: "NewStrong2@" } });
    fireEvent.change(screen.getByLabelText("settings.confirmNewPassword"), { target: { value: "NewStrong2@" } });

    fireEvent.click(screen.getByRole("button", { name: "settings.updatePassword" }));

    await waitFor(() => {
      expect(screen.getByText("auth.incorrect_current_password")).toBeInTheDocument();
    });
  });

  it("disables submit button when rate-limited via Retry-After", async () => {
    const rateLimitError = new Error("auth.change_password_rate_limited");
    rateLimitError.retryAfterSeconds = 60;
    mockMutateAsync.mockRejectedValueOnce(rateLimitError);

    render(<ChangePasswordForm />);

    fireEvent.change(screen.getByLabelText("settings.currentPassword"), { target: { value: "OldPass1!" } });
    fireEvent.change(screen.getByLabelText("settings.newPassword"), { target: { value: "NewStrong2@" } });
    fireEvent.change(screen.getByLabelText("settings.confirmNewPassword"), { target: { value: "NewStrong2@" } });

    fireEvent.click(screen.getByRole("button", { name: "settings.updatePassword" }));

    // Error message should be visible
    await waitFor(() => {
      expect(screen.getByText("auth.change_password_rate_limited")).toBeInTheDocument();
    });

    // onRateLimitError should have been called with the error
    expect(mockOnRateLimitError).toHaveBeenCalledWith(rateLimitError);
  });

});


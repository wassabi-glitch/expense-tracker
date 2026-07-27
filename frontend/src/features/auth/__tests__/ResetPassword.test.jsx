import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ResetPassword from "../ResetPassword";

// Mock i18n
vi.mock("react-i18next", () => ({
    useTranslation: () => ({
        t: (key) => key,
    }),
}));

const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
});

// Mock the hook
vi.mock("../hooks/useAuthMutations", () => ({
    useResetPasswordMutation: vi.fn()
}));

import { useResetPasswordMutation } from "../hooks/useAuthMutations";

function renderWithProviders(ui) {
    return render(
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>{ui}</BrowserRouter>
        </QueryClientProvider>
    );
}

describe("ResetPassword", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.replaceState(null, "", "/reset-password");
    });

    it("renders the form correctly", () => {
        useResetPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: vi.fn() });
        renderWithProviders(<ResetPassword />);
        expect(screen.getByPlaceholderText("auth.newPassword")).toBeInTheDocument();
        expect(screen.getByPlaceholderText("auth.confirmNewPassword")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "auth.savePassword" })).toBeInTheDocument();
    });



    it("shows success state and checkmark on successful reset", async () => {
        window.history.replaceState(null, "", "/reset-password?token=mocktoken");
        const mockMutate = vi.fn().mockResolvedValue({ message: "Password reset successful" });
        useResetPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: mockMutate });

        renderWithProviders(<ResetPassword />);
        
        const newPassInput = screen.getByPlaceholderText("auth.newPassword");
        fireEvent.change(newPassInput, { target: { value: "ValidPass123!" } });

        const confirmPassInput = screen.getByPlaceholderText("auth.confirmNewPassword");
        fireEvent.change(confirmPassInput, { target: { value: "ValidPass123!" } });
        
        const submitBtn = screen.getByRole("button", { name: "auth.savePassword" });
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(mockMutate).toHaveBeenCalledWith({ token: "mocktoken", newPassword: "ValidPass123!", captchaToken: "" });
            expect(screen.getByText("common.success")).toBeInTheDocument();
            expect(screen.getByText("auth.resetPasswordSuccessRedirect")).toBeInTheDocument();
        });
    });

    it("maps backend invalid token error to translation key", async () => {
        window.history.replaceState(null, "", "/reset-password?token=mocktoken");
        const mockMutate = vi.fn().mockRejectedValue(new Error("auth.reset_token_invalid_or_expired"));
        useResetPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: mockMutate });

        renderWithProviders(<ResetPassword />);
        
        fireEvent.change(screen.getByPlaceholderText("auth.newPassword"), { target: { value: "ValidPass123!" } });
        fireEvent.change(screen.getByPlaceholderText("auth.confirmNewPassword"), { target: { value: "ValidPass123!" } });
        fireEvent.click(screen.getByRole("button", { name: "auth.savePassword" }));

        await waitFor(() => {
            expect(screen.getByText("auth.resetPasswordInvalidToken")).toBeInTheDocument();
            expect(screen.getByText("auth.verifyEmailErrorTitle")).toBeInTheDocument();
            expect(screen.getByRole("button", { name: "auth.requestNewResetLink" })).toBeInTheDocument();
        });
    });
});

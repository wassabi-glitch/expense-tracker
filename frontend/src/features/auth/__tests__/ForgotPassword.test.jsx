import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ForgotPassword from "../ForgotPassword";

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
    useForgotPasswordMutation: vi.fn()
}));

import { useForgotPasswordMutation } from "../hooks/useAuthMutations";

function renderWithProviders(ui) {
    return render(
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>{ui}</BrowserRouter>
        </QueryClientProvider>
    );
}

describe("ForgotPassword", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.replaceState(null, "", "/forgot-password");
    });

    it("renders the form correctly", () => {
        useForgotPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: vi.fn() });
        renderWithProviders(<ForgotPassword />);
        expect(screen.getByPlaceholderText("auth.email")).toBeInTheDocument();
        expect(screen.getByText("auth.sendResetLink")).toBeInTheDocument();
    });

    it("extracts ?email parameter from URL and pre-fills the input", () => {
        useForgotPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: vi.fn() });
        window.history.replaceState(null, "", "/forgot-password?email=test%40example.com");
        renderWithProviders(<ForgotPassword />);
        expect(screen.getByPlaceholderText("auth.email")).toHaveValue("test@example.com");
    });

    it("shows the success state with checkmark on successful submission", async () => {
        const mockMutate = vi.fn().mockResolvedValue({ message: "check your email inbox" });
        useForgotPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: mockMutate });

        renderWithProviders(<ForgotPassword />);
        
        const input = screen.getByPlaceholderText("auth.email");
        fireEvent.change(input, { target: { value: "test@example.com" } });
        
        const submitBtn = screen.getByRole("button", { name: "auth.sendResetLink" });
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(mockMutate).toHaveBeenCalledWith({ email: "test@example.com", captchaToken: "" });
            expect(screen.getByText("common.success")).toBeInTheDocument();
            expect(screen.getByText("auth.forgotPasswordSuccess")).toBeInTheDocument();
            expect(screen.queryByPlaceholderText("auth.email")).not.toBeInTheDocument();
        });
    });

    it("displays error on rate limit", async () => {
        const mockMutate = vi.fn().mockRejectedValue(new Error("auth.forgot_password_rate_limited"));
        useForgotPasswordMutation.mockReturnValue({ isPending: false, mutateAsync: mockMutate });

        renderWithProviders(<ForgotPassword />);
        
        const input = screen.getByPlaceholderText("auth.email");
        fireEvent.change(input, { target: { value: "test@example.com" } });
        
        const submitBtn = screen.getByRole("button", { name: "auth.sendResetLink" });
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(screen.getByText("auth.forgotPasswordTooManyRequests")).toBeInTheDocument();
        });
    });
});

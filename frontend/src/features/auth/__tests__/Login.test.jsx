import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Login from "../Login";

// Mock i18n
vi.mock("react-i18next", () => ({
    useTranslation: () => ({
        t: (key) => key,
    }),
}));

const queryClient = new QueryClient();

function renderWithProviders(ui) {
    return render(
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>{ui}</BrowserRouter>
        </QueryClientProvider>
    );
}

describe("Login", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.replaceState(null, "", "/sign-in");
    });

    it("extracts ?error parameter from URL and displays it", () => {
        window.history.replaceState(null, "", "/sign-in?error=auth.refresh_token_invalid");
        renderWithProviders(<Login />);
        expect(screen.getByText("auth.refresh_token_invalid")).toBeInTheDocument();
    });
});

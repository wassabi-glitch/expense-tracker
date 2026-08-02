import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "../Layout";
import * as storeModule from "@/lib/store";
import * as apiModule from "@/lib/api";

// Mock i18n
vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key) => key,
      i18n: { changeLanguage: vi.fn(), language: "en" }
    }),
    initReactI18next: {
      type: "3rdParty",
      init: vi.fn(),
    }
  };
});

// Mock NotificationBell
vi.mock("@/components/NotificationBell", () => ({
  NotificationBell: () => <div data-testid="notification-bell">Bell</div>,
}));

// Mock matchMedia for Dark Mode
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

const queryClient = new QueryClient();

function renderWithProviders(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe("Layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock user
    vi.spyOn(apiModule, "getCurrentUser").mockResolvedValue({
      id: 1,
      email: "test@example.com",
      username: "testuser",
      timezone: "UTC",
    });

    // Mock store
    vi.spyOn(storeModule, "useSidebarStore").mockImplementation(() => ({
      isPinned: true,
      togglePin: vi.fn(),
    }));
  });

  it("renders main navigation items with translated labels", async () => {
    renderWithProviders(<Layout />);
    
    // Wait for the desktop sidebar elements (since mobile hides it via classes but jsdom doesn't process CSS display)
    // The NavList renders nav.dashboard
    const dashboardLinks = await screen.findAllByText("nav.dashboard");
    expect(dashboardLinks.length).toBeGreaterThan(0);
    
    const walletsLinks = screen.getAllByText("nav.wallets");
    expect(walletsLinks.length).toBeGreaterThan(0);
    
    const incomeLinks = screen.getAllByText("nav.income");
    expect(incomeLinks.length).toBeGreaterThan(0);
  });

  it("fetches and displays the current user profile in the header dropdown", async () => {
    renderWithProviders(<Layout />);
    
    // Header triggers the dropdown via user icon
    const userDropdownButtons = await screen.findAllByRole("button", { name: "" }); // The button wrapping the <User /> icon has no name
    // We can find the text via DOM since jsdom renders the dropdown content (or we need to click it if Radix UI hides it)
    
    // Radix dropdowns usually hide content until clicked. Let's find the trigger by its class or just click the user avatar.
    // The button has a child with class `bg-muted`
    const avatar = document.querySelector(".rounded-full.border.bg-muted");
    expect(avatar).toBeInTheDocument();
    
    // Click the avatar to open the dropdown
    fireEvent.pointerDown(avatar.parentElement);
    
    // Now check for user data
    await waitFor(() => {
      expect(screen.getByText("testuser")).toBeInTheDocument();
      expect(screen.getByText("test@example.com")).toBeInTheDocument();
    });
  });

  it("handles dark mode toggle clicks", async () => {
    renderWithProviders(<Layout />);
    
    // Find the toggle button (it has a sun/moon icon)
    // Wait for render
    await screen.findAllByText("nav.dashboard");
    
    // Find button by clicking it
    const toggleButtons = document.querySelectorAll("button");
    const toggleButton = Array.from(toggleButtons).find(b => b.querySelector("svg.lucide-sun") || b.querySelector("svg.lucide-moon"));
    expect(toggleButton).toBeInTheDocument();
    
    fireEvent.click(toggleButton);
    
    // Component should toggle to dark mode
    await waitFor(() => {
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });
  });
});

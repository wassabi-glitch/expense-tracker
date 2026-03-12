/**
 * App.jsx — Root component with silent refresh on mount.
 *
 * On page reload, the in-memory access token is gone. silentRefresh()
 * uses the HttpOnly cookie to get a new one. The app shows nothing
 * until this completes, preventing a flash of the login page.
 */
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Routes, Route, Navigate } from "react-router-dom";
import { silentRefresh } from "@/lib/api";
import { AuthContext } from "@/lib/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import OnboardingGate from "@/components/OnboardingGate";
import Layout from "@/components/Layout";
import NotFound from "@/components/NotFound";
import Login from "@/features/auth/Login";
import Signup from "@/features/auth/Signup";
import AuthCallback from "@/features/auth/AuthCallback";
import ForgotPassword from "@/features/auth/ForgotPassword";
import ResetPassword from "@/features/auth/ResetPassword";
import VerifyEmail from "@/features/auth/VerifyEmail";
import ResendVerification from "@/features/auth/ResendVerification";
import Dashboard from "@/features/dashboard/Dashboard";
import Expenses from "@/features/expenses/Expenses";
import Income from "@/features/income/Income";
import Budgets from "@/features/budgets/Budgets";
import Analytics from "@/features/analytics/Analytics";
import ExportPage from "@/features/expenses/ExportPage";
import Settings from "@/features/settings/Settings";
import Onboarding from "@/features/onboarding/Onboarding";

export default function App() {
  const authBootstrapQuery = useQuery({
    queryKey: ["auth", "silent-refresh"],
    queryFn: silentRefresh,
    retry: false,
    staleTime: Infinity,
    gcTime: Infinity,
  });

  useEffect(() => {
    if (!authBootstrapQuery.isPending) {
      localStorage.removeItem("token");
      localStorage.removeItem("access_token");
    }
  }, [authBootstrapQuery.isPending]);

  const authReady = !authBootstrapQuery.isPending;
  if (!authReady) return null;

  return (
    <AuthContext.Provider value={{ authReady }}>
      <Routes>
        <Route path="/" element={<Navigate to="/sign-in" replace />} />
        <Route path="/sign-in" element={<Login />} />
        <Route path="/sign-up" element={<Signup />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/resend-verification" element={<ResendVerification />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<OnboardingGate />}>
            <Route path="/onboarding" element={<Onboarding />} />
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/expenses" element={<Expenses />} />
              <Route path="/income" element={<Income />} />
              <Route path="/budgets" element={<Budgets />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/export" element={<ExportPage />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AuthContext.Provider>
  );
}

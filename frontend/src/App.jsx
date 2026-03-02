import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { getHealth } from "@/lib/api";
import ProtectedRoute from "@/components/ProtectedRoute";
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
import Budgets from "@/features/budgets/Budgets";
import Analytics from "@/features/analytics/Analytics";
import ExportPage from "@/features/expenses/ExportPage";
import Settings from "@/features/settings/Settings";

export default function App() {
  const [_status, setStatus] = useState("loading...");
  const [_error, setError] = useState("");

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(`${data.status} / ${data.database}`))
      .catch((e) => {
        setStatus("error");
        setError(e.message || "Something went wrong");
      });
  }, []);

  return (
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
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

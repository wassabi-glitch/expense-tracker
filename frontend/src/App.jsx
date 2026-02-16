import { useEffect, useState } from "react";
import { getHealth } from "./api";
import Login from "./Login";
import { Routes, Route, Navigate } from "react-router-dom";
import Signup from "./Signup";
import ProtectedRoute from "./ProtectedRoute";
import Dashboard from "./Dashboard";
import Layout from "./Layout";
import Expenses from "./Expenses";
import Budgets from "./Budgets";
import Analytics from "./Analytics";
import ExportPage from "./ExportPage";
import Settings from "./Settings";
import NotFound from "./NotFound";

export default function App() {
  const [status, setStatus] = useState("loading...");
  const [error, setError] = useState("");

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

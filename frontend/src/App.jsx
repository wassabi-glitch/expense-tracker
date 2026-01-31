import { useEffect, useState } from "react";
import { getHealth } from "./api";
import Login from "./Login";
import { Routes, Route, Navigate } from "react-router-dom";
import Signup from "./Signup";

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
    </Routes>
  );
}

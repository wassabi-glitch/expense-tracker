import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

export default function AuthCallback() {
  const navigate = useNavigate();
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    handledRef.current = true;

    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;

    const hashParams = new URLSearchParams(hash);
    const queryParams = new URLSearchParams(window.location.search);

    const token =
      hashParams.get("token") ||
      hashParams.get("access_token") ||
      queryParams.get("token") ||
      queryParams.get("access_token");

    if (token) {
      localStorage.removeItem("token");
      localStorage.setItem("access_token", token);
      navigate("/dashboard", { replace: true });
      return;
    }

    if (localStorage.getItem("access_token")) {
      navigate("/dashboard", { replace: true });
      return;
    }

    navigate("/sign-in", { replace: true });
  }, [navigate]);

  return null;
}

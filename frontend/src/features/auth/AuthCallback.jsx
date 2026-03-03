/**
 * AuthCallback — handles redirect from Google OAuth.
 * Stores the access token from the URL hash into memory (not localStorage).
 * The refresh token cookie is already set by the backend during the redirect.
 */
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { setAccessToken } from "@/lib/api";

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
      // Store in memory (not localStorage)
      setAccessToken(token);
      localStorage.removeItem("token");
      localStorage.removeItem("access_token");
      navigate("/dashboard", { replace: true });
      return;
    }

    navigate("/sign-in", { replace: true });
  }, [navigate]);

  return null;
}

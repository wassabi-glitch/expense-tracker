import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AuthCallback() {
    const navigate = useNavigate();

    useEffect(() => {
        const hash = new URLSearchParams(window.location.hash.replace("#", ""));
        const token = hash.get("token");
        if (token) {
            localStorage.setItem("access_token", token);
            navigate("/dashboard", { replace: true });
        } else {
            navigate("/sign-in", { replace: true });
        }
    }, [navigate]);

    return null;
}

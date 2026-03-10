import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCurrentUser } from "@/lib/api";

export default function OnboardingGate() {
    const location = useLocation();
    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });

    if (userQuery.isPending) return null;
    if (userQuery.isError) return <Outlet />;

    const needsOnboarding = !!userQuery.data?.needs_onboarding;
    const isOnboardingRoute = location.pathname === "/onboarding";

    if (needsOnboarding && !isOnboardingRoute) {
        return <Navigate to="/onboarding" replace />;
    }

    if (!needsOnboarding && isOnboardingRoute) {
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
}

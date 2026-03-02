// src/components/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';

const ProtectedRoute = () => {
    // 1. Check if the user is authenticated
    // (For MVP, we check if a token exists in localStorage)
    const isAuthenticated = localStorage.getItem('access_token');

    // 2. If no token, redirect to Login
    if (!isAuthenticated) {
        return <Navigate to="/sign-in" replace />;
    }

    // 3. If token exists, render the child route (The Dashboard)
    return <Outlet />;
};

export default ProtectedRoute;
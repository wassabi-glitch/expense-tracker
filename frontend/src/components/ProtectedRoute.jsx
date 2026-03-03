/**
 * ProtectedRoute — guards authenticated routes.
 * Checks the in-memory token via isLoggedIn() instead of localStorage.
 * App.jsx ensures silentRefresh() completes before this runs.
 */
import { Navigate, Outlet } from 'react-router-dom';
import { isLoggedIn } from '@/lib/api';

const ProtectedRoute = () => {
    if (!isLoggedIn()) {
        return <Navigate to="/sign-in" replace />;
    }
    return <Outlet />;
};

export default ProtectedRoute;
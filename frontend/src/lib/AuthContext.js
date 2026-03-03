import { createContext } from "react";

/**
 * AuthContext — shared by App.jsx and ProtectedRoute.
 * Separated from App.jsx to satisfy react-refresh
 * (fast refresh requires component files to only export components).
 */
export const AuthContext = createContext({ authReady: false });

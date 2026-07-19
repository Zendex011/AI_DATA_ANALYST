import { createContext, useContext, useState, useCallback } from "react";
import { api, setAuthToken, ApiError } from "../api/client";

const AuthContext = createContext(null);

const STORAGE_KEY = "ai_data_analyst_token";
const EMAIL_STORAGE_KEY = "ai_data_analyst_email";

export function AuthProvider({ children }) {
  const initialToken = localStorage.getItem(STORAGE_KEY);
  // Set synchronously at module init, not in a useEffect -- a useEffect
  // here would run AFTER children mount, so a child's own mount-time fetch
  // (Dashboard loading /files and /databases) can fire before the token is
  // set, sending an unauthenticated request right after login/signup. See
  // persist()/logout() below for the same reasoning.
  setAuthToken(initialToken);

  const [token, setToken] = useState(initialToken);
  const [email, setEmail] = useState(() => localStorage.getItem(EMAIL_STORAGE_KEY));

  const persist = useCallback((newToken, newEmail) => {
    localStorage.setItem(STORAGE_KEY, newToken);
    localStorage.setItem(EMAIL_STORAGE_KEY, newEmail);
    setAuthToken(newToken); // synchronous -- must happen before any child re-renders and fetches
    setToken(newToken);
    setEmail(newEmail);
  }, []);

  const signup = useCallback(
    async (signupEmail, password) => {
      const data = await api.signup(signupEmail, password);
      persist(data.access_token, signupEmail);
    },
    [persist]
  );

  const login = useCallback(
    async (loginEmail, password) => {
      const data = await api.login(loginEmail, password);
      persist(data.access_token, loginEmail);
    },
    [persist]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(EMAIL_STORAGE_KEY);
    setAuthToken(null);
    setToken(null);
    setEmail(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, email, isAuthenticated: !!token, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { ApiError };

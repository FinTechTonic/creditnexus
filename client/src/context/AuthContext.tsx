import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { resolveApiUrl } from '@/utils/apiBase';

interface User {
  id: number;
  email: string;
  display_name: string;
  profile_image: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

interface Organization {
  id: number;
  name: string;
  slug: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

interface Implementation {
  id: number;
  name: string;
  display_name: string;
  category: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  organization?: Organization | null;
  implementations?: Implementation[] | null;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  display_name: string;
  organization_identifier?: string;  // Organization alias, blockchain address, or key
  organization_id?: number;  // FK to organizations.id
  implementation_ids?: number[];  // Implementation selection (multi-select)
  consents?: Record<string, boolean>;
}

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  implementations: Implementation[];
  isLoading: boolean;
  isAuthenticated: boolean;
  authError: string | null;
  login: (credentials: LoginCredentials) => Promise<boolean>;
  register: (data: RegisterData) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const TOKEN_KEY = 'creditnexus_access_token';
const REFRESH_TOKEN_KEY = 'creditnexus_refresh_token';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getStoredToken();
  const headers = new Headers(options.headers);
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const response = await fetch(resolveApiUrl(url), { ...options, headers });

  return response;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [implementations, setImplementations] = useState<Implementation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const refreshUser = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setOrganization(null);
      setImplementations([]);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetchWithAuth('/api/auth/me');
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated && data.user) {
          setUser(data.user);
          setOrganization(data.organization ?? null);
          setImplementations(Array.isArray(data.implementations) ? data.implementations : []);
        } else {
          setUser(null);
          setOrganization(null);
          setImplementations([]);
          clearTokens();
        }
      } else if (response.status === 401) {
        const refreshToken = getStoredRefreshToken();
        if (refreshToken) {
          const refreshed = await refreshTokens(refreshToken);
          if (refreshed) {
            await refreshUser();
            return;
          }
        }
        setUser(null);
        setOrganization(null);
        setImplementations([]);
        clearTokens();
      } else {
        setUser(null);
        setOrganization(null);
        setImplementations([]);
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      setUser(null);
      setOrganization(null);
      setImplementations([]);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshTokens = async (refreshToken: string): Promise<boolean> => {
    try {
      const response = await fetch(resolveApiUrl('/api/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const tokens: AuthTokens = await response.json();
        storeTokens(tokens);
        return true;
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
    }
    return false;
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<boolean> => {
    setAuthError(null);
    try {
      const response = await fetch(resolveApiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });

      if (response.ok) {
        const tokens: AuthTokens = await response.json();
        storeTokens(tokens);
        // Store organization and implementations from TokenResponse
        if (tokens.organization !== undefined) {
          setOrganization(tokens.organization);
        }
        if (tokens.implementations !== undefined) {
          setImplementations(Array.isArray(tokens.implementations) ? tokens.implementations : []);
        }
        await refreshUser();
        return true;
      } else {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        // Handle Pydantic validation errors (422)
        if (response.status === 422 && error.detail) {
          if (Array.isArray(error.detail)) {
            // Pydantic validation errors are arrays
            const errorMessages = error.detail.map((e: any) => {
              const field = e.loc ? e.loc.join('.') : 'field';
              return `${field}: ${e.msg || e.message || String(e)}`;
            });
            setAuthError(errorMessages.join('; '));
          } else if (typeof error.detail === 'string') {
            setAuthError(error.detail);
          } else {
            setAuthError('Invalid email or password format');
          }
        } else {
          setAuthError(error.detail || 'Login failed');
        }
        return false;
      }
    } catch (error) {
      console.error('Login error:', error);
      setAuthError('Network error. Please try again.');
      return false;
    }
  };

  const register = async (data: RegisterData): Promise<boolean> => {
    setAuthError(null);
    try {
      const response = await fetch(resolveApiUrl('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        const tokens: AuthTokens = await response.json();
        storeTokens(tokens);
        // Store organization and implementations from TokenResponse
        if (tokens.organization !== undefined) {
          setOrganization(tokens.organization);
        }
        if (tokens.implementations !== undefined) {
          setImplementations(Array.isArray(tokens.implementations) ? tokens.implementations : []);
        }
        await refreshUser();
        return true;
      } else {
        const error = await response.json();
        let errorMessage = 'Registration failed';
        if (error.detail) {
          if (typeof error.detail === 'string') {
            errorMessage = error.detail;
          } else if (Array.isArray(error.detail)) {
            errorMessage = error.detail.map((e: any) => e.msg || e.message || String(e)).join('; ');
          }
        }
        setAuthError(errorMessage);
        return false;
      }
    } catch (error) {
      console.error('Registration error:', error);
      setAuthError('Network error. Please try again.');
      return false;
    }
  };

  const logout = async () => {
    try {
      await fetchWithAuth('/api/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearTokens();
      setUser(null);
      setOrganization(null);
      setImplementations([]);
    }
  };

  const clearError = () => setAuthError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        implementations,
        isLoading,
        isAuthenticated: !!user,
        authError,
        login,
        register,
        logout,
        refreshUser,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { fetchWithAuth };

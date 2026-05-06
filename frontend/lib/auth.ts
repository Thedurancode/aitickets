const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  id: number;
  email: string;
  name: string;
  phone?: string | null;
  avatar_url?: string | null;
  auth_provider?: string;
  is_admin?: boolean;
  email_opt_in?: boolean;
  sms_opt_in?: boolean;
  marketing_opt_in?: boolean;
  created_at?: string | null;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

class AuthError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "AuthError";
  }
}

async function authFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "An error occurred" }));
    throw new AuthError(res.status, body.detail || body.message || "An error occurred");
  }
  return res.json();
}

export const auth = {
  register: async (name: string, email: string, password: string): Promise<AuthResponse> => {
    const data = await authFetch<AuthResponse>(`${API_BASE}/api/auth/register`, {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    return data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const data = await authFetch<AuthResponse>(`${API_BASE}/api/auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    return data;
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  },

  getUser: async (): Promise<User> => {
    return authFetch<User>(`${API_BASE}/api/auth/me`);
  },

  updateProfile: async (data: { name?: string; phone?: string; avatar_url?: string }): Promise<User> => {
    return authFetch<User>(`${API_BASE}/api/auth/me`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  refreshToken: async (): Promise<string> => {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
    if (!refreshToken) throw new AuthError(401, "No refresh token");

    const data = await authFetch<{ access_token: string }>(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", data.access_token);
    }
    return data.access_token;
  },

  isLoggedIn: (): boolean => {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("access_token");
  },

  getToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  },
};

export { AuthError };

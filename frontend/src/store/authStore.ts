import { create } from "zustand";
import { IS_AUTH_DISABLED, LOCAL_USER } from "@/config/runtime";
import { authService } from "@/services/api";
import type { User, UserRole } from "@/types";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    username: string,
    password: string,
    role: Extract<UserRole, "developer" | "viewer">,
  ) => Promise<void>;
  logout: () => Promise<void>;
  markUnauthenticated: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: IS_AUTH_DISABLED ? LOCAL_USER : null,
  isAuthenticated: IS_AUTH_DISABLED,
  isLoading: !IS_AUTH_DISABLED,

  checkAuth: async () => {
    if (IS_AUTH_DISABLED) {
      set({ user: LOCAL_USER, isAuthenticated: true, isLoading: false });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authService.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (email, password) => {
    if (IS_AUTH_DISABLED) {
      set({ user: LOCAL_USER, isAuthenticated: true, isLoading: false });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authService.login(email, password);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      throw error;
    }
  },

  signup: async (email, username, password, role) => {
    if (IS_AUTH_DISABLED) {
      set({ user: LOCAL_USER, isAuthenticated: true, isLoading: false });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authService.register({
        email,
        username,
        password,
        role,
      });
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    if (IS_AUTH_DISABLED) {
      set({ user: LOCAL_USER, isAuthenticated: true, isLoading: false });
      return;
    }
    try {
      await authService.logout();
    } finally {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  markUnauthenticated: () =>
    IS_AUTH_DISABLED
      ? set({ user: LOCAL_USER, isAuthenticated: true, isLoading: false })
      : set({ user: null, isAuthenticated: false, isLoading: false }),
}));

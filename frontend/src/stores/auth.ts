import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserPublic } from "@/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  setAuth: (data: {
    access_token: string;
    refresh_token: string;
    user: UserPublic;
  }) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setAuth: (data) =>
        set({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          user: data.user,
        }),
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null }),
      isAuthenticated: () => get().accessToken !== null,
    }),
    {
      name: "quant-auth",
    }
  )
);

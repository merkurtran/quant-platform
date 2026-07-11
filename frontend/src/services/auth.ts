import api from "@/lib/api";
import type { TokenResponse } from "@/types";

export const authService = {
  register: (data: { email: string; password: string; nickname: string }) =>
    api.post<TokenResponse>("/auth/register", data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", data).then((r) => r.data),

  refresh: (refreshToken: string) =>
    api
      .post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })
      .then((r) => r.data),
};

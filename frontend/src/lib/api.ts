import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { toast } from "sonner";
import { API_BASE_URL, ErrorCode } from "@/constants";
import { useAuthStore } from "@/stores/auth";
import type { ApiResponse } from "@/types";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── 请求拦截：附加 token ──
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── 刷新 token 锁，防止并发 401 重复刷新 ──
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const refreshToken = useAuthStore.getState().refreshToken;
  if (!refreshToken) throw new Error("No refresh token");

  const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  const data: ApiResponse<{
    access_token: string;
    refresh_token: string;
    user: import("@/types").UserPublic;
  }> = res.data;

  if (data.code !== ErrorCode.SUCCESS) {
    throw new Error(data.message);
  }

  useAuthStore.getState().setTokens(data.data.access_token, data.data.refresh_token);
  return data.data.access_token;
}

// ── 响应拦截：解包 + 错误处理 ──
api.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse<unknown>;

    // 非标准格式直接返回
    if (body.code === undefined || body.data === undefined) {
      return response;
    }

    if (body.code === ErrorCode.SUCCESS) {
      return { ...response, data: body.data };
    }

    // 业务错误
    throw new ApiError(body.code, body.message);
  },
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const body = error.response?.data as ApiResponse<unknown> | undefined;
    const code = body?.code ?? ErrorCode.UNKNOWN;

    // 401 / token 过期 → 尝试刷新
    if (
      (status === 401 || code === ErrorCode.UNAUTHORIZED || code === ErrorCode.TOKEN_EXPIRED) &&
      !originalRequest._retry
    ) {
      // 排除 auth 接口自身的 401（登录失败/注册冲突），不应触发刷新和跳转
      if (originalRequest.url?.includes("/auth/")) {
        const message = body?.message ?? "操作失败";
        toast.error(message);
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        if (!isRefreshing) {
          isRefreshing = true;
          refreshPromise = doRefresh().finally(() => {
            isRefreshing = false;
            refreshPromise = null;
          });
        }

        const newToken = await (refreshPromise ?? doRefresh());
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch {
        handleAuthFailure();
        return Promise.reject(error);
      }
    }

    // 429 限流
    if (status === 429 || code === ErrorCode.RATE_LIMITED) {
      toast.error("操作过于频繁，请稍后再试");
      return Promise.reject(error);
    }

    // 其他业务错误
    const message = body?.message ?? error.message ?? "请求失败";
    if (code !== ErrorCode.NOT_FOUND) {
      toast.error(message);
    }

    return Promise.reject(new ApiError(code, message));
  }
);

function handleAuthFailure() {
  useAuthStore.getState().logout();
  toast.error("登录已过期，请重新登录");
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

export class ApiError extends Error {
  code: number;
  constructor(code: number, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiError";
  }
}

export default api;

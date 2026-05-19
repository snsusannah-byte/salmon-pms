import axios from "axios";
import { toast } from "sonner";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

/**
 * 带错误提示的 fetch 风格封装（兼容 salmon-finance-v4 迁移的页面）
 */
export async function apiFetch(
  url: string,
  options?: RequestInit,
  successMsg?: string,
  errorMsg: string = "操作失败，请重试"
): Promise<{ ok: boolean; data?: any; error?: string }> {
  try {
    const method = options?.method || "GET";
    const config: any = { method };
    if (options?.headers) config.headers = options.headers;
    if (options?.body) config.data = JSON.parse(options.body as string);

    const res = await api.request({ url, ...config });
    const data = res.data;

    if (!data.success) {
      const msg = data?.error || errorMsg;
      if (errorMsg) toast.error(msg);
      return { ok: false, error: msg };
    }

    if (successMsg) toast.success(successMsg);
    return { ok: true, data: data.data || data };
  } catch (err: any) {
    const msg = `网络错误: ${err.message || "无法连接到服务器"}`;
    toast.error(msg);
    return { ok: false, error: msg };
  }
}

export async function apiPost(
  url: string,
  body: any,
  successMsg?: string,
  errorMsg?: string
): Promise<{ ok: boolean; data?: any; error?: string }> {
  return apiFetch(
    url,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    successMsg,
    errorMsg
  );
}

export async function apiDelete(
  url: string,
  successMsg?: string,
  errorMsg?: string
): Promise<{ ok: boolean; data?: any; error?: string }> {
  return apiFetch(url, { method: "DELETE" }, successMsg, errorMsg);
}

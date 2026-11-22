// Thin REST client. Every call is an HTTP request from the browser (client)
// to the Django REST API (server) — the distributed boundary of the system.

const TOKEN_KEY = "cb_token";

// Where the Django server lives. Empty in development (Vite proxies /api and /ws).
// On hosting, set VITE_API_URL at build time, e.g. https://campblazer-api.onrender.com
export const API_ORIGIN = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

/** Keep uploaded media on the Django origin when the API is hosted separately. */
export function mediaUrl(src: string): string {
  return src.startsWith("/media/") ? `${API_ORIGIN}${src}` : src;
}

/** ws(s)://host for the WebSocket, derived from API_ORIGIN or the page itself. */
export function wsOrigin(): string {
  const base = API_ORIGIN || window.location.origin;
  return base.replace(/^http/, "ws");
}

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t: string | null) {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
}

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown) {
    super(ApiError.message(data, status));
    this.status = status;
    this.data = data;
  }
  static message(data: unknown, status: number): string {
    if (data && typeof data === "object") {
      const d = data as Record<string, unknown>;
      if (typeof d.detail === "string") return d.detail;
      const first = Object.entries(d)[0];
      if (first) {
        const v = Array.isArray(first[1]) ? first[1][0] : first[1];
        return first[0] === "non_field_errors" ? String(v) : `${first[0].replace(/_/g, " ")}: ${String(v)}`;
      }
    }
    return `Request failed (${status})`;
  }
}

async function responseData(res: Response): Promise<unknown> {
  if (res.status === 204) return undefined;

  const contentType = res.headers.get("content-type") ?? "";
  const mediaType = contentType.split(";", 1)[0].trim().toLowerCase();
  if (mediaType !== "application/json" && !mediaType.endsWith("+json")) {
    throw new Error(`Expected a JSON API response, received ${contentType || "no content type"} (HTTP ${res.status}). Check that the API URL targets the Django service.`);
  }

  try {
    return await res.json();
  } catch {
    throw new Error(`The API returned invalid JSON (HTTP ${res.status}). Check that the API URL targets the Django service.`);
  }
}

export interface ApiMeta { workerPid?: string; serverMs?: string; clientMs: number }

/** multipart/form-data upload (photo files). */
export async function upload<T>(path: string, form: FormData): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_ORIGIN}/api${path}`, { method: "POST", headers: token ? { Authorization: `Token ${token}` } : {}, body: form });
  const data = await responseData(res);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export async function api<T>(path: string, opts: { method?: string; body?: unknown } = {}, meta?: (m: ApiMeta) => void): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;
  const t0 = performance.now();
  const res = await fetch(`${API_ORIGIN}/api${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  meta?.({
    workerPid: res.headers.get("X-Worker-PID") ?? undefined,
    serverMs: res.headers.get("X-Processing-Time-ms") ?? undefined,
    clientMs: Math.round(performance.now() - t0),
  });
  const data = await responseData(res);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

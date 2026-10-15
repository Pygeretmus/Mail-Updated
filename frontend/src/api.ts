import { tr } from "./i18n";

const BASE: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public messages: string[],
  ) {
    super(messages.join(" "));
  }
}
export const errText = (e: unknown) =>
  e instanceof ApiError ? e.message : tr("err_request");

const store = {
  get access() {
    return localStorage.getItem("access");
  },
  get refresh() {
    return localStorage.getItem("refresh");
  },
  set(access: string, refresh?: string) {
    localStorage.setItem("access", access);
    if (refresh) localStorage.setItem("refresh", refresh);
  },
  clear() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
  },
};
export const hasSession = () => !!store.refresh;

let onLogout: () => void = () => {};
export const setLogoutHandler = (fn: () => void) => {
  onLogout = fn;
};
export const logout = () => {
  store.clear();
  onLogout();
};

type RefreshResult = "ok" | "rejected" | "failed";

let refreshing: Promise<RefreshResult> | null = null;
async function refreshToken(): Promise<RefreshResult> {
  try {
    const res = await fetch(`${BASE}/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: store.refresh }),
    });
    // Only these mean the refresh token itself is invalid or expired
    if (res.status === 400 || res.status === 401) return "rejected";
    // 5xx, 429 and the like: the token may still be fine
    if (!res.ok) return "failed";
    const data = await res.json();
    store.set(data.access, data.refresh);
    return "ok";
  } catch {
    // Network error or unreadable response
    return "failed";
  }
}

function toError(status: number, data: unknown): ApiError {
  const errors = (
    data as { errors?: { param: string | null; message: string }[] } | null
  )?.errors;
  if (errors?.length)
    return new ApiError(
      status,
      errors.map((e) => e.message),
    );
  if (status === 429) return new ApiError(status, [tr("err_throttle")]);
  return new ApiError(status, [tr("err_generic")]);
}

interface Opts {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

export async function api<T>(
  path: string,
  { method = "GET", body, auth = true }: Opts = {},
): Promise<T> {
  const send = () =>
    fetch(`${BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(auth && store.access
          ? { Authorization: `Bearer ${store.access}` }
          : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  let res: Response;
  try {
    res = await send();
    if (res.status === 401 && auth && store.refresh) {
      refreshing ??= refreshToken().finally(() => {
        refreshing = null;
      });
      const result = await refreshing;
      if (result === "ok") res = await send();
      else if (result === "rejected") {
        logout();
        throw new ApiError(401, [tr("err_session")]);
      } else {
        // Keep the session: the user can simply retry later
        throw new ApiError(0, [tr("err_network")]);
      }
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, [tr("err_network")]);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw toError(res.status, data);
  return data as T;
}

export async function login(email: string, password: string) {
  const t = await api<{ access: string; refresh: string }>("/token/", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  store.set(t.access, t.refresh);
}

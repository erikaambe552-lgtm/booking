import { useCallback, useEffect, useState } from "react";
import { api, getToken } from "./api";

function cacheKey(path: string) {
  const token = getToken();
  return `campblazer.api:${token ? `token-${token}` : "public"}:${path}`;
}

function readCache<T>(path: string): T | null {
  try {
    const value = sessionStorage.getItem(cacheKey(path));
    return value ? JSON.parse(value) as T : null;
  } catch {
    return null;
  }
}

function writeCache<T>(path: string, value: T) {
  try {
    sessionStorage.setItem(cacheKey(path), JSON.stringify(value));
  } catch {
    // Storage may be unavailable or full; the live API response remains usable.
  }
}

export function useApi<T>(path: string | null) {
  const initialData = path ? readCache<T>(path) : null;
  const [state, setState] = useState<{ key: string | null; value: T | null }>({
    key: path,
    value: initialData,
  });
  const data = state.key === path ? state.value : (path ? readCache<T>(path) : null);
  const setData = useCallback((value: T | null | ((current: T | null) => T | null)) => {
    setState((current) => {
      const next = typeof value === "function"
        ? (value as (current: T | null) => T | null)((current.key === path ? current.value : (path ? readCache<T>(path) : null)))
        : value;
      if (path && next !== null) writeCache(path, next);
      return { key: path, value: next };
    });
  }, [path]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(() => !!path && (path ? !readCache<T>(path) : false));
  const [n, setN] = useState(0);
  const reload = useCallback(() => setN((x) => x + 1), []);
  useEffect(() => {
    if (!path) return;
    let alive = true;
    const cached = readCache<T>(path);
    if (cached !== null) setData(cached);
    setLoading(cached === null);
    api<T>(path)
      .then((d) => {
        if (alive) {
          setState({ key: path, value: d });
          writeCache(path, d);
          setError(null);
        }
      })
      .catch((e) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [path, n]);
  return { data, error, loading, reload, setData };
}

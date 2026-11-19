// WebSocket client for server push (Django Channels + Redis).
// One connection per browser tab; reconnects automatically with backoff.
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { getToken, wsOrigin } from "./api";
import { useAuth } from "./auth";

export type LiveEvent = { type: string; [k: string]: unknown };
type Listener = (e: LiveEvent) => void;
export interface Toast { id: number; title: string; body: string; tone: "ok" | "warn" | "info" }

interface Ctx {
  status: "connecting" | "live" | "offline";
  subscribe: (fn: Listener) => () => void;
  watch: (slug: string | null) => void;
  toasts: Toast[];
  dismiss: (id: number) => void;
}
const RealtimeCtx = createContext<Ctx | null>(null);

const STATUS_TEXT: Record<string, string> = { APPROVED: "approved ✅", REJECTED: "rejected", CANCELLED: "cancelled", COMPLETED: "completed" };

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [status, setStatus] = useState<Ctx["status"]>("connecting");
  const [toasts, setToasts] = useState<Toast[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const listeners = useRef(new Set<Listener>());
  const watching = useRef<string | null>(null);
  const userRef = useRef(user);
  userRef.current = user;

  const send = (m: object) => { if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(m)); };

  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((x) => [...x.slice(-3), { ...t, id }]);
    setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), 7000);
  }, []);

  useEffect(() => {
    let closed = false;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout>;
    const connect = () => {
      setStatus("connecting");
      const sock = new WebSocket(`${wsOrigin()}/ws/live/`);
      ws.current = sock;
      sock.onopen = () => {
        retry = 0;
        setStatus("live");
        const token = getToken();
        if (token && userRef.current) sock.send(JSON.stringify({ type: "auth", token }));
        if (watching.current) sock.send(JSON.stringify({ type: "watch", destination: watching.current }));
      };
      sock.onmessage = (ev) => {
        let e: LiveEvent;
        try { e = JSON.parse(ev.data); } catch { return; }
        if (e.type === "reservation.status" && userRef.current && e.old_status !== undefined) {
          const mine = userRef.current.role === "CAMPER";
          toast({
            title: `${e.reference} ${STATUS_TEXT[String(e.status)] ?? String(e.status).toLowerCase()}`,
            body: `${e.destination} · ${e.service}${mine ? "" : ` (was ${String(e.old_status).toLowerCase()})`}`,
            tone: e.status === "APPROVED" || e.status === "COMPLETED" ? "ok" : "warn",
          });
        }
        if (e.type === "reservation.new") {
          toast({ title: `New reservation ${e.reference}`, body: `${e.destination} · ${e.service} — ${e.customer_name}`, tone: "info" });
        }
        listeners.current.forEach((fn) => fn(e));
      };
      sock.onclose = () => {
        if (closed) return;
        setStatus("offline");
        retry = Math.min(retry + 1, 6);
        timer = setTimeout(connect, 500 * 2 ** retry); // 1s, 2s, 4s … max 32s
      };
    };
    timer = setTimeout(connect, 0);
    return () => { closed = true; clearTimeout(timer); ws.current?.close(); };
  }, [toast]);

  // log in / log out without reconnecting
  useEffect(() => {
    const token = getToken();
    if (user && token) send({ type: "auth", token });
    else send({ type: "logout" });
  }, [user]);

  const subscribe = useCallback((fn: Listener) => { listeners.current.add(fn); return () => { listeners.current.delete(fn); }; }, []);
  const watch = useCallback((slug: string | null) => { watching.current = slug; if (slug) send({ type: "watch", destination: slug }); }, []);
  const dismiss = (id: number) => setToasts((x) => x.filter((t) => t.id !== id));

  return <RealtimeCtx.Provider value={{ status, subscribe, watch, toasts, dismiss }}>{children}</RealtimeCtx.Provider>;
}

export function useRealtime() {
  const c = useContext(RealtimeCtx);
  if (!c) throw new Error("useRealtime outside RealtimeProvider");
  return c;
}

/** Run `fn` whenever a server event of one of `types` arrives. */
export function useLiveEvent(types: string[], fn: (e: LiveEvent) => void) {
  const { subscribe } = useRealtime();
  const ref = useRef(fn);
  ref.current = fn;
  const key = types.join(",");
  useEffect(() => subscribe((e) => { if (key.split(",").includes(e.type)) ref.current(e); }), [subscribe, key]);
}

export function Toaster() {
  const { toasts, dismiss } = useRealtime();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <button key={t.id} className={`toast toast-${t.tone}`} onClick={() => dismiss(t.id)}>
          <b>{t.title}</b><span>{t.body}</span><small>Live update · pushed by server</small>
        </button>
      ))}
    </div>
  );
}

export function LiveDot() {
  const { status } = useRealtime();
  return <span className={`live-dot live-${status}`} title={`Real-time connection: ${status}`}><i />{status === "live" ? "Live" : status === "connecting" ? "…" : "Offline"}</span>;
}

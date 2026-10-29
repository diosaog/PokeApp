import { useEffect, useState } from "react";
import { AlertTriangle, Check, X } from "lucide-react";

// Small notices at the top of every screen: the real reason an action could
// not be done, warnings, and short confirmations. The same text is never
// stacked twice; each one retires by itself or when its problem is solved.
export type NoticeTone = "error" | "warn" | "ok";
type TopNotice = { id: number; tone: NoticeTone; text: string; key: string };
let topNotices: TopNotice[] = [];
let noticeId = 0;
const noticeTimers = new Map<number, ReturnType<typeof setTimeout>>();
const noticeListeners = new Set<(items: TopNotice[]) => void>();
const emitNotices = () => noticeListeners.forEach((fn) => fn(topNotices));
export function notify(
  text: string,
  tone: NoticeTone = "error",
  { key = text, ttl = tone === "ok" ? 4000 : 9000 } = {},
) {
  const existing = topNotices.find((n) => n.key === key);
  const id = existing?.id ?? ++noticeId;
  topNotices = [
    ...topNotices.filter((n) => n.key !== key),
    { id, tone, text, key },
  ].slice(-3);
  clearTimeout(noticeTimers.get(id));
  noticeTimers.set(
    id,
    setTimeout(() => dismissNotice(key), ttl),
  );
  emitNotices();
}
export function dismissNotice(key: string) {
  const found = topNotices.find((n) => n.key === key);
  if (!found) return;
  clearTimeout(noticeTimers.get(found.id));
  noticeTimers.delete(found.id);
  topNotices = topNotices.filter((n) => n.key !== key);
  emitNotices();
}
export function TopNotices() {
  const [items, setItems] = useState(topNotices);
  useEffect(() => {
    noticeListeners.add(setItems);
    return () => {
      noticeListeners.delete(setItems);
    };
  }, []);
  if (!items.length) return null;
  return (
    <div className="top-notices" role="status" aria-live="polite">
      {items.map((n) => (
        <p key={n.id} className="top-notice" data-tone={n.tone}>
          {n.tone === "ok" ? (
            <Check size={16} aria-hidden="true" />
          ) : (
            <AlertTriangle size={16} aria-hidden="true" />
          )}
          <span>{n.text}</span>
          <button
            className="icon-button"
            aria-label="Cerrar aviso"
            onClick={() => dismissNotice(n.key)}
          >
            <X size={14} />
          </button>
        </p>
      ))}
    </div>
  );
}

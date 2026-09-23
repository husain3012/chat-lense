export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, init);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export const number = (n: number) =>
  new Intl.NumberFormat().format(Math.round(n));
export function date(value: string | null, full = false) {
  if (!value) return "—";
  const format =
    typeof window !== "undefined"
      ? localStorage.getItem("chatlens-date")
      : "locale";
  if (format === "iso") {
    return new Date(value)
      .toISOString()
      .slice(0, full ? 16 : 10)
      .replace("T", " ");
  }
  return new Date(value).toLocaleString(
    undefined,
    full
      ? { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }
      : { dateStyle: "medium", timeZone: "UTC" },
  );
}
export function duration(n: number | null | undefined) {
  if (n == null) return "Unavailable";
  return n < 60
    ? `${Math.round(n)}s`
    : n < 3600
      ? `${Math.round(n / 60)}m`
      : n < 86400
        ? `${(n / 3600).toFixed(1)}h`
        : `${(n / 86400).toFixed(1)}d`;
}

export function errorText(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(errorText).join(" ");
  if (value && typeof value === "object")
    return Object.entries(value)
      .map(
        ([k, v]) =>
          `${k === "detail" || k === "non_field_errors" ? "" : k + ": "}${errorText(v)}`,
      )
      .join(" ");
  return "Не удалось выполнить запрос.";
}
let refreshPromise;
export async function api(path, options = {}) {
  const token = sessionStorage.getItem("access");
  const isForm = options.body instanceof FormData;
  const headers = {
    "X-CSRFToken": decodeURIComponent(
      document.cookie
        .split("; ")
        .find((v) => v.startsWith("csrftoken="))
        ?.split("=")[1] || "",
    ),
    ...(!isForm && options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };
  const response = await fetch(
    path.startsWith("/api/") ? path : `/api/${path}`,
    {
      ...options,
      headers,
      body:
        options.body && !isForm ? JSON.stringify(options.body) : options.body,
    },
  );
  if (
    response.status === 401 &&
    sessionStorage.getItem("refresh") &&
    !options.retried
  ) {
    if (!refreshPromise)
      refreshPromise = fetch("/api/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: sessionStorage.getItem("refresh") }),
      })
        .then(async (r) => (r.ok ? await r.json() : null))
        .finally(() => {
          refreshPromise = null;
        });
    const t = await refreshPromise;
    if (t) {
      sessionStorage.setItem("access", t.access);
      if (t.refresh) sessionStorage.setItem("refresh", t.refresh);
      return api(path, { ...options, retried: true });
    }
    sessionStorage.removeItem("access");
    sessionStorage.removeItem("refresh");
    window.dispatchEvent(new Event("session-expired"));
  }
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = { detail: "Сервер временно недоступен. Попробуйте позже." };
    }
    throw new Error(errorText(data));
  }
  return response.status === 204 ? null : response.json();
}
export const rows = (data) =>
  Array.isArray(data) ? data : data?.results || [];
export const money = (value) =>
  new Intl.NumberFormat("ru-RU").format(value || 0) + " ₽";
export const number = (value) =>
  new Intl.NumberFormat("ru-RU", {
    notation: value >= 100000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value || 0);
export async function downloadFile(kind, id) {
  const r = await fetch(`/api/files/${kind}/${id}/`, {
    headers: { Authorization: `Bearer ${sessionStorage.getItem("access")}` },
  });
  if (!r.ok) throw new Error("Не удалось скачать файл. Проверьте доступ.");
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = r.headers.get("content-disposition") || "";
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  a.download = encoded
    ? decodeURIComponent(encoded[1])
    : disposition.match(/filename="([^"]+)"/)?.[1] || "attachment";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function downloadCatalog(filters) {
  const r = await fetch("/api/export/?" + new URLSearchParams(filters), {
    headers: { Authorization: `Bearer ${sessionStorage.getItem("access")}` },
  });
  if (!r.ok) throw new Error("Экспорт недоступен. Войдите как рекламодатель.");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = "bloggers.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

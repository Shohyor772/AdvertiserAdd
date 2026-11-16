import { test } from "node:test";
import assert from "node:assert/strict";
import { api, errorText, rows, money } from "../src/api.js";

test("API field errors retain every validation message", () => {
  assert.equal(
    errorText({
      price: ["Цена должна быть положительной."],
      non_field_errors: ["Добавьте ТЗ."],
    }),
    "price: Цена должна быть положительной. Добавьте ТЗ.",
  );
  assert.deepEqual(rows({ results: [{ id: 1 }] }), [{ id: 1 }]);
  assert.match(money(12000), /12\s000 ₽/);
});

test("parallel expired requests share one refresh and retain rotated token", async () => {
  const store = new Map([
    ["access", "old-access"],
    ["refresh", "old-refresh"],
  ]);
  globalThis.sessionStorage = {
    getItem: (k) => store.get(k),
    setItem: (k, v) => store.set(k, v),
    removeItem: (k) => store.delete(k),
  };
  globalThis.document = { cookie: "" };
  let refreshCalls = 0;
  const original = globalThis.fetch;
  globalThis.fetch = async (path, options) => {
    if (path === "/api/token/refresh/") {
      refreshCalls++;
      await new Promise((r) => setTimeout(r, 20));
      return new Response(
        JSON.stringify({ access: "new-access", refresh: "new-refresh" }),
        { status: 200 },
      );
    }
    return options.headers.Authorization === "Bearer new-access"
      ? new Response(JSON.stringify({ ok: true }), { status: 200 })
      : new Response("{}", { status: 401 });
  };
  try {
    const responses = await Promise.all([api("me/"), api("notifications/")]);
    assert.equal(refreshCalls, 1);
    assert.equal(store.get("refresh"), "new-refresh");
    assert.deepEqual(responses, [{ ok: true }, { ok: true }]);
  } finally {
    globalThis.fetch = original;
  }
});

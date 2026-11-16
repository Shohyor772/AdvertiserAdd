import { test, expect } from "@playwright/test";

async function login(page, username) {
  await page.goto("/#/login");
  await page.getByLabel("Имя пользователя", { exact: true }).fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill("E2e-Local-Only-8472");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Найдите своего блогера" }),
  ).toBeVisible();
}
test("catalog desktop and mobile, filters, empty state, detail", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Найдите своего блогера" }),
  ).toBeVisible();
  await expect(page.locator(".blogger-card")).toHaveCount(1);
  await page.screenshot({ path: "../tmp/catalog-desktop.png", fullPage: true });
  await page.getByLabel("Цена до", { exact: true }).fill("1");
  await page.getByRole("button", { name: "Показать блогеров" }).click();
  await expect(
    page.getByRole("heading", { name: "Пока нет совпадений" }),
  ).toBeVisible();
  await page
    .locator(".filter-title")
    .getByRole("button", { name: "Сбросить" })
    .click();
  await page.locator(".card-name").click();
  await expect(
    page.getByRole("heading", { name: "e2e_blogger", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/");
  await expect(
    page.getByRole("heading", { name: "Найдите своего блогера" }),
  ).toBeVisible();
  await expect(page.locator('.sidebar')).not.toBeInViewport();
  await page.screenshot({ path: "../tmp/catalog-mobile.png", fullPage: true, animations: 'disabled' });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await expect(page.getByLabel("Город", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("proposal → counter offer → reserve → revision → acceptance → mutual review", async ({
  browser,
}) => {
  const ad = await browser.newContext(),
    blog = await browser.newContext();
  const a = await ad.newPage(),
    b = await blog.newPage();
  await login(a, "e2e_ad");
  await a.locator(".card-name").click();
  await a
    .getByLabel("Идея и требования")
    .fill("Браузерный сценарий: интеграция нового приложения");
  await a.getByRole("button", { name: "Отправить предложение" }).click();
  await expect(
    a.getByRole("heading", { name: "Условия интеграции" }),
  ).toBeVisible();
  const route = new URL(a.url()).hash;
  await login(b, "e2e_blogger");
  await b.goto("/" + route);
  await b.getByLabel("Встречная цена, ₽").fill("15000");
  await b.getByRole("button", { name: "Предложить цену", exact: true }).click();
  await expect(b.locator(".deal-price")).toHaveText("15 000 ₽");
  await a.reload();
  await a.getByRole("button", { name: "Принять условия" }).click();
  await a.getByRole("button", { name: "Создать тестовый резерв" }).click();
  await expect(a.locator(".deal-status")).toContainText("В работе");
  await b.reload();
  await b.getByLabel("Ссылка на публикацию").fill("https://t.me/e2e_blogger/1");
  await b.getByRole("button", { name: "Сдать работу" }).click();
  await a.reload();
  await a.getByLabel("Что исправить?").fill("Добавьте ссылку на приложение");
  await a.getByRole("button", { name: "Отправить на доработку" }).click();
  await expect(a.locator(".deal-status")).toContainText("Доработка");
  await b.reload();
  await b.getByLabel("Ссылка на публикацию").fill("https://t.me/e2e_blogger/2");
  await b.getByRole("button", { name: "Сдать работу" }).click();
  await a.reload();
  await a.getByRole("button", { name: "Принять работу", exact: true }).click();
  await expect(a.locator(".deal-status")).toContainText("Завершена");
  await a.getByLabel("Ваш отзыв").fill("Успешно проверено в браузере");
  await a.getByRole("button", { name: "Оставить отзыв" }).click();
  await b.reload();
  await b.getByRole("button", { name: "Оставить отзыв" }).click();
  await expect(
    b.getByRole("heading", { name: "Отзывы по сделке" }),
  ).toBeVisible();
  await a.screenshot({ path: "../tmp/completed-deal.png", fullPage: true });
  await ad.close();
  await blog.close();
});

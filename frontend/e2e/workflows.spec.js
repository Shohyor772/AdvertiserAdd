import { test, expect } from "@playwright/test";

test("educational registration confirms locally without external requests", async ({
  page,
}) => {
  const external = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:8002")) external.push(r.url());
  });
  await page.goto("/#/register");
  const username = "edu_registered_" + Date.now();
  await page.getByLabel("Имя пользователя", { exact: true }).fill(username);
  await page
    .getByLabel("Email", { exact: true })
    .fill(username + "@example.test");
  await page
    .getByLabel("Пароль", { exact: true })
    .fill("Educational-Strong-54321");
  await page
    .getByRole("button", { name: "Зарегистрироваться", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Подтвердите email" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Подтвердить учебный email" }).click();
  await expect(
    page.getByText("Email подтверждён. Теперь можно войти.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Перейти ко входу" }).click();
  await page.getByLabel("Имя пользователя", { exact: true }).fill(username);
  await page
    .getByLabel("Пароль", { exact: true })
    .fill("Educational-Strong-54321");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Найдите своего блогера" }),
  ).toBeVisible();
  expect(external).toEqual([]);
});

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
  await expect(page.locator(".sidebar")).not.toBeInViewport();
  await page.screenshot({
    path: "../tmp/catalog-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await expect(page.getByLabel("Город", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
  for (const width of [320, 768]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
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

test("file brief → dispute → support message → administrator refund", async ({
  browser,
}) => {
  const ad = await browser.newContext(),
    blog = await browser.newContext(),
    admin = await browser.newContext();
  const a = await ad.newPage(),
    b = await blog.newPage(),
    m = await admin.newPage();
  await login(a, "e2e_ad");
  await a.locator(".card-name").click();
  await a.getByLabel("Файл ТЗ (необязательно)").setInputFiles({
    name: "brief.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Publish the agreed product link."),
  });
  await a.getByRole("button", { name: "Отправить предложение" }).click();
  await expect(
    a.getByRole("heading", { name: "Условия интеграции" }),
  ).toBeVisible();
  const route = new URL(a.url()).hash;
  await login(b, "e2e_blogger");
  await b.goto("/" + route);
  await b.getByRole("button", { name: "Принять условия" }).click();
  await a.reload();
  await a.getByRole("button", { name: "Создать тестовый резерв" }).click();
  await b.reload();
  await b
    .getByLabel("Ссылка на публикацию")
    .fill("https://t.me/e2e_blogger/disputed");
  await b.getByRole("button", { name: "Сдать работу" }).click();
  await a.reload();
  await a.locator("summary").filter({ hasText: "Открыть спор" }).click();
  await a.getByLabel("Причина спора").fill("В публикации отсутствует продукт");
  await a.getByLabel("Доказательства (до 10 МБ)").setInputFiles({
    name: "evidence.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Missing product link."),
  });
  await a.getByRole("button", { name: "Открыть спор", exact: true }).click();
  await expect(a.locator(".deal-status")).toContainText("Спор");
  await expect(
    a.getByRole("button", { name: "Принять работу", exact: true }),
  ).toHaveCount(0);
  await login(m, "e2e_admin");
  await m.goto("/" + route);
  await m
    .getByLabel("Сообщение", { exact: true })
    .fill("Предоставьте дополнительные материалы в чат.");
  await m.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(m.locator(".messages")).toContainText(
    "дополнительные материалы",
  );
  await m.getByLabel("Решение", { exact: true }).selectOption("advertiser");
  await m
    .getByLabel("Обоснование")
    .fill("Публикация не соответствует согласованному ТЗ");
  await m.getByRole("button", { name: "Вынести решение" }).click();
  await expect(m.locator(".deal-status")).toContainText("Возврат");
  await m.screenshot({ path: "../tmp/arbitration-refund.png", fullPage: true });
  await ad.close();
  await blog.close();
  await admin.close();
});

test("campaign → persisted response → linked proposal; moderator blocks and unblocks", async ({
  browser,
}) => {
  const ad = await browser.newContext(),
    blog = await browser.newContext(),
    admin = await browser.newContext();
  const a = await ad.newPage(),
    b = await blog.newPage(),
    m = await admin.newPage();
  await login(a, "e2e_ad");
  await a.goto("/#/campaigns");
  await a.getByRole("button", { name: "Новая кампания" }).click();
  const title = "Учебный подбор " + Date.now();
  await a.getByLabel("Название", { exact: true }).fill(title);
  await a.getByLabel("Тематика", { exact: true }).fill("Технологии");
  await a.getByLabel("Общий бюджет, ₽").fill("20000");
  const now = new Date();
  await a
    .getByLabel("Начало", { exact: true })
    .fill(now.toISOString().slice(0, 10));
  await a
    .getByLabel("Окончание", { exact: true })
    .fill(new Date(now.getTime() + 7 * 86400000).toISOString().slice(0, 10));
  await a
    .getByLabel("Продукт, формат и требования")
    .fill("Учебный продукт без подключения к платформам");
  await a.getByRole("button", { name: "Создать и подобрать блогеров" }).click();
  const card = a
    .locator(".campaign-card")
    .filter({ has: a.getByRole("heading", { name: title, exact: true }) });
  await expect(card).toBeVisible();
  await login(b, "e2e_blogger");
  await b.goto("/#/campaigns");
  const blogCard = b
    .locator(".campaign-card")
    .filter({ has: b.getByRole("heading", { name: title, exact: true }) });
  await blogCard
    .getByRole("button", { name: "Откликнуться", exact: true })
    .click();
  await b.reload();
  await expect(
    blogCard.getByRole("button", { name: "Отклик отправлен", exact: true }),
  ).toBeDisabled();
  await a.reload();
  await card.locator(".campaign-responses a").click();
  await expect(a.getByLabel("Кампания (необязательно)")).toHaveValue(/\d+/);
  await login(m, "e2e_admin");
  await m.getByRole("link", { name: "Модерация", exact: true }).click();
  await m.getByLabel("Поиск пользователя").fill("e2e_blogger");
  await m.getByRole("button", { name: "Найти пользователя" }).click();
  const member = m
    .locator(".moderation-card")
    .filter({
      has: m.getByRole("heading", { name: "e2e_blogger", exact: true }),
    });
  await member.getByLabel("Действие для e2e_blogger").selectOption("verify");
  await member.getByRole("button", { name: "Применить" }).click();
  await expect(
    member.getByText("Профиль подтверждён", { exact: true }),
  ).toBeVisible();
  await member.getByLabel("Действие для e2e_blogger").selectOption("block");
  await member.getByRole("button", { name: "Применить" }).click();
  await expect(member.getByText("Заблокирован", { exact: true })).toBeVisible();
  await m.screenshot({ path: "../tmp/moderation-desktop.png", fullPage: true });
  await member.getByLabel("Действие для e2e_blogger").selectOption("unblock");
  await member.getByRole("button", { name: "Применить" }).click();
  await expect(member.getByText("Активен", { exact: true })).toBeVisible();
  await member.getByLabel("Действие для e2e_blogger").selectOption("unverify");
  await member.getByRole("button", { name: "Применить" }).click();
  await expect(
    member.getByText("Профиль подтверждён", { exact: true }),
  ).toHaveCount(0);
  await ad.close();
  await blog.close();
  await admin.close();
});

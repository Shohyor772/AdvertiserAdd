# Blogger Marketplace

Платформа для поиска блогеров и управления рекламными интеграциями. Реализованы React-интерфейс, Django REST API, учётные записи, каталог, переговоры, чат, кампании, сдача/приёмка, доработка, арбитраж и отзывы.

**Текущая версия проводит только тестовые сделки без реальных денег.** Полное production-соответствие ТЗ ещё не достигнуто: платёжный шлюз/реальные выплаты, полноценный антифрод, Web Push при закрытом приложении и инфраструктурные SLA остаются открытыми. Google/YouTube/Telegram и реестр ИНН имеют адаптеры, но требуют ваших ключей и приёмки на реальных аккаунтах. Подробности: [исходный аудит](docs/requirements-audit.md), [текущий статус](project-status.md), [проверки](docs/validation.md), [архитектура/UML](docs/architecture.md).

## Локальный запуск в Windows

Требуются Python 3.14 и Node.js 22+. Существующая `db.sqlite3` используется по умолчанию; база не пересоздаётся. Перед обновлением остановите старый сервер. Не заменяйте свой `.env`, если он уже настроен.

```powershell
cd C:\AdvertiserAdd
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
# Только если .env ещё нет:
Copy-Item .env.example .env
venv\Scripts\python.exe manage.py backup_database
venv\Scripts\python.exe manage.py migrate
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
venv\Scripts\python.exe manage.py collectstatic --noinput
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Откройте http://127.0.0.1:8000/ . В `.env.example` включён `PAYMENT_MODE=test`. Резерв, комиссия, выплата и возврат в этом режиме — записи тестового журнала; банковские операции не выполняются. При `DEBUG=false` тестовые платежи запрещены настройками.

Регистрация доступна из интерфейса. По умолчанию письмо подтверждения выводится в терминал сервера: скопируйте ссылку целиком в браузер. Для существующих пользователей с неподтверждённым email есть кнопка повторной отправки в профиле. Существующие пароли и роли не менялись. Для нового администратора используйте `manage.py createsuperuser`, если у вас ещё нет административного аккаунта.

Админка: `/admin/`. Документация API: `/api/docs/`, схема: `/api/schema/`, сохранённая спецификация: `docs/openapi.yml`. Healthcheck: `/health/`.

## Основной сценарий

1. Зарегистрируйте рекламодателя и блогера; подтвердите email. Блогер заполняет профиль вручную либо подключает YouTube при настроенном OAuth.
2. Рекламодатель находит автора по фильтрам и отправляет цену с текстом или файлом ТЗ. Создаются чат и уведомление.
3. В разных браузерах/профилях согласуйте цену. Принять условия может другая сторона, отправившая последнюю цену.
4. Рекламодатель создаёт **тестовый** резерв, блогер сдаёт HTTPS-ссылку на публикацию.
5. Рекламодатель принимает работу или пишет замечания. После повторной сдачи доступна приёмка. По завершении обе стороны оставляют отзывы.
6. Для проверки альтернативы откройте спор. Администратор входит в React-интерфейс и открывает сделку из уведомлений/сообщений, изучает ТЗ, переписку и доказательства, выносит решение с обоснованием. Тестовый резерв выплачивается блогеру или возвращается рекламодателю.

Для арбитража через Django Admin сначала сохраните обоснование в поле resolution, затем выберите действие над спором в списке. Состояния финансовых моделей недоступны для произвольного редактирования в админке. Премиум-доступ к аналитике включается администратором в пользователях; пользователь не может назначить его себе.

## Фоновые задачи и резервные копии

При локальном запуске без Redis создание кампании выполняет начальный мэтчинг сразу. Периодические операции требуют запущенного планировщика. Без Celery можно вручную выполнять:

```powershell
venv\Scripts\python.exe manage.py run_maintenance
venv\Scripts\python.exe manage.py backup_database
```

`run_maintenance` проверяет автоприёмку через 3 дня, новые совпадения сохранённых поисков, кампании и эвристики статистики. Он не должен запускать реальные платежи. `backup_database` создаёт новую копию в игнорируемом `backups/`: SQLite online backup с `integrity_check` либо PostgreSQL `pg_dump -Fc`. Для PostgreSQL утилита `pg_dump` должна быть установлена (в Dockerfile предусмотрена).

С Celery Beat автоприёмка выполняется раз в 5 минут, подбор/проверки — раз в час, backup — раз в 24 часа. Начальная копия также создаётся перед миграциями при запуске web-контейнера. Расписание требует постоянно работающих worker и beat; локально без них нет обещания автоматического выполнения. Копии SQLite хранятся рядом с проектом; для защиты от потери диска нужно отдельное внешнее хранилище. Файлы `media/` резервируйте отдельно.

Восстановление SQLite: остановите web/worker/beat; сохраните текущую базу отдельным файлом; скопируйте выбранную проверенную копию из `backups/` в `db.sqlite3`; выполните `manage.py migrate`; запустите приложение. Не подменяйте файл во время работы сервера. Для PostgreSQL используйте `pg_restore` в отдельную пустую базу, проверьте количества сущностей и только затем переключайте подключение.

## Docker и PostgreSQL

```powershell
# .env подготовлен, db.sqlite3 существует
# Для нового клона сначала выполните локальный manage.py migrate.
docker compose up --build -d
```

Базовый Compose сохраняет текущую SQLite через bind mount. Включены Redis, Celery worker и beat; порты Redis/PostgreSQL наружу не публикуются. Docker Desktop должен быть запущен. Проверка синтаксиса: `docker compose config --quiet`. Остановка с сохранением данных: `docker compose stop`. Не удаляйте volumes при обновлении.

Переход на PostgreSQL выполняйте явно, в отдельную пустую базу, сохранив SQLite и файлы `media/`:

1. Пока `POSTGRES_HOST` пуст, выполните backup и экспорт:

```powershell
venv\Scripts\python.exe manage.py dumpdata --natural-foreign --exclude contenttypes --exclude auth.permission --output backups/transfer.json
```

2. В `.env` установите `POSTGRES_HOST=db`, непустой `POSTGRES_PASSWORD`, нужные `POSTGRES_DB/POSTGRES_USER`. Файл экспорта содержит приватные данные: не отправляйте в чат и Git.
3. Запустите новую PostgreSQL и Redis, примените схему и загрузите экспорт:

```powershell
docker compose --profile postgres up -d db redis --wait
docker compose --profile postgres run --rm web python manage.py migrate
docker compose --profile postgres run --rm web python manage.py loaddata /app/backups/transfer.json
```

4. Сверьте пользователей, профили, предложения, кампании, сделки, сообщения, отзывы, финансовый журнал и доступ к файлам. Только после проверки запустите остальные сервисы: `docker compose --profile postgres up --build -d`. Импорт в уже заполненную базу выполнять нельзя: возможны конфликты идентификаторов. Если нужно вернуться к SQLite, остановите сервисы и очистите `POSTGRES_HOST`; исходный файл сохранён.

Для production установите `DEBUG=false`, новый случайный `SECRET_KEY`, `PAYMENT_MODE=disabled`, свой домен в `ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS` и `PUBLIC_URL=https://...`. Поставьте reverse proxy с TLS 1.2+ перед loopback-портом web; он должен перезаписывать `X-Forwarded-Proto`, а прямой доступ к backend нужно закрыть. Настройки HTTPS включены в Django, но сертификаты и публичный сервер в этот репозиторий не входят. Не публикуйте `/media/` напрямую: скачивание приватных материалов выполняет API с проверкой прав.

## Как передать недостающие настройки

Секреты запишите **локально в `C:\AdvertiserAdd\.env`**, используя имена из `.env.example`. Достаточно написать в чате, какие подключения настроены; значения ключей и пароли присылать не нужно.

- Google: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; OAuth web client с redirect `PUBLIC_URL/auth/google/callback/`. Для импорта включите YouTube Data API v3 и YouTube Analytics API, разрешите тестовые аккаунты на consent screen. Проверены обработчики и ошибки с mock-ответами; реальные данные потребуют проверки после подключения. Для постоянного фонового обновления нужен отдельный процесс хранения/обновления consent-токенов.
- Telegram: `TELEGRAM_BOT_NAME`, `TELEGRAM_BOT_TOKEN`; домен Login Widget задаётся через BotFather. Telegram Login не предоставляет автоматически полную демографию канала; для неё нужен отдельный подтверждённый источник.
- Почта: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, SMTP-настройки и адрес отправителя.
- ИНН: `DADATA_API_TOKEN`. Без ключа регистрация проверяет только контрольную сумму, а `inn_verified` остаётся false; это не выдаётся за успешную проверку по реестру.
- Платежи: сообщите выбранного провайдера и режим подключения (sandbox, модель безопасной сделки, получатели выплат). Ключи будущего шлюза кладите в `.env` после согласования адаптера. **Сейчас переменные платёжного провайдера не обрабатываются: нужно реализовать и проверить create/payment webhook/payout/refund, а не просто добавить ключ.**
- Полный антифрод: нужен согласованный источник качества аудитории/ботов, доступ к нему и критерии проверки. Текущие эвристики не доказывают отсутствие накруток.
- Web Push вне открытой страницы/мобильный клиент: нужны публичный HTTPS-домен, push-инфраструктура и отдельная реализация подписок/service worker (мобильное приложение отсутствует). Сейчас есть внутренняя лента и browser notifications при открытом приложении.

Дополнительные макеты, уточнения ТЗ или исходники UML можно положить в `docs/requirements/` или прикрепить к этому чату. Приватные настройки туда не добавляйте.

## Проверки

```powershell
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py makemigrations --check --dry-run
venv\Scripts\python.exe manage.py test --noinput
venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn --file docs/openapi.yml
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Браузерные тесты используют отдельную базу `tmp/e2e.sqlite3` и сами запускают сервер на 8002. Демо-пароль применяется только к тестовым аккаунтам этой базы. Для Linux замените `venv/Scripts/python.exe` на `venv/bin/python`.

```powershell
venv\Scripts\python.exe scripts/prepare_e2e.py
venv\Scripts\python.exe manage.py collectstatic --noinput
cd frontend
npx.cmd playwright install chromium
npx.cmd playwright test
```

Для локального измерения каталога: `venv\Scripts\python.exe scripts/benchmark_catalog.py`. Оно создаёт отдельную `tmp/benchmark.sqlite3`, не меняет пользовательскую базу и не имитирует 50 000 одновременных пользователей. Тесты PostgreSQL-конкурентности включаются только с PostgreSQL; локально на SQLite помечаются skipped. CI содержит отдельные задания SQLite/PostgreSQL и браузерные сценарии.

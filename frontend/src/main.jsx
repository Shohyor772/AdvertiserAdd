import React, { useState, useEffect, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  Search,
  SlidersHorizontal,
  ArrowUpRight,
  ArrowRight,
  Check,
  CheckCheck,
  BadgeCheck,
  MapPin,
  Users,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  LayoutGrid,
  Megaphone,
  Bell,
  ChartNoAxesCombined,
  LogOut,
  Menu,
  X,
  ShieldCheck,
  Bookmark,
  Plus,
  Paperclip,
  Send,
  Star,
  Link,
  UserRound,
  Settings,
  AlertCircle,
  RefreshCw,
  Wallet,
  CheckCircle2,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { api, rows, money, number, downloadFile, downloadCatalog } from "./api";
import "./style.css";

function useRoute() {
  const [r, set] = useState(location.hash.slice(1) || "/");
  useEffect(() => {
    const f = () => {
      set(location.hash.slice(1) || "/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return r;
}
function useLoad(path, key = 0) {
  const [data, set] = useState(null),
    [error, err] = useState(""),
    [loading, busy] = useState(true);
  const refresh = useCallback(() => {
    busy(true);
    err("");
    return api(path)
      .then(set)
      .catch((e) => err(e.message))
      .finally(() => busy(false));
  }, [path, key]);
  useEffect(() => {
    let active = true;
    busy(true);
    err("");
    api(path)
      .then((d) => active && set(d))
      .catch((e) => active && err(e.message))
      .finally(() => active && busy(false));
    return () => {
      active = false;
    };
  }, [path, key]);
  return { data, error, loading, refresh, set };
}
const go = (path) => {
  location.hash = path;
};
const IconButton = ({ label, children, ...props }) => (
  <button className="icon-button" aria-label={label} title={label} {...props}>
    {children}
  </button>
);
function Empty({ title = "Пока ничего нет", children, icon: Icon = Search }) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={28} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function ErrorBox({ text }) {
  return (
    text && (
      <div className="error" role="alert">
        <AlertCircle size={18} />
        <span>{text}</span>
      </div>
    )
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <RefreshCw className="spin" size={22} /> Загружаем данные…
    </div>
  );
}
function Badge({ b }) {
  return b.is_verified ? (
    <span className="badge good">
      <BadgeCheck size={13} /> Проверен
    </span>
  ) : b.fraud_status === "suspicious" ? (
    <span className="badge warn">Есть подозрения</span>
  ) : (
    <span className="badge neutral">Не верифицирован</span>
  );
}
function Avatar({ name, size = "normal", id = 0, src }) {
  return (
    <div className={`avatar ${size} tone-${Number(id) % 5}`}>
      {src ? (
        <img
          src={src}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      ) : (
        (name || "?").slice(0, 2).toUpperCase()
      )}
    </div>
  );
}
function Form({
  onSubmit,
  children,
  button = "Сохранить",
  className = "",
  successText = "",
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  return (
    <form
      className={className}
      onSubmit={async (e) => {
        e.preventDefault();
        if (busy) return;
        const form = e.currentTarget;
        setBusy(true);
        setError("");
        setSuccess("");
        try {
          await onSubmit(new FormData(form), form);
          setSuccess(successText);
        } catch (e) {
          setError(e.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <fieldset disabled={busy}>
        {children}
        <ErrorBox text={error} />
        {success && (
          <p className="success" role="status">
            {success}
          </p>
        )}
        <button className="button primary" type="submit">
          {busy ? "Подождите…" : button}
          {!busy && <ArrowRight size={16} />}
        </button>
      </fieldset>
    </form>
  );
}
function Field({ label, name, type = "text", ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input name={name} type={type} {...props} />
    </label>
  );
}
function Select({ label, name, children, ...props }) {
  const id=React.useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} name={name} {...props}>
        {children}
      </select>
    </div>
  );
}
function TextArea({ label, name, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea name={name} rows={4} {...props} />
    </label>
  );
}
function PageHead({ eyebrow, title, description, children }) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children}
    </div>
  );
}

function App() {
  const route = useRoute(),
    [user, setUser] = useState(null),
    [ready, setReady] = useState(false),
    [mobile, setMobile] = useState(false),
    [notice, setNotice] = useState("");
  const [opts, setOpts] = useState({
      categories: [],
      cities: [],
      platforms: ["Telegram", "YouTube", "TikTok"],
      payment_mode: "disabled",
    }),
    [notifications, setNotifications] = useState([]);
  useEffect(() => {
    api("options/")
      .then(setOpts)
      .catch(() => {});
    if (sessionStorage.getItem("access"))
      api("me/")
        .then(setUser)
        .catch(() => {})
        .finally(() => setReady(true));
    else setReady(true);
    const f = () => {
      setUser(null);
      setNotice("Сессия завершилась. Войдите снова.");
    };
    window.addEventListener("session-expired", f);
    return () => window.removeEventListener("session-expired", f);
  }, []);
  const seen = useRef(new Set());
  useEffect(() => {
    if (!user) return;
    let active = true;
    let first = true;
    const load = () =>
      api("notifications/")
        .then((d) => {
          if (!active) return;
          const list = rows(d);
          setNotifications(list);
          if (
            !first &&
            user.notifications_enabled &&
            "Notification" in window &&
            Notification.permission === "granted"
          ) {
            list
              .filter((n) => !n.is_read && !seen.current.has(n.id))
              .forEach((n) => {
                const p = new Notification("Blogger Marketplace", {
                  body: n.text,
                });
                p.onclick = () => {
                  window.focus();
                  go(n.link.replace(/^#/, ""));
                };
              });
          }
          list.forEach((n) => seen.current.add(n.id));
          first = false;
        })
        .catch(() => {});
    load();
    const timer = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [user]);
  useEffect(() => setMobile(false), [route]);
  const logout = async () => {
    try {
      await api("logout/", {
        method: "POST",
        body: { refresh: sessionStorage.getItem("refresh") },
      });
    } catch {}
    sessionStorage.clear();
    setUser(null);
    setNotifications([]);
    go("/");
  };
  const unread = notifications.filter((n) => !n.is_read).length;
  const links = [
    ["/", LayoutGrid, "Каталог блогеров"],
    ["/campaigns", Megaphone, "Кампании"],
    ["/chats", MessageSquare, "Сообщения"],
    ["/analytics", ChartNoAxesCombined, "Аналитика"],
  ];
  let content;
  if (!ready) content = <Loading />;
  else if (route.startsWith("/verify")) content = <Verify route={route} />;
  else if (route.startsWith("/oauth"))
    content = (
      <SocialExchange
        onLogin={(u) => {
          setUser(u);
          go("/profile");
        }}
      />
    );
  else if (route.startsWith("/login") || route === "/register")
    content = (
      <Auth
        register={route === "/register"}
        onLogin={(u) => {
          setUser(u);
          go("/");
        }}
      />
    );
  else if (route.startsWith("/bloggers/"))
    content = <BloggerDetail id={route.split("/")[2]} user={user} />;
  else if (route.startsWith("/chats/"))
    content = user ? (
      <Chat id={route.split("/")[2]} user={user} opts={opts} />
    ) : (
      <NeedLogin />
    );
  else if (route === "/chats") content = user ? <ChatList /> : <NeedLogin />;
  else if (route === "/campaigns")
    content = user ? <Campaigns user={user} /> : <NeedLogin />;
  else if (route === "/profile")
    content = user ? <Profile user={user} setUser={setUser} /> : <NeedLogin />;
  else if (route === "/notifications")
    content = user ? (
      <Notifications
        data={notifications}
        refresh={() =>
          api("notifications/").then((d) => setNotifications(rows(d)))
        }
      />
    ) : (
      <NeedLogin />
    );
  else if (route === "/analytics")
    content = user ? <Analytics /> : <NeedLogin />;
  else if (route === "/searches")
    content = user ? <SavedSearches /> : <NeedLogin />;
  else if (route === "/" || route.startsWith("/?"))
    content = <Catalog user={user} opts={opts} route={route} />;
  else
    content = (
      <Empty title="Страница не найдена">
        <a href="#/">Вернуться в каталог</a>
      </Empty>
    );
  return (
    <div className="app">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <a className="brand" href="#/">
          <span className="brand-symbol">
            b<span>•</span>
          </span>
          <span>
            blogger<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-mark">
            <Megaphone size={18} />
          </span>
          <div>
            <strong>Рабочее пространство</strong>
            <small>
              {user
                ? user.user_type === "blogger"
                  ? "Кабинет блогера"
                  : user.is_staff
                    ? "Модерация"
                    : "Кабинет рекламодателя"
                : "Платформа интеграций"}
            </small>
          </div>
        </div>
        <div className="nav-label">ПЛАТФОРМА</div>
        <nav>
          {links.map(([path, Icon, text]) => (
            <a
              key={path}
              className={
                (
                  path === "/"
                    ? route === "/" ||
                      route.startsWith("/?") ||
                      route.startsWith("/bloggers")
                    : route.startsWith(path)
                )
                  ? "active"
                  : ""
              }
              href={"#" + path}
            >
              <Icon size={19} />
              <span>{text}</span>
              {path === "/analytics" && <small className="pro">PRO</small>}
            </a>
          ))}
          {user && (
            <>
              <a
                href="#/searches"
                className={route === "/searches" ? "active" : ""}
              >
                <Bookmark size={19} />
                Сохранённые поиски
              </a>
              <a
                href="#/notifications"
                className={route === "/notifications" ? "active" : ""}
              >
                <Bell size={19} />
                Уведомления
                {unread > 0 && <small className="count">{unread}</small>}
              </a>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="trust-box">
            <ShieldCheck size={22} />
            <strong>Договорённости под контролем</strong>
            <p>ТЗ, переписка и все этапы сделки — в одном месте.</p>
            <a href="#/chats">
              Перейти к сделкам <ArrowUpRight size={14} />
            </a>
          </div>
          {user ? (
            <a className="account" href="#/profile">
              <Avatar name={user.username} id={user.id} />
              <span>
                <strong>{user.first_name || user.username}</strong>
                <small>
                  {user.user_type === "blogger"
                    ? "Блогер"
                    : user.is_staff
                      ? "Администратор"
                      : "Рекламодатель"}
                </small>
              </span>
              <Settings size={17} />
            </a>
          ) : (
            <a className="button secondary" href="#/login">
              Войти в аккаунт <ArrowRight size={16} />
            </a>
          )}
        </div>
      </aside>
      {mobile && (
        <button
          className="mobile-overlay"
          aria-label="Закрыть меню"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <IconButton label="Меню" onClick={() => setMobile(!mobile)}>
              <Menu size={21} />
            </IconButton>
            <span>Платформа</span>
            <ChevronRight size={14} />
            <strong>
              {links.find(([p]) =>
                p === "/"
                  ? route === "/" || route.startsWith("/?")
                  : route.startsWith(p),
              )?.[2] || "Личный кабинет"}
            </strong>
          </div>
          <div className="header-actions">
            <span className="live-dot" />{" "}
            <span className="header-caption">Ваши идеи. Их аудитория.</span>
            {user ? (
              <>
                <a
                  className="icon-button notification-button"
                  aria-label="Уведомления"
                  href="#/notifications"
                >
                  <Bell size={20} />
                  {unread > 0 && <i />}
                </a>
                <IconButton label="Выйти" onClick={logout}>
                  <LogOut size={18} />
                </IconButton>
              </>
            ) : (
              <a className="text-link" href="#/register">
                Создать аккаунт <ArrowUpRight size={15} />
              </a>
            )}
          </div>
        </header>
        <main>
          {notice && (
            <div className="info">
              {notice}
              <button onClick={() => setNotice("")}>×</button>
            </div>
          )}
          {content}
        </main>
        <footer>
          <span>© {new Date().getFullYear()} Blogger Marketplace</span>
          <span>
            От первого контакта до результата{" "}
            <span className="footer-dot">•</span> Сделано для сотрудничества
          </span>
        </footer>
      </div>
    </div>
  );
}

function Catalog({ user, opts, route }) {
  const initial = () =>
    Object.fromEntries(new URLSearchParams(route.split("?")[1] || ""));
  const [filters, setFilters] = useState(initial),
    [applied, setApplied] = useState(initial),
    [page, setPage] = useState(1),
    [showFilters, setShowFilters] = useState(false),
    [saveError, setSaveError] = useState(""),
    [saved, setSaved] = useState(false),
    [suggest, setSuggest] = useState([]);
  useEffect(() => {
    const v = Object.fromEntries(
      new URLSearchParams(route.split("?")[1] || ""),
    );
    setFilters(v);
    setApplied(v);
    setPage(1);
  }, [route]);
  const query = new URLSearchParams({
    ...Object.fromEntries(Object.entries(applied).filter(([, v]) => v !== "")),
    page,
  });
  const { data, error, loading } = useLoad("bloggers/?" + query);
  useEffect(() => {
    if (!filters.q) {
      setSuggest([]);
      return;
    }
    let active = true;
    const t = setTimeout(
      () =>
        api("bloggers/suggest/?q=" + encodeURIComponent(filters.q))
          .then((d) => active && setSuggest(d))
          .catch(() => {}),
      250,
    );
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [filters.q]);
  const update = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const submit = (e) => {
    e?.preventDefault();
    setApplied(filters);
    setPage(1);
    setSaved(false);
    setShowFilters(false);
  };
  const activeCount = Object.entries(applied).filter(
    ([k, v]) => v !== "" && k !== "ordering",
  ).length;
  const save = async () => {
    setSaveError("");
    try {
      await api("searches/", {
        method: "POST",
        body: {
          title: applied.q || applied.category || "Мой поиск",
          filters: applied,
        },
      });
      setSaved(true);
    } catch (e) {
      setSaveError(e.message);
    }
  };
  return (
    <>
      <PageHead
        eyebrow="СОЗДАВАЙТЕ ВМЕСТЕ"
        title="Найдите своего блогера"
        description="Те, кто расскажут о вашем бренде нужной аудитории."
      >
        <span className="page-chip">
          <span className="live-dot" /> Каталог авторов
        </span>
      </PageHead>
      <div className="catalog-hero">
        <div>
          <span className="hero-label">
            <Sparkles size={14} /> БОЛЬШЕ, ЧЕМ ПРОСТО РЕКЛАМА
          </span>
          <h2>
            Хорошие интеграции
            <br />
            начинаются с совпадения<span>.</span>
          </h2>
          <p>
            Выбирайте авторов по интересам, аудитории и бюджету.
            <br className="desktop-break" /> Обсуждайте идеи и двигайтесь к
            результату вместе.
          </p>
          <a href="#/campaigns">
            Создать кампанию <ArrowUpRight size={17} />
          </a>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-card art-back">
            <span className="art-bar" />
            <span className="art-bar short" />
            <div className="mini-chart">
              <i />
              <i />
              <i />
              <i />
              <i />
            </div>
          </div>
          <div className="art-card art-front">
            <div className="art-avatar">
              <Users size={28} />
            </div>
            <span className="art-bar" />
            <span className="art-bar short" />
            <div className="art-check">
              <Check size={14} /> Это мэтч!
            </div>
          </div>
          <span className="floating-star">✦</span>
          <span className="floating-dot" />
        </div>
      </div>
      <div className="catalog-layout">
        <aside className={`filters ${showFilters ? "expanded" : ""}`}>
          <div className="filter-title">
            <h3>
              <SlidersHorizontal size={17} />
              Фильтры
            </h3>
            <button
              onClick={() => {
                setFilters({});
                setApplied({});
                setPage(1);
                setSaved(false);
              }}
            >
              Сбросить
            </button>
          </div>
          <form onSubmit={submit}>
            <Select
              label="Площадка"
              value={filters.platform || ""}
              onChange={(e) => update("platform", e.target.value)}
            >
              <option value="">Все площадки</option>
              {opts.platforms.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </Select>
            <Select
              label="Тематика"
              value={filters.category || ""}
              onChange={(e) => update("category", e.target.value)}
            >
              <option value="">Все тематики</option>
              {opts.categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </Select>
            <Field
              label="Город"
              placeholder="Например, Москва"
              value={filters.city || ""}
              onChange={(e) => update("city", e.target.value)}
              list="cities"
            />
            <datalist id="cities">
              {opts.cities.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </datalist>
            <div className="field">
              <span>Цена за интеграцию, ₽</span>
              <div className="range-fields">
                <input
                  aria-label="Цена от"
                  type="number"
                  min="0"
                  placeholder="От"
                  value={filters.price_min || ""}
                  onChange={(e) => update("price_min", e.target.value)}
                />
                <span>—</span>
                <input
                  aria-label="Цена до"
                  type="number"
                  min="0"
                  placeholder="До"
                  value={filters.price_max || ""}
                  onChange={(e) => update("price_max", e.target.value)}
                />
              </div>
              <input
                aria-label="Максимальный бюджет"
                type="range"
                min="0"
                max="300000"
                step="1000"
                value={filters.price_max || 300000}
                onChange={(e) => update("price_max", e.target.value)}
              />
              <div className="range-labels">
                <span>0 ₽</span>
                <span>300 000 ₽</span>
              </div>
            </div>
            <div className="field">
              <span>Подписчики</span>
              <div className="range-fields">
                <input
                  aria-label="Подписчиков от"
                  type="number"
                  min="0"
                  placeholder="От"
                  value={filters.subscribers_min || ""}
                  onChange={(e) => update("subscribers_min", e.target.value)}
                />
                <span>—</span>
                <input
                  aria-label="Подписчиков до"
                  type="number"
                  min="0"
                  placeholder="До"
                  value={filters.subscribers_max || ""}
                  onChange={(e) => update("subscribers_max", e.target.value)}
                />
              </div>
            </div>
            <div className="filter-divider" />
            <Select
              label="Женская аудитория"
              value={filters.female_percent || ""}
              onChange={(e) => update("female_percent", e.target.value)}
            >
              <option value="">Любая доля</option>
              {[50, 70, 80, 90].map((p) => (
                <option value={p} key={p}>
                  От {p}%
                </option>
              ))}
            </Select>
            <Select
              label="Мужская аудитория"
              value={filters.male_percent || ""}
              onChange={(e) => update("male_percent", e.target.value)}
            >
              <option value="">Любая доля</option>
              {[50, 70, 80, 90].map((p) => (
                <option value={p} key={p}>
                  От {p}%
                </option>
              ))}
            </Select>
            <div className="field">
              <span>Возраст аудитории</span>
              <div className="range-fields">
                <input
                  aria-label="Возраст от"
                  type="number"
                  min="0"
                  max="100"
                  placeholder="От"
                  value={filters.age_min || ""}
                  onChange={(e) => update("age_min", e.target.value)}
                />
                <span>—</span>
                <input
                  aria-label="Возраст до"
                  type="number"
                  min="0"
                  max="100"
                  placeholder="До"
                  value={filters.age_max || ""}
                  onChange={(e) => update("age_max", e.target.value)}
                />
              </div>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={!!filters.verified}
                onChange={(e) =>
                  update("verified", e.target.checked ? "true" : "")
                }
              />
              Только проверенные <BadgeCheck size={15} />
            </label>
            <button className="button primary full">
              Показать блогеров <ArrowRight size={16} />
            </button>
          </form>
        </aside>
        <section className="results">
          <form className="search-bar" onSubmit={submit}>
            <Search size={20} />
            <input
              aria-label="Поиск блогера"
              placeholder="Имя или ник блогера"
              value={filters.q || ""}
              onChange={(e) => update("q", e.target.value)}
              list="blogger-suggestions"
            />
            <datalist id="blogger-suggestions">
              {suggest.map((s) => (
                <option key={s.id} value={s.user__username} />
              ))}
            </datalist>
            <button className="search-submit" aria-label="Найти">
              <ArrowRight size={19} />
            </button>
          </form>
          <div className="results-toolbar">
            <strong>
              {loading ? "Ищем авторов…" : `Авторов: ${data?.count || 0}`}
              <span> в каталоге</span>
            </strong>
            {user?.user_type === "advertiser" && (
              <button
                className="text-link export-link"
                onClick={() =>
                  downloadCatalog(applied).catch((e) => setSaveError(e.message))
                }
              >
                Экспорт CSV <ArrowUpRight size={14} />
              </button>
            )}
            <button
              className="filter-mobile"
              onClick={() => setShowFilters(!showFilters)}
            >
              <SlidersHorizontal size={16} />
              Фильтры
            </button>
            <select
              aria-label="Сортировка"
              value={applied.ordering || "-subscribers"}
              onChange={(e) => {
                const f = { ...applied, ordering: e.target.value };
                setApplied(f);
                setFilters(f);
                setPage(1);
              }}
            >
              <option value="-subscribers">По подписчикам ↓</option>
              <option value="subscribers">По подписчикам ↑</option>
              <option value="price">Сначала дешевле</option>
              <option value="-price">Сначала дороже</option>
              <option value="-rating">По рейтингу</option>
            </select>
          </div>
          {activeCount > 0 && (
            <div className="active-filters">
              <span>
                <Check size={13} /> Фильтров: {activeCount}
              </span>
              <button
                onClick={() => {
                  setFilters({});
                  setApplied({});
                  setPage(1);
                }}
              >
                Сбросить
              </button>
            </div>
          )}
          <ErrorBox text={error || saveError} />
          {loading ? (
            <Loading />
          ) : rows(data).length ? (
            <div className="blogger-grid">
              {rows(data).map((b) => (
                <BloggerCard key={b.id} b={b} />
              ))}
            </div>
          ) : (
            <Empty title="Пока нет совпадений">
              Попробуйте увеличить бюджет или убрать часть фильтров.
            </Empty>
          )}
          {data?.count > 24 && (
            <div className="pagination">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft size={17} />
              </button>
              <span>
                Страница {page} из {Math.ceil(data.count / 24)}
              </span>
              <button
                disabled={!data.next}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight size={17} />
              </button>
            </div>
          )}
          <div className="save-search">
            <span className="save-icon">
              <Bookmark size={21} />
            </span>
            <div>
              <strong>Ваш идеальный автор ещё впереди</strong>
              <p>Сохраните поиск — сообщим о новых совпадениях.</p>
            </div>
            <button
              className="button secondary"
              onClick={() => (user ? save() : go("/login"))}
              disabled={saved}
            >
              <Bookmark size={15} />
              {saved ? "Поиск сохранён" : "Сохранить поиск"}
            </button>
          </div>
        </section>
      </div>
    </>
  );
}
function BloggerCard({ b }) {
  return (
    <article className="blogger-card">
      <div className={`card-cover tone-${b.id % 5}`}>
        <span className="platform-label">
          <span className={`platform-dot ${b.platform.toLowerCase()}`} />
          {b.platform}
        </span>
        <a
          className="card-open"
          aria-label={"Открыть профиль " + b.display_name}
          href={"#/bloggers/" + b.id}
        >
          <ArrowUpRight size={17} />
        </a>
        <span className="cover-circle" />
      </div>
      <div className="card-body">
        <div className="card-identity">
          <Avatar
            name={b.display_name}
            id={b.id}
            size="large"
            src={b.avatar_url}
          />
          <span className="rating">
            <Star size={13} />
            {b.rating ? Number(b.rating).toFixed(1) : "Новый"}
          </span>
        </div>
        <a className="card-name" href={"#/bloggers/" + b.id}>
          {b.display_name}
          {b.is_verified && <BadgeCheck size={17} />}
        </a>
        <p className="handle">@{b.username}</p>
        <div className="card-meta">
          <span className="category">{b.category}</span>
          {b.city && (
            <span>
              <MapPin size={12} />
              {b.city}
            </span>
          )}
        </div>
        <div className="card-stats">
          <div>
            <span>Подписчики</span>
            <strong>{number(b.subscribers)}</strong>
          </div>
          <div>
            <span>Просмотры</span>
            <strong>{b.views ? number(b.views) : "—"}</strong>
          </div>
          <div>
            <span>ER</span>
            <strong>{b.engagement_rate ? b.engagement_rate + "%" : "—"}</strong>
          </div>
        </div>
        {b.rating && b.rating < 4 ? (
          <span className="badge warn">Внимание: низкий рейтинг</span>
        ) : (
          <Badge b={b} />
        )}
        <div className="card-bottom">
          <div>
            <span>Интеграция от</span>
            <strong>{money(b.price)}</strong>
          </div>
          <a className="button secondary small" href={"#/bloggers/" + b.id}>
            Подробнее <ArrowUpRight size={15} />
          </a>
        </div>
      </div>
    </article>
  );
}

function NeedLogin() {
  return (
    <Empty title="Войдите, чтобы продолжить" icon={UserRound}>
      <span>Кампании, сообщения и сделки доступны в вашем аккаунте.</span>
      <br />
      <a className="button primary" href="#/login">
        Войти в аккаунт <ArrowRight size={16} />
      </a>
    </Empty>
  );
}
function Auth({ register, onLogin }) {
  return (
    <div className="auth-layout">
      <div className="auth-intro">
        <span className="eyebrow">НОВЫЕ ВОЗМОЖНОСТИ</span>
        <h1>{register ? "Начнём с знакомства." : "С возвращением."}</h1>
        <p>
          Авторы и бренды, которые подходят друг другу.
          <br />
          Все договорённости — в одном пространстве.
        </p>
        <div className="auth-decoration">
          <MessageSquare size={80} />
          <span>Идея → контакт → результат</span>
        </div>
      </div>
      <div className="panel auth-panel">
        <h2>{register ? "Создать аккаунт" : "Вход в аккаунт"}</h2>
        <p className="muted">
          {register
            ? "Выберите роль и заполните данные."
            : "Продолжите работу с вашими интеграциями."}
        </p>
        {location.hash.includes("registered") && (
          <div className="info">
            Письмо отправлено. Подтвердите email перед входом.
          </div>
        )}
        <Form
          key={register ? "register" : "login"}
          button={register ? "Зарегистрироваться" : "Войти"}
          onSubmit={async (fd) => {
            const d = Object.fromEntries(fd);
            if (register) {
              await api("register/", { method: "POST", body: d });
              go("/login?registered");
            } else {
              const t = await api("login/", { method: "POST", body: d });
              sessionStorage.setItem("access", t.access);
              sessionStorage.setItem("refresh", t.refresh);
              onLogin(await api("me/"));
            }
          }}
        >
          <Field
            label="Имя пользователя"
            name="username"
            autoComplete="username"
            required
            maxLength="150"
          />
          {register && (
            <>
              <Field
                label="Email"
                name="email"
                type="email"
                autoComplete="email"
                required
              />
              <Select label="Ваша роль" name="user_type">
                <option value="advertiser">Рекламодатель</option>
                <option value="blogger">Блогер</option>
              </Select>
              <Select label="Тип аккаунта" name="account_type">
                <option value="person">Физическое лицо</option>
                <option value="company">Юридическое лицо</option>
              </Select>
              <Field
                label="ИНН (для юридического лица)"
                name="inn"
                inputMode="numeric"
                maxLength="12"
              />
              <p className="help">
                Проверяется формат и контрольная сумма ИНН. Проверка по реестру
                ФНС пока не подключена.
              </p>
            </>
          )}
          <Field
            label="Пароль"
            name="password"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            minLength={register ? 8 : 1}
            required
          />
          {register && (
            <p className="help">
              После регистрации отправим письмо для подтверждения email. Для
              локального запуска ссылка появится в консоли сервера.
            </p>
          )}
        </Form>
        <SocialButtons onLogin={onLogin} />
        {location.hash.includes("oauth_error") && (
          <ErrorBox text="Вход через соцсеть не завершён. Повторите попытку или используйте email. Если этот email уже зарегистрирован, войдите паролем и подключите соцсеть в профиле." />
        )}
        <p className="auth-switch">
          {register ? "Уже есть аккаунт? " : "Нет аккаунта? "}
          <a href={register ? "#/login" : "#/register"}>
            {register ? "Войти" : "Зарегистрироваться"}
          </a>
        </p>
      </div>
    </div>
  );
}
function SocialExchange({ onLogin }) {
  const [error, setError] = useState("");
  useEffect(() => {
    api("auth/exchange/", { method: "POST" })
      .then(async (t) => {
        sessionStorage.setItem("access", t.access);
        sessionStorage.setItem("refresh", t.refresh);
        if (location.hash.includes("stats=partial"))
          sessionStorage.setItem("stats-warning", "true");
        onLogin(await api("me/"));
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="panel narrow">
      <h2>Подключаем аккаунт</h2>
      {error ? <ErrorBox text={error} /> : <Loading />}
    </div>
  );
}

function SocialButtons({ onLogin, connect = false }) {
  const { data } = useLoad("options/");
  const [error, setError] = useState("");
  const target = useRef(null);
  const google = async (provider) => {
    try {
      const d = await api("auth/google/start/", {
        method: "POST",
        body: { provider },
      });
      location.assign(d.authorization_url);
    } catch (e) {
      setError(e.message);
    }
  };
  const telegram = async () => {
    try {
      const d = await api("auth/telegram/start/", { method: "POST" });
      window.bloggerTelegramLogin = async (auth) => {
        try {
          const t = await api("auth/telegram/login/", {
            method: "POST",
            body: { auth, nonce: d.nonce },
          });
          sessionStorage.setItem("access", t.access);
          sessionStorage.setItem("refresh", t.refresh);
          onLogin(await api("me/"));
        } catch (e) {
          setError(e.message);
        }
      };
      target.current.replaceChildren();
      const script = document.createElement("script");
      script.src = "https://telegram.org/js/telegram-widget.js?22";
      script.async = true;
      script.dataset.telegramLogin = d.bot_name;
      script.dataset.size = "large";
      script.dataset.onauth = "bloggerTelegramLogin(user)";
      target.current.appendChild(script);
    } catch (e) {
      setError(e.message);
    }
  };
  useEffect(
    () => () => {
      delete window.bloggerTelegramLogin;
    },
    [],
  );
  if (!data?.social_providers?.google && !data?.social_providers?.telegram)
    return null;
  return (
    <div className="social-buttons">
      <p className="help">
        {connect
          ? "Подключить статистику и вход"
          : "Для блогеров — вход через соцсеть"}
      </p>
      {data.social_providers.google && (
        <>
          <button
            type="button"
            className="button secondary"
            onClick={() => google("google")}
          >
            Google
          </button>
          <button
            type="button"
            className="button secondary"
            onClick={() => google("youtube")}
          >
            YouTube + статистика
          </button>
        </>
      )}
      {data.social_providers.telegram && !connect && (
        <button type="button" className="button secondary" onClick={telegram}>
          Telegram
        </button>
      )}
      <div ref={target} />
      <ErrorBox text={error} />
    </div>
  );
}

function Verify({ route }) {
  const token = new URLSearchParams(route.split("?")[1]).get("token");
  const [result, set] = useState(""),
    [error, err] = useState("");
  useEffect(() => {
    api("verify-email/", { method: "POST", body: { token } })
      .then((d) => set(d.detail))
      .catch((e) => err(e.message));
  }, [token]);
  return (
    <div className="panel narrow">
      <h1>Подтверждение email</h1>
      <ErrorBox text={error} />
      <p>{result || (!error && "Проверяем ссылку…")}</p>
      <a href="#/login" className="button primary">
        Перейти ко входу <ArrowRight size={16} />
      </a>
    </div>
  );
}

function BloggerDetail({ id, user }) {
  const { data: b, error, loading } = useLoad(`bloggers/${id}/`);
  const [sent, setSent] = useState(false);
  if (loading) return <Loading />;
  if (error) return <ErrorBox text={error} />;
  return (
    <>
      <a className="back-link" href="#/">
        <ChevronLeft size={15} /> В каталог
      </a>
      <div className="detail-layout">
        <section>
          <div className="panel profile-public">
            <div className={`profile-cover tone-${b.id % 5}`}>
              <span>{b.platform}</span>
              <span className="cover-circle" />
            </div>
            <div className="profile-info">
              <Avatar
                name={b.display_name}
                id={b.id}
                size="huge"
                src={b.avatar_url}
              />
              <Badge b={b} />
              <h1>{b.display_name}</h1>
              <div className="muted">
                @{b.username} · {b.category} {b.city && "· " + b.city}
              </div>
              {b.rating && (
                <p className={b.rating < 4 ? "warning-text" : "rating"}>
                  <Star size={16} />
                  {Number(b.rating).toFixed(1)} · Отзывов: {b.review_count}
                  {b.rating < 4 && " · Внимание: низкий рейтинг"}
                </p>
              )}
              <p className="bio">
                {b.bio || "Автор ещё не добавил описание профиля."}
              </p>
              {b.channel_url && (
                <a
                  className="text-link"
                  href={b.channel_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Открыть канал <ExternalLink size={15} />
                </a>
              )}
              <div className="stats-grid">
                <div>
                  <Users size={18} />
                  <strong>{number(b.subscribers)}</strong>
                  <span>подписчиков</span>
                </div>
                <div>
                  <ChartNoAxesCombined size={18} />
                  <strong>{number(b.views)}</strong>
                  <span>просмотров</span>
                </div>
                <div>
                  <Star size={18} />
                  <strong>{b.engagement_rate}%</strong>
                  <span>вовлечённость</span>
                </div>
              </div>
              <h3>Аудитория</h3>
              <div className="audience">
                <div>
                  <span>Женщины {b.female_percent}%</span>
                  <span>Мужчины {100 - b.female_percent}%</span>
                </div>
                <div className="audience-track">
                  <i style={{ width: b.female_percent + "%" }} />
                </div>
                <p className="muted">
                  Возраст: {b.age_min}–{b.age_max} лет · CPM:{" "}
                  {b.cpm ? money(b.cpm) : "нет данных"}
                </p>
              </div>
              <p className="help">
                Статистика{" "}
                {b.is_verified
                  ? "проверена администратором"
                  : "указана автором и не подтверждена API соцсети"}
                .
              </p>
              {b.forbidden_topics && (
                <div className="info">
                  <ShieldCheck size={18} />
                  <span>Не рекламирует: {b.forbidden_topics}</span>
                </div>
              )}
            </div>
          </div>
          <div className="panel">
            <h2>Отзывы и сотрудничество</h2>
            {b.reviews.length ? (
              b.reviews.map((r) => (
                <div className="review" key={r.id}>
                  <Avatar name={r.author_name} id={r.author} />
                  <div>
                    <strong>{r.author_name}</strong>
                    <span className="review-stars">
                      {"★".repeat(r.rating)}
                      {"☆".repeat(5 - r.rating)}
                    </span>
                    <p>{r.text || "Без комментария"}</p>
                  </div>
                </div>
              ))
            ) : (
              <Empty title="Первый отзыв ещё впереди" icon={Star}>
                Отзывы появятся после завершённых интеграций.
              </Empty>
            )}
          </div>
        </section>
        <aside className="panel proposal-panel">
          <span className="eyebrow">ОБСУДИМ СОТРУДНИЧЕСТВО</span>
          <h2>
            {money(b.price)} <small>за интеграцию</small>
          </h2>
          <p className="muted">
            Предложите идею и согласуйте условия напрямую с автором.
          </p>
          {sent ? (
            <div className="success">
              <CheckCircle2 size={20} /> Предложение отправлено. Продолжайте в
              сообщениях.<a href="#/chats">Открыть сообщения →</a>
            </div>
          ) : user?.user_type === "advertiser" ? (
            <Form
              button="Отправить предложение"
              onSubmit={async (fd) => {
                fd.set("blogger", b.id);
                if (!fd.get("attachment")?.size) fd.delete("attachment");
                const p = await api("proposals/", { method: "POST", body: fd });
                go("/chats/" + p.id);
                setSent(true);
              }}
            >
              <Field
                label="Ваша цена, ₽"
                name="price"
                type="number"
                min="1"
                max="1000000000"
                defaultValue={b.price || 1}
                required
              />
              <TextArea
                label="Идея и требования"
                name="message"
                placeholder="Расскажите о продукте, формате и сроках…"
              />
              <label className="field upload">
                <span>
                  <Paperclip size={15} /> Файл ТЗ (необязательно)
                </span>
                <input
                  type="file"
                  name="attachment"
                  accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
                />
              </label>
              <p className="help">Добавьте текст или файл. Файлы до 10 МБ.</p>
            </Form>
          ) : user ? (
            <div className="info">Предложения отправляют рекламодатели.</div>
          ) : (
            <a className="button primary full" href="#/login">
              Войти и предложить <ArrowRight size={16} />
            </a>
          )}
          <div className="proposal-note">
            <ShieldCheck size={19} />
            <span>
              ТЗ и договорённости сохранятся в переписке. При разногласиях
              доступен арбитраж.
            </span>
          </div>
        </aside>
      </div>
    </>
  );
}

function Pager({ data, page, setPage }) {
  if (!data || data.count <= 24) return null;
  return (
    <div className="pagination">
      <button
        aria-label="Предыдущая страница"
        disabled={!data.previous}
        onClick={() => setPage((p) => p - 1)}
      >
        <ChevronLeft size={17} />
      </button>
      <span>
        Страница {page} из {Math.ceil(data.count / 24)}
      </span>
      <button
        aria-label="Следующая страница"
        disabled={!data.next}
        onClick={() => setPage((p) => p + 1)}
      >
        <ChevronRight size={17} />
      </button>
    </div>
  );
}
function ChatList() {
  const [page, setPage] = useState(1);
  const { data, error, loading } = useLoad("proposals/?page=" + page);
  return (
    <>
      <PageHead
        eyebrow="НА СВЯЗИ"
        title="Сообщения и сделки"
        description="Все предложения, договорённости и результаты в одном месте."
      />
      <ErrorBox text={error} />
      {loading ? (
        <Loading />
      ) : rows(data).length ? (
        <div className="panel list-panel">
          {rows(data).map((p) => (
            <a className="chat-row" key={p.id} href={"#/chats/" + p.id}>
              <Avatar name={p.blogger_name} id={p.blogger} />
              <div>
                <strong>
                  {p.blogger_name}{" "}
                  <span className="muted">× {p.advertiser_name}</span>
                </strong>
                <p>{p.message || "Файл с техническим заданием"}</p>
              </div>
              <div className="chat-row-end">
                <strong>{money(p.counter_price || p.price)}</strong>
                <span
                  className={
                    "badge " + (p.status === "agreed" ? "good" : "neutral")
                  }
                >
                  {p.status === "agreed"
                    ? "Согласовано"
                    : p.status === "rejected"
                      ? "Отклонено"
                      : "Переговоры"}
                </span>
              </div>
              <ChevronRight size={18} />
            </a>
          ))}
        </div>
      ) : (
        <Empty title="Здесь начнётся сотрудничество" icon={MessageSquare}>
          Отправьте предложение из профиля блогера или дождитесь входящего
          запроса.
        </Empty>
      )}
      <Pager data={data} page={page} setPage={setPage} />
    </>
  );
}

function Chat({ id, user, opts }) {
  const { data: p, error, loading, refresh } = useLoad(`proposals/${id}/`),
    [actionError, setActionError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [refresh]);
  const act = async (path, body = {}) => {
    if (busy) return;
    setBusy(true);
    setActionError("");
    try {
      await api(path, { method: "POST", body });
      await refresh();
    } catch (e) {
      setActionError(e.message);
    } finally {
      setBusy(false);
    }
  };
  if (loading && !p) return <Loading />;
  if (!p) return <ErrorBox text={error} />;
  const d = p.deal,
    ad = user.id === p.advertiser,
    blogger = user.id === p.blogger_user_id,
    party = ad || blogger;
  return (
    <>
      <a className="back-link" href="#/chats">
        <ChevronLeft size={15} />
        Все сообщения
      </a>
      <PageHead
        eyebrow={"ПРЕДЛОЖЕНИЕ №" + p.id}
        title={`${p.blogger_name} × ${p.advertiser_name}`}
        description={
          "Создано " + new Date(p.created_at).toLocaleDateString("ru-RU")
        }
      />
      <ErrorBox text={error || actionError} />
      <div className="chat-layout">
        <section className="panel chat-panel">
          <div className="chat-title">
            <MessageSquare size={18} />
            <strong>Переписка</strong>
            <span className="muted">Только участники и поддержка</span>
          </div>
          <div className="messages">
            {p.messages.map((m) => (
              <div
                className={"message " + (m.sender === user.id ? "own" : "")}
                key={m.id}
              >
                <div className="message-meta">
                  <strong>{m.sender_name}</strong>
                  <time>
                    {new Date(m.created_at).toLocaleString("ru-RU", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                </div>
                <p>{m.text}</p>
                {m.attachment_name && (
                  <button
                    className="file-link"
                    onClick={() =>
                      downloadFile("message", m.id).catch((e) =>
                        setActionError(e.message),
                      )
                    }
                  >
                    <Paperclip size={14} />
                    {m.attachment_name}
                  </button>
                )}
              </div>
            ))}
          </div>
          <Form
            className="message-form"
            button="Отправить"
            onSubmit={async (fd, form) => {
              if (!fd.get("attachment")?.size) fd.delete("attachment");
              await api(`proposals/${id}/message/`, {
                method: "POST",
                body: fd,
              });
              form.reset();
              await refresh();
            }}
          >
            <TextArea
              label="Сообщение"
              name="text"
              placeholder="Обсудите детали или приложите материалы…"
            />
            <label className="field">
              <span>
                <Paperclip size={14} />
                Прикрепить файл
              </span>
              <input
                type="file"
                name="attachment"
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
              />
            </label>
          </Form>
        </section>
        <aside>
          <div className="panel deal-panel">
            <h3>Условия интеграции</h3>
            <span className="muted">
              {p.counter_price ? "Встречная цена" : "Предложенная цена"}
            </span>
            <div className="deal-price">
              {money(p.counter_price || p.price)}
            </div>
            {p.attachment_name && (
              <button
                className="file-link"
                onClick={() =>
                  downloadFile("brief", p.id).catch((e) =>
                    setActionError(e.message),
                  )
                }
              >
                <Paperclip size={15} />
                {p.attachment_name}
              </button>
            )}
            {p.status === "sent" && party && (
              <>
                <div className="info">
                  Согласуйте стоимость до начала работы.
                </div>
                {(p.last_offer_by || p.advertiser) !== user.id && (
                  <button
                    disabled={busy}
                    className="button primary full"
                    onClick={() =>
                      act(`proposals/${id}/negotiate/`, { action: "accept" })
                    }
                  >
                    <Check size={16} />
                    Принять условия
                  </button>
                )}
                <Form
                  button="Предложить цену"
                  onSubmit={async (fd) => {
                    await api(`proposals/${id}/negotiate/`, {
                      method: "POST",
                      body: { action: "counter", price: fd.get("price") },
                    });
                    await refresh();
                  }}
                >
                  <Field
                    label="Встречная цена, ₽"
                    name="price"
                    type="number"
                    min="1"
                    max="1000000000"
                    required
                  />
                </Form>
                <button
                  className="button ghost full"
                  disabled={busy}
                  onClick={() =>
                    act(`proposals/${id}/negotiate/`, { action: "reject" })
                  }
                >
                  Отклонить предложение
                </button>
              </>
            )}
            {p.status === "rejected" && (
              <div className="info">Предложение отклонено.</div>
            )}
            {d && (
              <>
                <div className={"deal-status status-" + d.status}>
                  <span className="live-dot" />
                  {d.status_label}
                </div>
                <div className="deal-summary">
                  <span>
                    Стоимость<strong>{money(d.amount)}</strong>
                  </span>
                  <span>
                    Комиссия сервиса<strong>{money(d.commission)}</strong>
                  </span>
                  <span>
                    Автору после приёмки
                    <strong>{money(d.amount - d.commission)}</strong>
                  </span>
                </div>
                {(d.is_test || opts.payment_mode === "test") && (
                  <div className="test-label">
                    <AlertCircle size={16} />
                    Тестовый режим. Реальные деньги не списываются и не
                    переводятся.
                  </div>
                )}
                {d.status === "awaiting_payment" &&
                  ad &&
                  (opts.payment_mode === "test" ? (
                    <button
                      disabled={busy}
                      className="button primary full"
                      onClick={() => act(`deals/${d.id}/pay/`)}
                    >
                      <Wallet size={17} />
                      Создать тестовый резерв
                    </button>
                  ) : (
                    <div className="info">
                      Платёжный провайдер пока не подключён. Реальная оплата
                      недоступна.
                    </div>
                  ))}
                {["in_progress", "revision"].includes(d.status) && blogger && (
                  <Form
                    button="Сдать работу"
                    onSubmit={async (fd) => {
                      await api(`deals/${d.id}/submit/`, {
                        method: "POST",
                        body: Object.fromEntries(fd),
                      });
                      await refresh();
                    }}
                  >
                    <Field
                      label="Ссылка на публикацию"
                      name="publication_url"
                      type="url"
                      placeholder="https://…"
                      required
                    />
                  </Form>
                )}
                {d.revision_reason && (
                  <div className="info">Замечания: {d.revision_reason}</div>
                )}
                {d.publication_url && (
                  <a
                    className="publication-link"
                    href={d.publication_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink size={16} />
                    Посмотреть публикацию
                  </a>
                )}
                {d.status === "submitted" && (
                  <p className="help">
                    Автоприёмка через 3 дня после последней сдачи, если нет
                    доработки или спора.
                  </p>
                )}
                {d.status === "submitted" && ad && (
                  <>
                    <button
                      disabled={busy}
                      className="button primary full"
                      onClick={() => act(`deals/${d.id}/accept/`)}
                    >
                      <Check size={17} />
                      Принять работу
                    </button>
                    <Form
                      button="Отправить на доработку"
                      onSubmit={async (fd) => {
                        await api(`deals/${d.id}/revise/`, {
                          method: "POST",
                          body: { reason: fd.get("reason") },
                        });
                        await refresh();
                      }}
                    >
                      <TextArea label="Что исправить?" name="reason" required />
                    </Form>
                  </>
                )}
                {["in_progress", "submitted", "revision"].includes(d.status) &&
                  ad && (
                    <details className="dispute-details">
                      <summary>Открыть спор</summary>
                      <Form
                        button="Открыть спор"
                        onSubmit={async (fd) => {
                          if (!fd.get("evidence")?.size) fd.delete("evidence");
                          await api(`deals/${d.id}/dispute/`, {
                            method: "POST",
                            body: fd,
                          });
                          await refresh();
                        }}
                      >
                        <TextArea
                          label="Причина спора"
                          name="reason"
                          required
                        />
                        <Field
                          label="Доказательства (до 10 МБ)"
                          name="evidence"
                          type="file"
                          accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
                        />
                      </Form>
                    </details>
                  )}
                {p.dispute && (
                  <div className="dispute-block">
                    <h3>Спор №{p.dispute.id}</h3>
                    <p>{p.dispute.reason}</p>
                    {p.dispute.evidence_name && (
                      <button
                        className="file-link"
                        onClick={() =>
                          downloadFile("evidence", p.dispute.id).catch((e) =>
                            setActionError(e.message),
                          )
                        }
                      >
                        Скачать доказательства
                      </button>
                    )}
                    {p.dispute.resolution ? (
                      <p>Решение: {p.dispute.resolution}</p>
                    ) : (
                      <p className="help">
                        Резерв заблокирован. Поддержка может запросить
                        дополнительные материалы в переписке.
                      </p>
                    )}
                    {user.is_staff && !p.dispute.resolved_at && (
                      <Form
                        button="Вынести решение"
                        onSubmit={async (fd) => {
                          await api(`disputes/${p.dispute.id}/resolve/`, {
                            method: "POST",
                            body: Object.fromEntries(fd),
                          });
                          await refresh();
                        }}
                      >
                        <Select label="Решение" name="decision">
                          <option value="blogger">В пользу блогера</option>
                          <option value="advertiser">
                            Вернуть рекламодателю
                          </option>
                        </Select>
                        <TextArea
                          label="Обоснование"
                          name="resolution"
                          required
                        />
                      </Form>
                    )}
                  </div>
                )}
                {d.status === "completed" &&
                  party &&
                  !p.reviews.some((r) => r.author === user.id) && (
                    <Form
                      button="Оставить отзыв"
                      onSubmit={async (fd) => {
                        await api("reviews/", {
                          method: "POST",
                          body: { ...Object.fromEntries(fd), deal: d.id },
                        });
                        await refresh();
                      }}
                    >
                      <Select label="Оценка партнёра" name="rating">
                        {[5, 4, 3, 2, 1].map((v) => (
                          <option key={v} value={v}>
                            {v} {"★".repeat(v)}
                          </option>
                        ))}
                      </Select>
                      <TextArea label="Ваш отзыв" name="text" />
                    </Form>
                  )}
                {p.reviews.length > 0 && (
                  <div>
                    <h3>Отзывы по сделке</h3>
                    {p.reviews.map((r) => (
                      <div className="review" key={r.id}>
                        <div>
                          <strong>
                            {r.author_name} · {r.rating} ★
                          </strong>
                          <p>{r.text || "Без комментария"}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

function Campaigns({ user }) {
  const [page, setPage] = useState(1);
  const { data, error, loading, refresh } = useLoad("campaigns/?page=" + page),
    [create, setCreate] = useState(false);
  return (
    <>
      <PageHead
        eyebrow="ОТ ИДЕИ К РЕЗУЛЬТАТУ"
        title="Рекламные кампании"
        description={
          user.user_type === "blogger"
            ? "Подобранные для вас проекты по теме, аудитории и бюджету."
            : "Создайте бриф — поможем найти подходящих авторов."
        }
      >
        {user.user_type === "advertiser" && (
          <button className="button primary" onClick={() => setCreate(!create)}>
            <Plus size={17} />
            {create ? "Закрыть форму" : "Новая кампания"}
          </button>
        )}
      </PageHead>
      <ErrorBox text={error} />
      {create && (
        <div className="panel">
          <h2>Новая кампания</h2>
          <Form
            button="Создать и подобрать блогеров"
            onSubmit={async (fd) => {
              await api("campaigns/", {
                method: "POST",
                body: Object.fromEntries(fd),
              });
              setCreate(false);
              await refresh();
            }}
          >
            <div className="form-grid">
              <Field label="Название" name="title" required maxLength="160" />
              <Field label="Тематика" name="category" required />
              <Field
                label="Общий бюджет, ₽"
                name="budget"
                type="number"
                min="1"
                required
              />
              <Field label="Город (необязательно)" name="city" />
              <Field label="Начало" name="starts_at" type="date" required />
              <Field label="Окончание" name="ends_at" type="date" required />
              <Field
                label="Минимум подписчиков"
                name="min_subscribers"
                type="number"
                min="0"
                defaultValue="0"
              />
              <Field
                label="Женская аудитория от, %"
                name="female_percent"
                type="number"
                min="0"
                max="100"
                defaultValue="0"
              />
            </div>
            <TextArea
              label="Продукт, формат и требования"
              name="description"
              required
            />
          </Form>
        </div>
      )}
      {loading ? (
        <Loading />
      ) : rows(data).length ? (
        <div className="campaign-grid">
          {rows(data).map((c) => (
            <article className="panel campaign-card" key={c.id}>
              <span className="category">{c.category}</span>
              <h2>{c.title}</h2>
              <p>{c.description}</p>
              <div className="campaign-budget">
                {money(c.budget)} <small>бюджет</small>
              </div>
              <div className="muted">
                {c.starts_at} → {c.ends_at}
              </div>
              {user.user_type === "advertiser" ? (
                <>
                  <p className="help">
                    Подобрано блогеров: {c.matched_bloggers.length}. Если
                    совпадений нет, проверим новые профили позже.
                  </p>
                  <a
                    className="text-link"
                    href={
                      "#/?category=" +
                      encodeURIComponent(c.category) +
                      "&price_max=" +
                      c.budget
                    }
                  >
                    Перейти к подбору <ArrowUpRight size={15} />
                  </a>
                </>
              ) : (
                <CampaignRespond id={c.id} />
              )}
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Пока нет кампаний" icon={Megaphone}>
          {user.user_type === "advertiser"
            ? "Создайте первую кампанию и начните подбор блогеров."
            : "Когда появится подходящий проект, вы получите уведомление."}
        </Empty>
      )}
      <Pager data={data} page={page} setPage={setPage} />
    </>
  );
}
function CampaignRespond({ id }) {
  const [result, set] = useState(""),
    [error, err] = useState("");
  return (
    <>
      <button
        className="button secondary"
        disabled={!!result}
        onClick={async () => {
          try {
            await api(`campaigns/${id}/respond/`, { method: "POST" });
            set("Интерес отправлен рекламодателю");
          } catch (e) {
            err(e.message);
          }
        }}
      >
        Откликнуться <ArrowUpRight size={15} />
      </button>
      {result && <p className="success">{result}</p>}
      <ErrorBox text={error} />
    </>
  );
}
function Profile({ user, setUser }) {
  const { data, error, loading } = useLoad(
    user.user_type === "blogger" ? "profile/" : "me/",
  );
  return (
    <>
      <PageHead
        eyebrow="ВАШЕ ПРОСТРАНСТВО"
        title="Профиль и настройки"
        description="Актуальная информация помогает находить подходящие проекты."
      />
      <div className="settings-layout">
        <div className="panel">
          <h2>Данные аккаунта</h2>
          <Form
            button="Сохранить аккаунт"
            successText="Настройки сохранены"
            onSubmit={async (fd) => {
              const d = Object.fromEntries(fd);
              d.notifications_enabled =
                fd.get("notifications_enabled") === "on";
              const u = await api("me/", { method: "PATCH", body: d });
              setUser(u);
            }}
          >
            <Field
              label="Имя"
              name="first_name"
              defaultValue={user.first_name}
            />
            <Field label="Телефон" name="phone" defaultValue={user.phone} />
            <p className="muted">
              Email: {user.email}{" "}
              {user.email_verified ? "· подтверждён" : "· не подтверждён"}
            </p>
            {!user.email_verified && <ResendEmail email={user.email} />}
            <label className="checkbox">
              <input
                name="notifications_enabled"
                type="checkbox"
                defaultChecked={user.notifications_enabled}
              />
              Уведомления в браузере
            </label>
            <button
              className="button secondary"
              type="button"
              onClick={async () => {
                if ("Notification" in window)
                  await Notification.requestPermission();
              }}
            >
              Разрешить уведомления браузера
            </button>
            <p className="help">
              Уведомления работают, пока приложение открыто. Системный Web Push
              пока не подключён.
            </p>
          </Form>
        </div>
        {user.user_type === "blogger" && (
          <div className="panel">
            <h2>Публичный профиль</h2>
            {sessionStorage.getItem("stats-warning") && (
              <div className="info">
                Не удалось загрузить всю статистику YouTube. Аккаунт сохранён.
                Заполните данные вручную или подключите канал повторно позже.
              </div>
            )}
            <SocialButtons connect onLogin={setUser} />
            <ErrorBox text={error} />
            {loading ? (
              <Loading />
            ) : (
              <Form
                button="Сохранить профиль"
                successText="Профиль обновлён"
                onSubmit={async (fd) => {
                  await api("profile/", {
                    method: "PATCH",
                    body: Object.fromEntries(fd),
                  });
                }}
              >
                <div className="form-grid">
                  <Select
                    label="Площадка"
                    name="platform"
                    defaultValue={data.platform}
                  >
                    {["Telegram", "YouTube", "TikTok"].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </Select>
                  <Field
                    label="Ссылка на канал"
                    name="channel_url"
                    type="url"
                    defaultValue={data.channel_url}
                  />
                  <Field
                    label="Тематика"
                    name="category"
                    defaultValue={data.category}
                    required
                  />
                  <Field label="Город" name="city" defaultValue={data.city} />
                  {[
                    ["subscribers", "Подписчики"],
                    ["views", "Средние просмотры"],
                    ["price", "Цена интеграции, ₽"],
                    ["engagement_rate", "ER, %"],
                    ["female_percent", "Женская аудитория, %"],
                    ["age_min", "Возраст аудитории от"],
                    ["age_max", "Возраст аудитории до"],
                  ].map(([name, label]) => (
                    <Field
                      key={name}
                      label={label}
                      name={name}
                      type="number"
                      min="0"
                      step={name === "engagement_rate" ? ".1" : "1"}
                      max={
                        [
                          "female_percent",
                          "engagement_rate",
                          "age_min",
                          "age_max",
                        ].includes(name)
                          ? 100
                          : 1000000000
                      }
                      defaultValue={data[name]}
                    />
                  ))}
                </div>
                <TextArea label="О себе" name="bio" defaultValue={data.bio} />
                <TextArea
                  label="Запрещённые темы (через запятую)"
                  name="forbidden_topics"
                  defaultValue={data.forbidden_topics}
                />
                <TextArea
                  label="Автоответ на первое предложение"
                  name="reply_template"
                  defaultValue={data.reply_template}
                />
                <p className="help">
                  Ручная статистика будет отмечена как непроверенная. Для
                  автоматического импорта понадобится подключение API соцсети.
                </p>
              </Form>
            )}
          </div>
        )}
      </div>
    </>
  );
}
function ResendEmail({ email }) {
  const [msg, set] = useState("");
  return (
    <>
      <button
        type="button"
        className="text-link"
        onClick={async () => {
          try {
            const r = await api("resend-email/", {
              method: "POST",
              body: { email },
            });
            set(r.detail);
          } catch (e) {
            set(e.message);
          }
        }}
      >
        Отправить письмо подтверждения
      </button>
      {msg && <p className="help">{msg}</p>}
    </>
  );
}
function Notifications({ data: latest, refresh: refreshHeader }) {
  const [page, setPage] = useState(1);
  const result = useLoad(
    "notifications/?page=" + page,
    String(latest[0]?.id) + ":" + latest.filter((n) => !n.is_read).length,
  );
  const data = rows(result.data);
  const refresh = () => {
    result.refresh();
    refreshHeader();
  };
  return (
    <>
      <PageHead
        eyebrow="НИЧЕГО НЕ УПУСТИТЕ"
        title="Уведомления"
        description="Новые предложения, сообщения и изменения статуса сделок."
      >
        <button
          className="button secondary"
          onClick={async () => {
            await api("notifications/read_all/", { method: "POST" });
            refresh();
          }}
        >
          <CheckCheck size={17} />
          Прочитать все
        </button>
      </PageHead>
      <div className="panel list-panel">
        {data.length ? (
          data.map((n) => (
            <a
              className={"notification-row " + (!n.is_read ? "unread" : "")}
              href={n.link || "#/notifications"}
              key={n.id}
              onClick={() => {
                api(`notifications/${n.id}/`, {
                  method: "PATCH",
                  body: { is_read: true },
                })
                  .then(refresh)
                  .catch(() => {});
              }}
            >
              <span className="notification-icon">
                <Bell size={18} />
              </span>
              <div>
                <strong>{n.text}</strong>
                <p>{new Date(n.created_at).toLocaleString("ru-RU")}</p>
              </div>
              {!n.is_read && <i className="unread-dot" />}
            </a>
          ))
        ) : (
          <Empty title="Вы в курсе всего" icon={Bell}>
            Здесь появятся уведомления о вашей работе.
          </Empty>
        )}
      </div>
      <Pager data={result.data} page={page} setPage={setPage} />
    </>
  );
}
function SavedSearches() {
  const [page, setPage] = useState(1);
  const { data, error, loading, refresh } = useLoad("searches/?page=" + page);
  return (
    <>
      <PageHead
        eyebrow="ПОДХОДЯЩИЕ АВТОРЫ"
        title="Сохранённые поиски"
        description="Возвращайтесь к своим подборкам и следите за новыми совпадениями."
      />
      <ErrorBox text={error} />
      {loading ? (
        <Loading />
      ) : (
        <div className="panel list-panel">
          {rows(data).length ? (
            rows(data).map((s) => (
              <div className="saved-row" key={s.id}>
                <Bookmark size={19} />
                <div>
                  <a href={"#/?" + new URLSearchParams(s.filters)}>{s.title}</a>
                  <p>
                    {Object.entries(s.filters)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ") || "Все блогеры"}
                  </p>
                </div>
                <button
                  className="icon-button"
                  aria-label="Удалить поиск"
                  onClick={() =>
                    api(`searches/${s.id}/`, { method: "DELETE" }).then(refresh)
                  }
                >
                  <X size={17} />
                </button>
              </div>
            ))
          ) : (
            <Empty title="Сохраните первый поиск" icon={Bookmark}>
              Настройте фильтры в каталоге и нажмите «Сохранить поиск».
            </Empty>
          )}
        </div>
      )}
      <Pager data={data} page={page} setPage={setPage} />
    </>
  );
}
function Analytics() {
  const { data, error, loading } = useLoad("analytics/");
  return (
    <>
      <PageHead
        eyebrow="РЕШЕНИЯ НА ОСНОВЕ ДАННЫХ"
        title="Аналитика рынка"
        description="Средняя стоимость интеграций и CPM по тематикам. Премиум-доступ."
      />
      {error ? (
        <div className="panel">
          <ChartNoAxesCombined size={36} />
          <h2>Больше данных для ваших решений</h2>
          <p>{error}</p>
          <p className="help">
            Администратор управляет премиум-доступом в панели пользователей.
          </p>
        </div>
      ) : loading ? (
        <Loading />
      ) : (
        <div className="panel">
          <h2>Стоимость по категориям</h2>
          <p className="help">
            Расчёт по текущей базе и указанным просмотрам. Самостоятельно
            заполненные данные могут быть неточны.
          </p>
          {rows(data).length ? (
            <div className="analytics-table">
              <table>
                <thead>
                  <tr>
                    <th>Категория</th>
                    <th>Авторов</th>
                    <th>Средняя цена</th>
                    <th>Средний CPM</th>
                    <th>Сравнение CPM</th>
                  </tr>
                </thead>
                <tbody>
                  {rows(data).map((d) => (
                    <tr key={d.category}>
                      <td>{d.category}</td>
                      <td>{d.count}</td>
                      <td>{money(Math.round(d.average_price))}</td>
                      <td>{money(Math.round(d.average_cpm))}</td>
                      <td>
                        <div className="chart-track">
                          <i
                            style={{
                              width:
                                Math.max(
                                  2,
                                  (d.average_cpm /
                                    Math.max(
                                      ...data.map((r) => r.average_cpm),
                                    )) *
                                    100,
                                ) + "%",
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty title="Недостаточно данных" icon={ChartNoAxesCombined}>
              Для расчёта CPM авторам нужно указать просмотры и цены.
            </Empty>
          )}
        </div>
      )}
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);

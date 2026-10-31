import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  House,
  ListTodo,
  NotebookPen,
  Package,
  Plane,
  Layers,
  Table2,
  BriefcaseBusiness,
  Building2,
  Plus,
  ArrowUpRight,
  ArrowLeft,
  Pencil,
  Trash2,
  Check,
  X,
  Download,
  Share2,
  Upload,
  FileText,
  ChevronRight,
  LogOut,
  ShieldCheck,
  Save,
  Search,
  Wallet,
  FolderOpen,
  CalendarDays,
} from "lucide-react";
import "./style.css";
const pages = [
  ["home", "Home", House],
  ["tasks", "To Do List", ListTodo],
  ["meetings", "Meeting Minutes", NotebookPen],
  ["warehouse", "Warehouse", Package],
  ["mission", "Mission Report", Plane],
  ["development", "Rah Nia Development", Layers],
  ["bom", "BOM", Table2],
  ["employer", "Employer Report", BriefcaseBusiness],
  ["projects", "RNG Projects", Building2],
];
const clone = (x) => structuredClone(x),
  uid = () => crypto.randomUUID(),
  now = () => new Date().toISOString();
const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
const solar = () =>
  new Intl.DateTimeFormat("en-US-u-ca-persian", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .format(new Date())
    .replace(/(\d+)\/(\d+)\/(\d+)/, "$3/$1/$2");
const money = (x) => BigInt(String(x || 0)).toLocaleString("en-US");
const categories = ["متریال", "اجرت", "خدمات", "سایر", "دریافتی"];
const ascii = (x) =>
  String(x)
    .replace(/[۰-۹]/g, (c) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(c)))
    .replace(/[٠-٩]/g, (c) => String("٠١٢٣٤٥٦٧٨٩".indexOf(c)));
const integer = (x) => ascii(x).replace(/[,٬\s]/g, "");
function url(parts) {
  return "#/" + parts.map(encodeURIComponent).join("/");
}
function go(...parts) {
  location.hash = url(parts);
}
function useRoute() {
  const read = () =>
    location.hash.slice(2).split("/").filter(Boolean).map(decodeURIComponent);
  const [r, set] = useState(read);
  useEffect(() => {
    const fn = () => {
      set(read());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);
  return r;
}
function BrandLogo({ className = "" }) {
  return (
    <img
      className={"rng-logo " + className}
      src="/brand/rng-192.png?v=rng2"
      alt="RNG Logo"
      width="64"
      height="64"
    />
  );
}
function Button({ children, icon: Icon, kind = "", ...props }) {
  return (
    <button className={"button " + kind} {...props}>
      {Icon && <Icon size={18} />}
      <span>{children}</span>
    </button>
  );
}
function Field({ label, value, onChange, area = false, ...props }) {
  return (
    <label className={"field " + (area ? "wide" : "")}>
      <span>{label}</span>
      {area ? (
        <textarea
          aria-label={label}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          {...props}
        />
      ) : (
        <input
          aria-label={label}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          {...props}
        />
      )}
    </label>
  );
}
function Select({ label, value, onChange, options }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select
        aria-label={label}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}
function Empty({
  title = "A little space for your next idea.",
  text = "Create your first record to get started.",
}) {
  return (
    <div className="empty">
      <FolderOpen size={34} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
function Modal({ title, children, onClose }) {
  const box = useRef();
  useEffect(() => {
    const prev = document.activeElement;
    box.current?.focus();
    const key = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = box.current.querySelectorAll(
          'button,input,textarea,select,a[href],[tabindex="0"]',
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prev?.focus();
    };
  }, []);
  return (
    <div className="overlay">
      <section
        className="modal"
        ref={box}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="row between">
          <h2>{title}</h2>
          <Button icon={X} aria-label="Close" onClick={onClose} />
        </div>
        {children}
      </section>
    </div>
  );
}
function Confirm({ title, onConfirm, onClose, busy }) {
  return (
    <Modal title="Delete this record?" onClose={onClose}>
      <p className="warning">
        “{title}” will be permanently deleted. This cannot be undone.
      </p>
      <div className="actions">
        <Button onClick={onClose}>Cancel</Button>
        <Button kind="danger" disabled={busy} onClick={onConfirm} icon={Trash2}>
          Delete permanently
        </Button>
      </div>
    </Modal>
  );
}
function DraftGuard({ dirty = true }) {
  useEffect(() => {
    if (!dirty) return;
    const fn = (e) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", fn);
    const click = (e) => {
      if (
        e.target.closest('a[href^="#/"]') &&
        !window.confirm("Leave this page and discard unsaved changes?")
      )
        e.preventDefault();
    };
    document.addEventListener("click", click);
    return () => {
      window.removeEventListener("beforeunload", fn);
      document.removeEventListener("click", click);
    };
  }, [dirty]);
  return null;
}
async function fetchApi(path, options = {}) {
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
  });
  if (!response.ok) {
    let error;
    try {
      error = (await response.json()).detail;
    } catch {}
    throw new Error(
      typeof error === "string"
        ? error
        : response.status === 401
          ? "Please sign in again."
          : "The request could not be completed.",
    );
  }
  return response;
}
async function downloadOrShare(blob, name, share = false) {
  const file = new File([blob], name, { type: blob.type });
  if (share && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: name });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 60000);
}
function PdfActions({ kind, id, notify }) {
  const [busy, setBusy] = useState(false);
  async function action(share) {
    setBusy(true);
    try {
      const blob = await (
        await fetchApi(`/report/${kind}/${encodeURIComponent(id)}`)
      ).blob();
      await downloadOrShare(blob, `RNG-${kind}-report.pdf`, share);
    } catch (e) {
      notify(e.message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="actions">
      <Button icon={Download} disabled={busy} onClick={() => action(false)}>
        Download PDF
      </Button>
      <Button icon={Share2} disabled={busy} onClick={() => action(true)}>
        Share PDF
      </Button>
    </div>
  );
}
function App() {
  const route = useRoute();
  const page = route[0] || "home";
  const [csrf, setCsrf] = useState(null),
    [state, setState] = useState(null),
    [checking, setChecking] = useState(true),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(null);
  const version = useRef(null),
    saving = useRef(false);
  function notify(message, error = false) {
    setNotice({ message, error });
  }
  async function load() {
    const data = await (await fetchApi("/state")).json();
    version.current = data.version;
    setState(data.state);
  }
  useEffect(() => {
    (async () => {
      try {
        const session = await (await fetchApi("/session")).json();
        setCsrf(session.csrf);
        await load();
      } catch {
      } finally {
        setChecking(false);
      }
    })();
    if ("serviceWorker" in navigator)
      navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), notice.error ? 15000 : 4000);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    const nav = document.querySelector(".bottom-nav");
    const active = nav?.querySelector("a.active");
    if (nav?.clientWidth && active)
      nav.scrollTo({
        left: active.offsetLeft - nav.clientWidth / 2 + active.clientWidth / 2,
        behavior: "smooth",
      });
  }, [page, !!state]);
  async function save(sections) {
    if (saving.current) throw new Error("Please wait for the current save.");
    saving.current = true;
    setBusy(true);
    try {
      const data = await (
        await fetchApi("/state", {
          method: "PATCH",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify({ version: version.current, sections }),
        })
      ).json();
      version.current = data.version;
      setState((s) => ({ ...s, ...sections }));
      notify("Changes saved.");
    } catch (e) {
      notify(e.message, true);
      throw e;
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await fetchApi("/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": csrf },
      });
      setState(null);
      setCsrf(null);
      go("home");
    } catch (e) {
      notify(e.message, true);
    }
  }
  if (checking)
    return (
      <div className="loading">
        <BrandLogo className="loading-logo" />
        <p>Opening your workspace…</p>
      </div>
    );
  if (!csrf || !state)
    return (
      <Login
        onLogin={async (token) => {
          setCsrf(token);
          await load();
        }}
      />
    );
  const context = { state, save, busy, notify };
  const current = pages.find((p) => p[0] === page) || pages[0];
  return (
    <>
      <header className="topbar">
        <a className="brand" href="#/home">
          <BrandLogo className="header-logo" />
          <span>
            MY DASHBOARD<small>PERSONAL WORKSPACE</small>
          </span>
        </a>
        <div className="top-actions">
          <span className="private">
            <ShieldCheck size={15} />
            Private workspace
          </span>
          <Button icon={LogOut} onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      {page !== "home" && (
        <nav className="desktop-nav" aria-label="Sections">
          {pages.map(([key, title, Icon]) => (
            <a
              className={page === key ? "active" : ""}
              href={url([key])}
              key={key}
            >
              <Icon size={16} />
              {title}
            </a>
          ))}
        </nav>
      )}
      <main className={page === "home" ? "home" : "workspace"}>
        {page === "home" ? (
          <Home {...context} />
        ) : (
          <>
            <div className="page-heading">
              <div>
                <span className="eyebrow">
                  YOUR WORKSPACE / {current[1].toUpperCase()}
                </span>
                <h1>{current[1]}</h1>
              </div>
            </div>
            {page === "tasks" || page === "development" ? (
              <Tasks
                key={page}
                section={page === "tasks" ? "tasks" : "development_tasks"}
                {...context}
              />
            ) : ["meetings", "warehouse", "mission", "bom"].includes(page) ? (
              <Records
                key={page + "-" + (route[1] || "")}
                kind={page}
                recordId={route[1]}
                {...context}
              />
            ) : page === "projects" ? (
              <Projects key={route.join("/")} route={route} {...context} />
            ) : (
              <Empty
                title="Employer Report"
                text="This section was a placeholder in your original dashboard."
              />
            )}
          </>
        )}
      </main>
      <nav className="bottom-nav" aria-label="Mobile sections">
        {pages.map(([key, title, Icon]) => (
          <a
            key={key}
            className={page === key ? "active" : ""}
            href={url([key])}
          >
            <Icon size={23} />
            <span>{title}</span>
          </a>
        ))}
      </nav>
      {notice && (
        <div
          className={"toast " + (notice.error ? "error" : "")}
          role={notice.error ? "alert" : "status"}
        >
          {notice.message}
          <button aria-label="Dismiss" onClick={() => setNotice(null)}>
            <X size={16} />
          </button>
          {notice.error && notice.message.includes("Another device") && (
            <Button
              onClick={async () => {
                if (
                  confirm(
                    "Reload latest records? Unsaved changes on this screen may be lost.",
                  )
                ) {
                  await load();
                  location.reload();
                }
              }}
            >
              Reload latest
            </Button>
          )}
        </div>
      )}
      <footer>
        <span>RNG PERSONAL WORKSPACE</span>
        <Button
          icon={ShieldCheck}
          disabled={busy}
          onClick={async () => {
            try {
              const data = await (
                await fetchApi("/backup", {
                  method: "POST",
                  headers: { "X-CSRF-Token": csrf },
                })
              ).json();
              notify(data.message);
            } catch (e) {
              notify(e.message, true);
            }
          }}
        >
          Back up on server
        </Button>
      </footer>
    </>
  );
}
function Login({ onLogin }) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="login-scene">
      <div className="login-intro">
        <span className="eyebrow">A SPACE THAT’S YOURS.</span>
        <h1>
          Your work.
          <br />
          Your rhythm.
        </h1>
        <p>
          Everything you’re building,
          <br />
          together in one place.
        </p>
      </div>
      <form
        className="login-box"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            const s = await (
              await fetchApi("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
              })
            ).json();
            await onLogin(s.csrf);
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <BrandLogo className="login-logo" />
        <h2>Welcome back.</h2>
        <p>Sign in to your private workspace.</p>
        <Field
          label="Email address"
          value={email}
          onChange={setEmail}
          type="email"
          autoComplete="username"
          required
        />
        <Field
          label="Password"
          value={password}
          onChange={setPassword}
          type="password"
          autoComplete="current-password"
          required
        />
        {error && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        <Button kind="primary" disabled={busy}>
          {busy ? "Signing in…" : "Open my workspace"}
          <ArrowUpRight size={18} />
        </Button>
        <small>
          <ShieldCheck size={14} />
          Your records stay on your server.
        </small>
      </form>
    </div>
  );
}
function Home({ state, save, busy }) {
  const [note, setNote] = useState(""),
    [edit, setEdit] = useState(null),
    [draft, setDraft] = useState(""),
    [del, setDel] = useState(null);
  const notes = state.sticky_notes || [];
  const date = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Tehran",
  }).format(new Date());
  return (
    <>
      <div className="portrait" />
      <div className="home-content">
        <BrandLogo className="dashboard-logo" />
        <div className="home-top">
          <span className="eyebrow">MAKE ROOM FOR WHAT MATTERS</span>
          <div className="date">
            <CalendarDays size={17} />
            <span>
              {date}
              <small lang="fa" dir="rtl">
                {new Intl.DateTimeFormat("fa-IR", {
                  dateStyle: "full",
                  timeZone: "Asia/Tehran",
                }).format(new Date())}
              </small>
            </span>
          </div>
        </div>
        <h1>
          My Dashboard
          <span>
            A clear mind.
            <br />A space to make things happen.
          </span>
        </h1>
        <section className="notes-section">
          <div className="section-heading">
            <h2>Sticky notes</h2>
            <span>{String(notes.length).padStart(2, "0")} NOTES</span>
          </div>
          <div className="notes">
            {notes.map((n, i) => (
              <div className="note" key={i}>
                <span className="note-index">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p>{typeof n === "string" ? n : n.text || JSON.stringify(n)}</p>
                <Button
                  icon={Pencil}
                  aria-label="Edit note"
                  onClick={() => {
                    setEdit(i);
                    setDraft(typeof n === "string" ? n : n.text || "");
                  }}
                />
                <Button
                  icon={Trash2}
                  aria-label="Delete note"
                  onClick={() => setDel(i)}
                />
              </div>
            ))}
          </div>
          <form
            className="note-add"
            onSubmit={async (e) => {
              e.preventDefault();
              if (note.trim()) {
                await save({ sticky_notes: [...notes, note.trim()] })
                  .then(() => setNote(""))
                  .catch(() => {});
              }
            }}
          >
            <input
              aria-label="New sticky note"
              placeholder="Something to remember…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              required
            />
            <Button kind="primary" disabled={busy} icon={Plus}>
              Add note
            </Button>
          </form>
        </section>
        <div className="section-heading">
          <h2>Your spaces</h2>
          <span>ONE WORKSPACE. MANY POSSIBILITIES.</span>
        </div>
        <div className="home-tiles">
          {pages.slice(1).map(([key, title, Icon], i) => (
            <a href={url([key])} className="home-tile" key={key}>
              <Icon size={27} />
              <span>{title}</span>
              <ArrowUpRight className="tile-arrow" size={17} />
              <small>{String(i + 1).padStart(2, "0")}</small>
            </a>
          ))}
        </div>
      </div>
      {edit !== null && (
        <Modal title="Edit note" onClose={() => setEdit(null)}>
          <Field label="Note" area value={draft} onChange={setDraft} />
          <Button
            kind="primary"
            disabled={busy || !draft.trim()}
            onClick={async () => {
              const updated = clone(notes);
              updated[edit] =
                typeof notes[edit] === "string"
                  ? draft
                  : { ...notes[edit], text: draft };
              await save({ sticky_notes: updated })
                .then(() => setEdit(null))
                .catch(() => {});
            }}
          >
            Save note
          </Button>
        </Modal>
      )}
      {del !== null && (
        <Confirm
          title="Sticky note"
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={async () => {
            await save({ sticky_notes: notes.filter((_, i) => i !== del) })
              .then(() => setDel(null))
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}
function Tasks({ state, section, save, busy }) {
  const tasks = state[section] || [];
  const [edit, setEdit] = useState(null),
    [draft, setDraft] = useState(null),
    [del, setDel] = useState(null),
    [query, setQuery] = useState("");
  const order = tasks
    .map((task, index) => ({ task, index }))
    .filter(({ task }) =>
      task.title.toLowerCase().includes(query.toLowerCase()),
    )
    .sort(
      (a, b) =>
        (Date.parse(b.task.created_at || b.task.created || "") || 0) -
          (Date.parse(a.task.created_at || a.task.created || "") || 0) ||
        b.index - a.index,
    );
  const pending = order.filter((x) => !x.task.done),
    completed = order.filter((x) => x.task.done);
  function open(index) {
    setEdit(index);
    setDraft(
      index === -1
        ? {
            title: "",
            notes: "",
            done: false,
            created: today(),
            created_at: now(),
            completed: null,
            subtasks: [],
          }
        : clone(tasks[index]),
    );
  }
  async function toggle(index, sub = null) {
    const next = clone(tasks),
      t = next[index];
    if (sub === null) {
      t.done = !t.done;
      t.subtasks.forEach((s) => (s.done = t.done));
    } else {
      t.subtasks[sub].done = !t.subtasks[sub].done;
      t.done = t.subtasks.length > 0 && t.subtasks.every((s) => s.done);
    }
    t.completed = t.done ? today() : null;
    await save({ [section]: next }).catch(() => {});
  }
  const card = ({ task, index }) => (
    <article
      id={"task-" + index}
      className={"card task-card " + (task.done ? "completed" : "")}
      key={index}
      tabIndex={-1}
    >
      <div className="row between">
        <span className={"pill " + (task.done ? "done" : "")}>
          {task.done ? "Completed" : "In progress"}
        </span>
        <button
          className={"check-main " + (task.done ? "checked" : "")}
          aria-label={"Complete " + task.title}
          aria-pressed={!!task.done}
          disabled={busy}
          onClick={() => toggle(index)}
        >
          <Check size={18} />
        </button>
      </div>
      <h3>{task.title}</h3>
      <div className="subtasks">
        {task.subtasks?.map((s, i) => (
          <label key={i}>
            <input
              type="checkbox"
              checked={!!s.done}
              disabled={busy}
              onChange={() => toggle(index, i)}
            />
            <span>{s.text}</span>
          </label>
        ))}
      </div>
      {task.notes && <p className="task-notes">{task.notes}</p>}
      <div className="card-meta">
        Created {task.created}
        {task.completed && <span>Completed {task.completed}</span>}
      </div>
      <div className="actions">
        <Button icon={Pencil} onClick={() => open(index)}>
          Edit
        </Button>
        <Button icon={Trash2} onClick={() => setDel(index)}>
          Delete
        </Button>
      </div>
    </article>
  );
  return (
    <>
      <div className="toolbar">
        <div className="search">
          <Search size={18} />
          <input
            aria-label="Search tasks"
            placeholder="Find a task…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <Button kind="primary" icon={Plus} onClick={() => open(-1)}>
          New task
        </Button>
      </div>
      {pending.length > 0 && (
        <section className="jump-list">
          <span className="eyebrow">IN PROGRESS · JUMP TO A TASK</span>
          <div>
            {pending.map(({ task, index }) => (
              <button
                key={index}
                onClick={() => {
                  const target = document.getElementById("task-" + index);
                  target?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
                  target?.focus({ preventScroll: true });
                }}
              >
                {task.title}
                <ArrowUpRight size={14} />
              </button>
            ))}
          </div>
        </section>
      )}
      <div className="section-heading">
        <h2>In progress</h2>
        <span>{pending.length} TASKS</span>
      </div>
      <div className="card-grid">{pending.map(card)}</div>
      {!pending.length && (
        <Empty
          title="A clear runway."
          text="Add a task when you’re ready for your next step."
        />
      )}
      {completed.length > 0 && (
        <>
          <div className="section-heading">
            <h2>Completed</h2>
            <span>{completed.length} TASKS</span>
          </div>
          <div className="card-grid">{completed.map(card)}</div>
        </>
      )}
      {draft && (
        <Modal
          title={edit === -1 ? "New task" : "Edit task"}
          onClose={() => setDraft(null)}
        >
          <DraftGuard />
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const next = clone(tasks);
              if (edit === -1) next.push(draft);
              else next[edit] = draft;
              await save({ [section]: next })
                .then(() => setDraft(null))
                .catch(() => {});
            }}
          >
            <Field
              label="Task title"
              value={draft.title}
              onChange={(title) => setDraft({ ...draft, title })}
              required
            />
            <h3>Subtasks</h3>
            {draft.subtasks.map((s, i) => (
              <div className="row sub-edit" key={i}>
                <input
                  aria-label={"Subtask " + (i + 1)}
                  value={s.text}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      subtasks: draft.subtasks.map((v, j) =>
                        j === i ? { ...v, text: e.target.value } : v,
                      ),
                    })
                  }
                />
                <Button
                  type="button"
                  icon={X}
                  aria-label="Remove subtask"
                  onClick={() => {
                    const subs = draft.subtasks.filter((_, j) => i !== j);
                    setDraft({
                      ...draft,
                      subtasks: subs,
                      done: subs.length ? subs.every((s) => s.done) : false,
                      completed: null,
                    });
                  }}
                />
              </div>
            ))}
            <Button
              type="button"
              icon={Plus}
              onClick={() =>
                setDraft({
                  ...draft,
                  subtasks: [...draft.subtasks, { text: "", done: false }],
                  done: false,
                  completed: null,
                })
              }
            >
              Add subtask
            </Button>
            <Field
              label="Notes"
              area
              value={draft.notes || ""}
              onChange={(notes) => setDraft({ ...draft, notes })}
            />
            <div className="actions">
              <Button type="button" onClick={() => setDraft(null)}>
                Cancel
              </Button>
              <Button
                kind="primary"
                disabled={busy || !draft.title.trim()}
                icon={Save}
              >
                Save task
              </Button>
            </div>
          </form>
        </Modal>
      )}
      {del !== null && (
        <Confirm
          title={tasks[del].title}
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={async () => {
            await save({ [section]: tasks.filter((_, i) => i !== del) })
              .then(() => setDel(null))
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}
const missionFields = {
  report_date: "تاریخ گزارش",
  employee: "نام و نام خانوادگی",
  position: "پست سازمانی",
  dispatcher: "اعزام کننده",
  city: "شهر ماموریت",
  company: "نام شرکت / کارخانه",
  companions: "همراهان",
  duration: "مدت ماموریت",
  start_date: "تاریخ شروع",
  departure_time: "ساعت رفت",
  end_date: "تاریخ پایان",
  return_time: "ساعت برگشت",
  transport: "استفاده از وسایل نقلیه",
  distance: "مسافت طی شده (کیلومتر)",
  equipment: "تجهیزات مورد استفاده",
  description: "شرح ماموریت",
  objective: "هدف ماموریت",
  result: "نتیجه ماموریت",
  manager_comment: "نظر مدیر / رئیس مربوطه",
  manager_signature: "امضای مدیر",
  employee_signature: "امضای مامور",
};
const bomItem = () => ({
  description: "",
  size: "",
  actual: "",
  over: "",
  unit: "",
  notes: "",
});
const emptyForm = (kind) =>
  kind === "meetings"
    ? Array.from({ length: 11 }, () => [
        "",
        "",
        "",
        "Raised",
        "",
        "not Started",
      ])
    : kind === "warehouse"
      ? {
          date: "",
          number: "",
          items: Array.from({ length: 10 }, () => ["", "", "", "", ""]),
          requester: "",
          approver: "",
          requester_signature: "",
          approver_signature: "",
        }
      : kind === "mission"
        ? Object.fromEntries(Object.keys(missionFields).map((f) => [f, ""]))
        : {
            date: "",
            number: "",
            code: "",
            preparer: "",
            approver: "",
            items: Array.from({ length: 15 }, bomItem),
            extra_tables: [],
          };
const recordPrefix = {
  meetings: "meeting",
  warehouse: "warehouse",
  mission: "mission_report",
  bom: "bom",
};
function Records({ kind, recordId, state, save, busy, notify }) {
  const prefix = recordPrefix[kind],
    cards = state[prefix + "_cards"] || [],
    ids = cards.map(
      (_, i) =>
        (state[prefix + "_card_ids"] || [])[i] || `legacy-${prefix}-${i}`,
    ),
    forms = state[prefix + "_forms"] || {};
  const [create, setCreate] = useState(false),
    [title, setTitle] = useState(""),
    [rename, setRename] = useState(null),
    [del, setDel] = useState(null),
    [query, setQuery] = useState("");
  const isMeeting = kind === "meetings";
  const index = isMeeting ? Number(recordId) : ids.indexOf(recordId);
  const selected = recordId !== undefined && index >= 0 && index < cards.length;
  const target = isMeeting ? "meeting_data_" + cards[index] : recordId;
  const form = isMeeting ? state[target] : forms[target];
  async function add() {
    if (!title.trim()) return;
    const changes = { [prefix + "_cards"]: [...cards, title.trim()] };
    let id;
    if (isMeeting) {
      if (cards.includes(title.trim()))
        return notify("Choose a unique meeting name.", true);
      changes["meeting_data_" + title.trim()] = emptyForm(kind);
      id = String(cards.length);
    } else {
      id = uid();
      changes[prefix + "_card_ids"] = [...ids, id];
      changes[prefix + "_forms"] = { ...forms, [id]: emptyForm(kind) };
    }
    await save(changes)
      .then(() => {
        setCreate(false);
        go(kind, id);
      })
      .catch(() => {});
  }
  if (selected)
    return (
      <RecordEditor
        key={recordId}
        kind={kind}
        title={cards[index]}
        recordId={recordId}
        initial={form || emptyForm(kind)}
        busy={busy}
        notify={notify}
        onSave={async (draft) => {
          await save(
            isMeeting
              ? { [target]: draft }
              : {
                  [prefix + "_forms"]: { ...forms, [recordId]: draft },
                  [prefix + "_card_ids"]: ids,
                },
          );
        }}
      />
    );
  return (
    <>
      <div className="toolbar">
        <div className="search">
          <Search size={18} />
          <input
            aria-label="Search records"
            placeholder="Find a record…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <Button
          kind="primary"
          icon={Plus}
          onClick={() => {
            setTitle("");
            setCreate(true);
          }}
        >
          New{" "}
          {kind === "meetings" ? "meeting" : kind === "bom" ? "BOM" : "report"}
        </Button>
      </div>
      <div className="card-grid">
        {cards
          .map((name, i) => ({ name, i }))
          .reverse()
          .filter((x) =>
            String(x.name).toLowerCase().includes(query.toLowerCase()),
          )
          .map(({ name, i }) => {
            const Icon = pages.find((p) => p[0] === kind)[2];
            return (
              <article className="card record-card" key={i}>
                <div className="row between">
                  <span className="card-icon">
                    <Icon size={25} />
                  </span>
                  <span className="record-number">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3>{name}</h3>
                <p>
                  {isMeeting
                    ? "Discussion, decisions & next steps"
                    : kind === "warehouse"
                      ? "Items, quantities & approvals"
                      : kind === "mission"
                        ? "Mission details & outcomes"
                        : "Materials, quantities & specifications"}
                </p>
                <a
                  className="button primary"
                  href={url([kind, isMeeting ? String(i) : ids[i]])}
                >
                  Open record
                  <ArrowUpRight size={17} />
                </a>
                <div className="actions">
                  <Button
                    icon={Pencil}
                    onClick={() => {
                      setTitle(name);
                      setRename(i);
                    }}
                  >
                    Rename
                  </Button>
                  <Button icon={Trash2} onClick={() => setDel(i)}>
                    Delete
                  </Button>
                </div>
              </article>
            );
          })}
      </div>
      {!cards.length && <Empty />}
      {(create || rename !== null) && (
        <Modal
          title={create ? "Create record" : "Rename record"}
          onClose={() => {
            setCreate(false);
            setRename(null);
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (create) return add();
              if (
                isMeeting &&
                cards.some((n, i) => n === title.trim() && i !== rename)
              )
                return notify("Choose a unique meeting name.", true);
              const next = [...cards];
              next[rename] = title.trim();
              const changes = { [prefix + "_cards"]: next };
              if (isMeeting)
                changes["meeting_data_" + title.trim()] =
                  state["meeting_data_" + cards[rename]] || emptyForm(kind);
              await save(changes)
                .then(() => setRename(null))
                .catch(() => {});
            }}
          >
            <Field label="Name" value={title} onChange={setTitle} required />
            <Button kind="primary" disabled={busy || !title.trim()}>
              Save
            </Button>
          </form>
        </Modal>
      )}
      {del !== null && (
        <Confirm
          title={cards[del]}
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={async () => {
            const changes = {
              [prefix + "_cards"]: cards.filter((_, i) => i !== del),
            };
            if (!isMeeting) {
              changes[prefix + "_card_ids"] = ids.filter((_, i) => i !== del);
              const next = { ...forms };
              delete next[ids[del]];
              changes[prefix + "_forms"] = next;
            }
            await save(changes)
              .then(() => setDel(null))
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}
function RecordEditor({
  kind,
  title,
  recordId,
  initial,
  onSave,
  busy,
  notify,
}) {
  const [draft, setDraft] = useState(() => clone(initial)),
    [dirty, setDirty] = useState(false);
  function set(next) {
    setDraft(next);
    setDirty(true);
  }
  const change = (key, value) => set({ ...draft, [key]: value });
  const arraySet = (row, col, value) =>
    set(
      draft.map((r, i) =>
        i === row ? r.map((v, j) => (j === col ? value : v)) : r,
      ),
    );
  async function submit(e) {
    e.preventDefault();
    await onSave(draft)
      .then(() => setDirty(false))
      .catch(() => {});
  }
  const pdfKind = kind === "meetings" ? "meeting" : kind;
  return (
    <>
      <DraftGuard dirty={dirty} />
      <a className="back-link" href={url([kind])}>
        <ArrowLeft size={17} />
        Back to records
      </a>
      <div className="detail-heading">
        <span className="eyebrow">THE DETAILS THAT MATTER</span>
        <h2>{title}</h2>
      </div>
      <form onSubmit={submit} className="record-editor">
        {kind === "meetings" ? (
          <>
            {Array.from({ length: 11 }, (_, i) => {
              const r = draft[i] || ["", "", "", "", "", ""];
              return (
                <section className="panel" key={i}>
                  <div className="section-heading">
                    <h3>Agenda item {String(i + 1).padStart(2, "0")}</h3>
                    <span>{r[5] || "NOT STARTED"}</span>
                  </div>
                  <div className="fields">
                    <Field
                      label="Agenda"
                      value={r[0]}
                      onChange={(v) => arraySet(i, 0, v)}
                    />
                    <Field
                      label="Title"
                      value={r[1]}
                      onChange={(v) => arraySet(i, 1, v)}
                    />
                    <Field
                      label="Person in charge"
                      value={r[2]}
                      onChange={(v) => arraySet(i, 2, v)}
                    />
                    <Select
                      label="Discussion status"
                      value={r[3]}
                      onChange={(v) => arraySet(i, 3, v)}
                      options={["", "Raised", "not Raised"]}
                    />
                    <Select
                      label="Action status"
                      value={r[5]}
                      onChange={(v) => arraySet(i, 5, v)}
                      options={[
                        "",
                        "Done",
                        "not Started",
                        "In Progress",
                        "Stopped",
                      ]}
                    />
                    <Field
                      label="Description / action"
                      area
                      value={r[4]}
                      onChange={(v) => arraySet(i, 4, v)}
                    />
                  </div>
                </section>
              );
            })}
          </>
        ) : kind === "mission" ? (
          <section className="panel persian" dir="rtl">
            <div className="fields">
              {Object.entries(missionFields).map(([key, label]) => (
                <Field
                  key={key}
                  label={label}
                  value={draft[key]}
                  area={[
                    "description",
                    "objective",
                    "result",
                    "manager_comment",
                  ].includes(key)}
                  onChange={(v) => change(key, v)}
                />
              ))}
            </div>
          </section>
        ) : kind === "warehouse" ? (
          <>
            <section className="panel">
              <div className="fields">
                {[
                  ["date", "Date"],
                  ["number", "Request number"],
                  ["requester", "Requester"],
                  ["approver", "Approver"],
                  ["requester_signature", "Requester signature"],
                  ["approver_signature", "Approver signature"],
                ].map(([k, label]) => (
                  <Field
                    key={k}
                    label={label}
                    value={draft[k]}
                    onChange={(v) => change(k, v)}
                  />
                ))}
              </div>
            </section>
            <h3>Requested items</h3>
            {(draft.items || []).map((r, i) => (
              <section className="panel" key={i}>
                <span className="eyebrow">
                  ITEM {String(i + 1).padStart(2, "0")}
                </span>
                <div className="fields">
                  {[
                    "Item code",
                    "Description",
                    "Requested quantity",
                    "Intended use",
                    "Notes",
                  ].map((label, j) => (
                    <Field
                      key={j}
                      label={label}
                      value={r[j]}
                      onChange={(v) =>
                        change(
                          "items",
                          draft.items.map((row, index) =>
                            index === i
                              ? row.map((x, col) => (col === j ? v : x))
                              : row,
                          ),
                        )
                      }
                    />
                  ))}
                </div>
              </section>
            ))}
          </>
        ) : (
          <>
            <section className="panel">
              <div className="fields">
                {[
                  ["date", "Date"],
                  ["number", "Number"],
                  ["code", "Project / drawing code"],
                  ["preparer", "Prepared by"],
                  ["approver", "Approved by"],
                ].map(([k, label]) => (
                  <Field
                    key={k}
                    label={label}
                    value={draft[k]}
                    onChange={(v) => change(k, v)}
                  />
                ))}
              </div>
            </section>
            {[draft.items || [], ...(draft.extra_tables || [])].map(
              (table, t) => (
                <section className="panel" key={t}>
                  <div className="section-heading">
                    <h3>Material schedule {t + 1}</h3>
                  </div>
                  <div className="table-scroll">
                    <table className="bom-table persian" dir="rtl">
                      <thead>
                        <tr>
                          {[
                            "ردیف",
                            "شرح",
                            "سایز",
                            "مقدار واقعی",
                            "اضافه",
                            "جمع",
                            "واحد",
                            "توضیحات",
                          ].map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {table.map((item, i) => (
                          <tr key={i}>
                            <td>{i + 1}</td>
                            {[
                              "description",
                              "size",
                              "actual",
                              "over",
                              "total",
                              "unit",
                              "notes",
                            ].map((k) => (
                              <td key={k}>
                                {k === "total" ? (
                                  bomTotal(item)
                                ) : (
                                  <input
                                    aria-label={`${k} ${i + 1} table ${t + 1}`}
                                    value={item[k] || ""}
                                    onChange={(e) => {
                                      const next = clone(draft);
                                      const rows =
                                        t === 0
                                          ? next.items
                                          : next.extra_tables[t - 1];
                                      rows[i][k] = e.target.value;
                                      set(next);
                                    }}
                                  />
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ),
            )}
            <Button
              type="button"
              icon={Plus}
              onClick={() =>
                change("extra_tables", [
                  ...(draft.extra_tables || []),
                  Array.from({ length: 15 }, bomItem),
                ])
              }
            >
              Add material table
            </Button>
          </>
        )}
        <div className="save-bar">
          <span>{dirty ? "Unsaved changes" : "All changes saved"}</span>
          <Button icon={Save} kind="primary" disabled={busy}>
            Save {kind === "meetings" ? "meeting" : "report"}
          </Button>
        </div>
      </form>
      <section className="panel exports">
        <h3>Ready to send</h3>
        <p>
          {dirty
            ? "Save your changes before exporting."
            : "Download or share your report using its original layout."}
        </p>
        {!dirty && <PdfActions kind={pdfKind} id={recordId} notify={notify} />}
      </section>
    </>
  );
}
function solarValue(value) {
  const raw = ascii(value || "").replaceAll("-", "/");
  const match = raw.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
  if (match && Number(match[1]) >= 1700) {
    const date = new Date(
      Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])),
    );
    return new Intl.DateTimeFormat("en-US-u-ca-persian", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
      .format(date)
      .replace(/(\d+)\/(\d+)\/(\d+)/, "$3/$1/$2");
  }
  return raw;
}
function normalizeCategory(row) {
  if (row.type === "Income") return "دریافتی";
  if (categories.includes(row.category)) return row.category;
  return (
    {
      material: "متریال",
      materials: "متریال",
      wage: "اجرت",
      wages: "اجرت",
      labor: "اجرت",
      labour: "اجرت",
      service: "خدمات",
      services: "خدمات",
    }[String(row.category || "").toLowerCase()] || "سایر"
  );
}
function bomTotal(item) {
  const a = integer(item.actual || "0"),
    b = integer(item.over || "0");
  const n = Number(a) + Number(b);
  return Number.isFinite(n) ? String(n) : "Invalid";
}
function Projects({ route, state, save, busy, notify }) {
  const projects = state.financial_projects || {},
    id = route[1],
    section = route[2],
    project = projects[id];
  const [create, setCreate] = useState(false),
    [name, setName] = useState(""),
    [rename, setRename] = useState(null),
    [del, setDel] = useState(null);
  async function saveProject(value) {
    await save({ financial_projects: { ...projects, [id]: value } });
  }
  if (project && section === "financial")
    return (
      <Financial
        project={project}
        id={id}
        saveProject={saveProject}
        busy={busy}
        notify={notify}
      />
    );
  if (project && ["meetings", "plans", "documents"].includes(section))
    return (
      <Files
        project={project}
        id={id}
        section={section}
        fileId={route[3]}
        saveProject={saveProject}
        busy={busy}
        notify={notify}
      />
    );
  if (project)
    return (
      <>
        <a className="back-link" href="#/projects">
          <ArrowLeft size={17} />
          All projects
        </a>
        <div className="detail-heading">
          <span className="eyebrow">PROJECT WORKSPACE</span>
          <h2>{project.title}</h2>
          <p>Everything this project needs, together.</p>
        </div>
        <div className="project-spaces">
          {[
            [
              "financial",
              "Financial",
              Wallet,
              "Budgets, transactions & reports",
            ],
            [
              "meetings",
              "Meeting Minutes",
              NotebookPen,
              "Discussions, decisions & records",
            ],
            ["plans", "Plans", Layers, "Drawings, revisions & plans"],
            [
              "documents",
              "Documents",
              FolderOpen,
              "Your project’s essential files",
            ],
          ].map(([key, title, Icon, text]) => (
            <a
              className="card project-space"
              key={key}
              href={url(["projects", id, key])}
            >
              <span className="card-icon">
                <Icon size={27} />
              </span>
              <h3>{title}</h3>
              <p>{text}</p>
              <span className="row">
                Open section <ArrowUpRight size={17} />
              </span>
            </a>
          ))}
        </div>
      </>
    );
  return (
    <>
      <div className="toolbar">
        <p>A home for every project.</p>
        <Button
          kind="primary"
          icon={Plus}
          onClick={() => {
            setName("");
            setCreate(true);
          }}
        >
          New project
        </Button>
      </div>
      <div className="card-grid">
        {Object.entries(projects)
          .reverse()
          .map(([key, p]) => (
            <article className="card record-card" key={key}>
              <span className="card-icon">
                <Building2 size={26} />
              </span>
              <h3>{p.title}</h3>
              <p>Financial · Meetings · Plans · Documents</p>
              <a className="button primary" href={url(["projects", key])}>
                Open project
                <ArrowUpRight size={17} />
              </a>
              <div className="actions">
                <Button
                  icon={Pencil}
                  onClick={() => {
                    setName(p.title);
                    setRename(key);
                  }}
                >
                  Rename
                </Button>
                <Button icon={Trash2} onClick={() => setDel(key)}>
                  Delete
                </Button>
              </div>
            </article>
          ))}
      </div>
      {!Object.keys(projects).length && (
        <Empty
          title="Build something remarkable."
          text="Create a project to bring its finances and files together."
        />
      )}
      {(create || rename) && (
        <Modal
          title={create ? "New project" : "Rename project"}
          onClose={() => {
            setCreate(false);
            setRename(null);
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const key = rename || uid();
              await save({
                financial_projects: {
                  ...projects,
                  [key]: rename
                    ? { ...projects[key], title: name.trim() }
                    : {
                        id: key,
                        title: name.trim(),
                        budget: "0",
                        currency: "IRR",
                        notes: "",
                        transactions: [],
                        created_at: now(),
                      },
                },
              })
                .then(() => {
                  setCreate(false);
                  setRename(null);
                })
                .catch(() => {});
            }}
          >
            <Field
              label="Project name"
              value={name}
              onChange={setName}
              required
            />
            <Button kind="primary" disabled={busy || !name.trim()}>
              Save project
            </Button>
          </form>
        </Modal>
      )}
      {del && (
        <Confirm
          title={projects[del].title}
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={async () => {
            const next = { ...projects };
            delete next[del];
            await save({ financial_projects: next })
              .then(() => setDel(null))
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}
const blankTransaction = () => ({
  id: uid(),
  date: solar(),
  type: "Expense",
  category: "سایر",
  amount: "",
  description: "",
  payer: "",
  counterparty: "",
  attachments: [],
});
function Financial({ project, id, saveProject, busy, notify }) {
  const [draft, setDraft] = useState(() => ({
      ...clone(project),
      budget: project.budget || "0",
      notes: project.notes || "",
      transactions: (project.transactions || []).map((r) => ({
        ...clone(r),
        date: solarValue(r.date),
        category: normalizeCategory(r),
        attachments: r.attachments || [],
      })),
    })),
    [dirty, setDirty] = useState(false),
    [attach, setAttach] = useState(null),
    [del, setDel] = useState(null);
  function set(value) {
    setDraft(value);
    setDirty(true);
  }
  function rowSet(index, key, value) {
    set({
      ...draft,
      transactions: draft.transactions.map((r, i) =>
        i === index ? { ...r, [key]: value } : r,
      ),
    });
  }
  const rows = draft.transactions || [];
  let income = 0n,
    expenses = 0n;
  const cat = Object.fromEntries(categories.slice(0, 4).map((c) => [c, 0n]));
  for (const r of rows) {
    try {
      const n = BigInt(integer(r.amount || "0"));
      if (r.type === "Income") income += n;
      else {
        expenses += n;
        cat[categories.includes(r.category) ? r.category : "سایر"] += n;
      }
    } catch {}
  }
  let budget = 0n;
  try {
    budget = BigInt(integer(draft.budget || "0"));
  } catch {}
  const stats = [
    ["Budget", budget],
    ["Income", income],
    ["Expenses", expenses],
    ["Cash balance", income - expenses],
    ["Budget remaining", budget - expenses],
    ...["Material", "Wage", "Service", "Other"].map((v, i) => [
      v,
      cat[categories[i]],
    ]),
  ];
  return (
    <>
      <DraftGuard dirty={dirty} />
      <a className="back-link" href={url(["projects", id])}>
        <ArrowLeft size={17} />
        {project.title}
      </a>
      <div className="detail-heading">
        <span className="eyebrow">PROJECT FINANCIAL</span>
        <h2>{project.title}</h2>
        <p>A clear view of every rial.</p>
      </div>
      <div className="financial-stats">
        {stats.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value.toLocaleString("en-US")}</strong>
            <small>IRR RIAL</small>
          </div>
        ))}
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            if (!/^\d+$/.test(integer(draft.budget)))
              throw new Error("Enter a whole, non-negative project budget.");
            for (const [i, r] of rows.entries()) {
              if (
                !/^\d+$/.test(integer(r.amount)) ||
                BigInt(integer(r.amount)) <= 0n
              )
                throw new Error(`Row ${i + 1}: enter a positive whole amount.`);
            }
            const clean = {
              ...draft,
              budget: integer(draft.budget),
              transactions: rows.map((r) => ({
                ...r,
                amount: integer(r.amount),
              })),
            };
            await saveProject(clean);
            setDraft(clean);
            setDirty(false);
          } catch (e) {
            notify(e.message, true);
          }
        }}
      >
        <section className="panel">
          <div className="fields">
            <Field
              label="Project budget · IRR Rial"
              value={draft.budget}
              inputMode="numeric"
              onChange={(v) => set({ ...draft, budget: v })}
            />
            <Field
              label="Financial notes"
              area
              value={draft.notes}
              onChange={(v) => set({ ...draft, notes: v })}
            />
          </div>
        </section>
        <div className="section-heading">
          <h3>Transaction ledger</h3>
          <span>DATES IN SOLAR HIJRI · AMOUNTS IN IRR</span>
        </div>
        <div className="table-scroll ledger-wrap">
          <table className="ledger persian" dir="rtl">
            <colgroup>
              {[4, 9, 8, 10, 18, 11, 11, 12, 4, 4].map((n, i) => (
                <col key={i} style={{ width: n + "%" }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {[
                  "ردیف",
                  "تاریخ",
                  "نوع",
                  "دسته بندی",
                  "شرح",
                  "پرداخت کننده",
                  "طرف حساب",
                  "مبلغ",
                  "پیوست",
                  "حذف",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.id || i}>
                  <td data-label="ردیف">{i + 1}</td>
                  <td data-label="تاریخ">
                    <input
                      aria-label={"تاریخ " + (i + 1)}
                      dir="ltr"
                      value={r.date}
                      onChange={(e) => rowSet(i, "date", ascii(e.target.value))}
                    />
                  </td>
                  <td data-label="نوع">
                    <select
                      aria-label={"نوع " + (i + 1)}
                      value={r.type}
                      onChange={(e) => {
                        const type = e.target.value;
                        const next = clone(draft);
                        next.transactions[i] = {
                          ...r,
                          type,
                          category: type === "Income" ? "دریافتی" : "سایر",
                        };
                        set(next);
                      }}
                    >
                      <option value="Expense">هزینه</option>
                      <option value="Income">دریافتی</option>
                    </select>
                  </td>
                  <td data-label="دسته بندی">
                    <select
                      aria-label={"دسته بندی " + (i + 1)}
                      value={
                        categories.includes(r.category) ? r.category : "سایر"
                      }
                      onChange={(e) => rowSet(i, "category", e.target.value)}
                    >
                      {categories
                        .filter((c) =>
                          r.type === "Income"
                            ? c === "دریافتی"
                            : c !== "دریافتی",
                        )
                        .map((c) => (
                          <option key={c}>{c}</option>
                        ))}
                    </select>
                  </td>
                  {["description", "payer", "counterparty"].map((k, j) => (
                    <td
                      key={k}
                      data-label={["شرح", "پرداخت کننده", "طرف حساب"][j]}
                    >
                      <textarea
                        aria-label={
                          ["شرح", "پرداخت کننده", "طرف حساب"][j] + " " + (i + 1)
                        }
                        value={r[k] || ""}
                        onChange={(e) => rowSet(i, k, e.target.value)}
                      />
                    </td>
                  ))}
                  <td data-label="مبلغ">
                    <input
                      aria-label={"مبلغ " + (i + 1)}
                      inputMode="numeric"
                      dir="ltr"
                      value={r.amount}
                      onChange={(e) => rowSet(i, "amount", e.target.value)}
                    />
                  </td>
                  <td data-label="پیوست">
                    <Button
                      type="button"
                      icon={Plus}
                      aria-label={"پیوست " + (i + 1)}
                      onClick={() => setAttach(i)}
                    />
                    <small>{r.attachments?.length || 0}</small>
                  </td>
                  <td data-label="حذف">
                    <Button
                      type="button"
                      icon={Trash2}
                      aria-label={"حذف " + (i + 1)}
                      onClick={() => setDel(i)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <Empty
              title="Your ledger starts here."
              text="Add a transaction to track an expense or income."
            />
          )}
        </div>
        <Button
          type="button"
          icon={Plus}
          onClick={() =>
            set({ ...draft, transactions: [...rows, blankTransaction()] })
          }
        >
          Add transaction
        </Button>
        <div className="save-bar">
          <span>{dirty ? "Unsaved changes" : "All changes saved"}</span>
          <Button kind="primary" icon={Save} disabled={busy}>
            Save financial
          </Button>
        </div>
      </form>
      <section className="panel exports">
        <h3>Project financial report</h3>
        <p>Persian · A4 landscape · RNG branding</p>
        {dirty ? (
          <p>Save your changes before exporting.</p>
        ) : (
          <PdfActions kind="financial" id={id} notify={notify} />
        )}
      </section>
      {attach !== null && (
        <Modal
          title={"Row " + (attach + 1) + " attachments"}
          onClose={() => setAttach(null)}
        >
          <p>
            Images or PDFs, up to 2 MB each. Save financial changes to keep your
            attachments.
          </p>
          <input
            type="file"
            aria-label="Attach file"
            accept="image/*,application/pdf"
            onChange={async (e) => {
              try {
                const file = e.target.files[0];
                if (!file) return;
                if (file.size > 2 * 1024 * 1024)
                  throw new Error("Maximum attachment size is 2 MB.");
                const total = rows.reduce(
                  (n, r) =>
                    n +
                    (r.attachments || []).reduce(
                      (s, a) => s + (a.size || 0),
                      0,
                    ),
                  0,
                );
                if (total + file.size > 20 * 1024 * 1024)
                  throw new Error("The project attachment limit is 20 MB.");
                const record = {
                  ...(await readFile(file, file.name)),
                  name: file.name,
                };
                rowSet(attach, "attachments", [
                  ...(rows[attach].attachments || []),
                  record,
                ]);
              } catch (e) {
                notify(e.message, true);
              }
              e.target.value = "";
            }}
          />
          {(rows[attach].attachments || []).map((f, i) => (
            <div className="attachment" key={f.id || i}>
              <span>{f.filename || f.name}</span>
              <Button
                icon={Download}
                onClick={() => fileAction(f, false, notify)}
              >
                Download
              </Button>
              <Button
                icon={Trash2}
                aria-label="Remove attachment"
                onClick={() => {
                  if (confirm("Remove this attachment?"))
                    rowSet(
                      attach,
                      "attachments",
                      rows[attach].attachments.filter((_, j) => j !== i),
                    );
                }}
              />
            </div>
          ))}
        </Modal>
      )}
      {del !== null && (
        <Confirm
          title={"Transaction " + (del + 1)}
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={() => {
            set({ ...draft, transactions: rows.filter((_, i) => i !== del) });
            setDel(null);
          }}
        />
      )}
    </>
  );
}
async function readFile(file, title, note = "") {
  const data = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = () => reject(new Error("Could not read this file."));
    reader.readAsDataURL(file);
  });
  return {
    id: uid(),
    title,
    filename: file.name,
    mime: file.type || "application/octet-stream",
    size: file.size,
    data,
    note,
    url: "",
    uploaded_at: now(),
  };
}
async function fileBlob(f) {
  if (f._blob_ref) {
    const blob = await (await fetchApi(`/file/${f._blob_ref}`)).blob();
    return new Blob([blob], { type: f.mime || "application/octet-stream" });
  }
  const raw = atob(f.data || "");
  return new Blob([Uint8Array.from(raw, (c) => c.charCodeAt(0))], {
    type: f.mime || "application/octet-stream",
  });
}
async function fileAction(f, share, notify) {
  try {
    await downloadOrShare(
      await fileBlob(f),
      f.filename || f.name || "document",
      share,
    );
  } catch (e) {
    notify(e.message, true);
  }
}
function Preview({ record }) {
  const [src, setSrc] = useState(""),
    [text, setText] = useState(""),
    [error, setError] = useState("");
  const name = record.filename || record.name || "";
  const image = /\.(png|jpe?g|gif|webp|bmp)$/i.test(name),
    pdf = /\.pdf$/i.test(name),
    plain = /\.(txt|csv|md|json|log|xml|ya?ml)$/i.test(name);
  useEffect(() => {
    let src = "",
      cancelled = false;
    if (record.url || !(image || pdf || plain)) return;
    (async () => {
      try {
        const original = await fileBlob(record);
        const blob = pdf
          ? new Blob([original], { type: "application/pdf" })
          : original;
        if (cancelled) return;
        src = URL.createObjectURL(blob);
        setSrc(src);
        if (plain) {
          const text = await blob.text();
          if (!cancelled) setText(text.slice(0, 200000));
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    })();
    return () => {
      cancelled = true;
      if (src) URL.revokeObjectURL(src);
    };
  }, [record]);
  if (error)
    return (
      <p className="warning" role="alert">
        {error}
      </p>
    );
  if (record.url) {
    try {
      const u = new URL(record.url);
      return ["http:", "https:"].includes(u.protocol) ? (
        <a
          className="button"
          href={u.href}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open document link
        </a>
      ) : (
        <p>Invalid document link.</p>
      );
    } catch {
      return <p>Invalid document link.</p>;
    }
  }
  return image ? (
    <img className="file-preview" alt={record.title} src={src} />
  ) : pdf ? (
    <iframe className="pdf-preview" title={record.title} src={src} />
  ) : plain ? (
    <pre className="text-preview">{text}</pre>
  ) : (
    <Empty
      title="Your original file is ready."
      text="Download this file to open it in its usual application."
    />
  );
}
function Files({ project, id, section, fileId, saveProject, busy, notify }) {
  const field = {
      meetings: "meeting_files",
      plans: "plan_files",
      documents: "documents",
    }[section],
    records = project[field] || [],
    selected = records.find((f) => f.id === fileId);
  const [upload, setUpload] = useState(false),
    [title, setTitle] = useState(""),
    [note, setNote] = useState(""),
    [file, setFile] = useState(null),
    [rename, setRename] = useState(null),
    [del, setDel] = useState(null);
  const heading = {
    meetings: "Meeting Minutes",
    plans: "Plans",
    documents: "Documents",
  }[section];
  const actionBar = (f) => (
    <div className="actions">
      <Button icon={Download} onClick={() => fileAction(f, false, notify)}>
        Download
      </Button>
      <Button icon={Share2} onClick={() => fileAction(f, true, notify)}>
        Share
      </Button>
    </div>
  );
  if (selected)
    return (
      <>
        <a className="back-link" href={url(["projects", id, section])}>
          <ArrowLeft size={17} />
          Back to {heading}
        </a>
        <div className="detail-heading">
          <span className="eyebrow">{project.title}</span>
          <h2>{selected.title}</h2>
          <p>{selected.filename}</p>
        </div>
        <section className="panel">
          {selected.note && <p>{selected.note}</p>}
          {!selected.url && actionBar(selected)}
          <Preview record={selected} />
        </section>
      </>
    );
  return (
    <>
      <a className="back-link" href={url(["projects", id])}>
        <ArrowLeft size={17} />
        {project.title}
      </a>
      <div className="detail-heading">
        <span className="eyebrow">PROJECT LIBRARY</span>
        <h2>{heading}</h2>
        <p>Your files, clearly named and always together.</p>
      </div>
      <div className="toolbar">
        <span>{records.length} files</span>
        <Button
          kind="primary"
          icon={Upload}
          onClick={() => {
            setTitle("");
            setNote("");
            setFile(null);
            setUpload(true);
          }}
        >
          Upload file
        </Button>
      </div>
      <div className="card-grid">
        {records
          .map((r, i) => ({ r, i }))
          .reverse()
          .map(({ r, i }) => (
            <article className="card file-card" key={r.id || i}>
              <span className="card-icon">
                <FileText size={25} />
              </span>
              <span className="pill">
                {r.filename?.split(".").pop()?.toUpperCase() || "LINK"}
              </span>
              <h3>{r.title}</h3>
              <p>{r.filename}</p>
              {r.note && <p className="task-notes">{r.note}</p>}
              <small>
                {r.size ? `${Math.ceil(r.size / 1024)} KB · ` : ""}
                {r.uploaded_at?.slice(0, 10)}
              </small>
              <a
                className="button primary"
                href={url(["projects", id, section, r.id])}
              >
                View file
                <ArrowUpRight size={17} />
              </a>
              {!r.url && actionBar(r)}
              <div className="actions">
                <Button
                  icon={Pencil}
                  onClick={() => {
                    setTitle(r.title);
                    setRename(i);
                  }}
                >
                  Rename
                </Button>
                <Button icon={Trash2} onClick={() => setDel(i)}>
                  Delete
                </Button>
              </div>
            </article>
          ))}
      </div>
      {!records.length && (
        <Empty
          title="A place for the details."
          text="Upload a file from your computer or phone and give it a name."
        />
      )}
      {Array.isArray(project[section]) && project[section].length > 0 && (
        <section className="panel">
          <h3>Previously saved records</h3>
          <p>Your original structured records are preserved here.</p>
          {project[section].map((r, i) => (
            <div className="legacy-record" key={i}>
              {Object.entries(r).map(([k, v]) => (
                <p key={k}>
                  <strong>{k}: </strong>
                  {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </p>
              ))}
            </div>
          ))}
        </section>
      )}
      {(upload || rename !== null) && (
        <Modal
          title={upload ? "Upload a named file" : "Rename file"}
          onClose={() => {
            setUpload(false);
            setRename(null);
          }}
        >
          <DraftGuard />
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                if (!title.trim()) throw new Error("Enter a file name.");
                let next = clone(records);
                if (upload) {
                  if (!file) throw new Error("Choose a file.");
                  if (file.size > 5 * 1024 * 1024)
                    throw new Error("Maximum file size is 5 MB.");
                  if (
                    records.reduce((s, r) => s + (r.size || 0), 0) + file.size >
                    20 * 1024 * 1024
                  )
                    throw new Error("This library’s limit is 20 MB.");
                  next.push(await readFile(file, title.trim(), note));
                } else next[rename].title = title.trim();
                await saveProject({ ...project, [field]: next });
                setUpload(false);
                setRename(null);
              } catch (e) {
                notify(e.message, true);
              }
            }}
          >
            <Field
              label="File name"
              value={title}
              onChange={setTitle}
              required
            />
            {upload && (
              <>
                <label className="upload-zone">
                  <Upload size={28} />
                  <span>{file?.name || "Choose a file from your device"}</span>
                  <small>Up to 5 MB per file</small>
                  <input
                    type="file"
                    aria-label="Choose file"
                    onChange={(e) => setFile(e.target.files[0])}
                    required
                  />
                </label>
                <Field
                  label="Description / revision (optional)"
                  area
                  value={note}
                  onChange={setNote}
                />
              </>
            )}
            <Button kind="primary" disabled={busy} icon={Save}>
              Save file
            </Button>
          </form>
        </Modal>
      )}
      {del !== null && (
        <Confirm
          title={records[del].title}
          onClose={() => setDel(null)}
          busy={busy}
          onConfirm={async () => {
            await saveProject({
              ...project,
              [field]: records.filter((_, i) => i !== del),
            })
              .then(() => setDel(null))
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}
createRoot(document.getElementById("root")).render(<App />);

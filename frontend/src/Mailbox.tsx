import { useEffect, useState } from "react";
import { api, errText } from "./api";
import type { Entry, Label, Page } from "./types";
import { useI18n } from "./i18n";

const SYSTEM = ["inbox", "starred", "sent", "archive", "spam"] as const;
const PAGE_SIZE = 20;

export default function Mailbox() {
  const { t, fmt } = useI18n();
  const [labels, setLabels] = useState<Label[]>([]);
  const [folder, setFolder] = useState("inbox");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Entry> | null>(null);
  // Key of the last finished request: while it differs from the current key, a request is in flight
  const [settled, setSettled] = useState("");
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [open, setOpen] = useState<Entry | null>(null);
  const [tick, setTick] = useState(0);
  const [newLabel, setNewLabel] = useState("");
  const [menu, setMenu] = useState(false);
  const reload = () => setTick((t) => t + 1);

  const loadLabels = () =>
    api<Label[] | Page<Label>>("/labels/")
      .then((r) => setLabels(Array.isArray(r) ? r : r.results))
      .catch(() => {});
  useEffect(() => {
    loadLabels();
  }, []);

  const key = `${folder}|${page}|${tick}`;
  const loading = settled !== key;
  const error = failure?.key === key ? failure.message : "";

  useEffect(() => {
    let off = false;
    const q =
      folder === "trash"
        ? "deleted=true"
        : `label=${encodeURIComponent(folder)}`;
    api<Page<Entry>>(`/mailbox/?${q}&page=${page}&page_size=${PAGE_SIZE}`)
      .then((r) => {
        if (!off) setData(r);
      })
      .catch((e) => {
        if (off) return;
        if (page > 1) setPage(1);
        else setFailure({ key, message: errText(e) });
      })
      .finally(() => {
        if (!off) setSettled(key);
      });
    return () => {
      off = true;
    };
  }, [folder, page, key]);

  const go = (f: string) => {
    setFolder(f);
    setPage(1);
    setOpen(null);
    setMenu(false);
  };

  function openEntry(e: Entry) {
    setOpen(e.is_read ? e : { ...e, is_read: true });
    if (!e.is_read)
      api(`/mailbox/${e.id}/update_state/`, {
        method: "PATCH",
        body: { is_read: true },
      })
        .then(reload)
        .catch(() => {});
  }

  async function addLabel() {
    const name = newLabel.trim();
    if (!name) return;
    try {
      await api("/labels/", { method: "POST", body: { name } });
      setNewLabel("");
      loadLabels();
    } catch (e) {
      alert(errText(e));
    }
  }
  async function removeLabel(l: Label) {
    if (!confirm(t("confirm_delete_label", { name: l.name }))) return;
    try {
      await api(`/labels/${l.id}/`, { method: "DELETE" });
      if (folder === l.name) go("inbox");
      loadLabels();
    } catch (e) {
      alert(errText(e));
    }
  }

  const custom = labels.filter((l) => !l.is_system);
  const lastPage = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const btn = (key: string, title: string) => (
    <button
      key={key}
      className={`nav ${folder === key ? "active" : ""}`}
      onClick={() => go(key)}
    >
      {title}
    </button>
  );

  return (
    <div className={`app ${open ? "reading" : ""}`}>
      <aside className={menu ? "show" : ""}>
        <nav>
          {SYSTEM.map((k) => btn(k, t(k)))}
          {btn("trash", t("trash"))}
        </nav>
        <div className="section">{t("labels_section")}</div>
        <nav>
          {custom.map((l) => (
            <div key={l.id} className="labelrow">
              {btn(l.name, l.name)}
              <button
                className="ghost small"
                title={t("delete_label")}
                onClick={() => removeLabel(l)}
              >
                ✕
              </button>
            </div>
          ))}
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              addLabel();
            }}
          >
            <input
              placeholder={t("new_label")}
              maxLength={50}
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
            />
            <button className="ghost" aria-label={t("add_label")}>
              +
            </button>
          </form>
        </nav>
      </aside>

      <main className="list">
        <div className="topbar">
          <button
            className="ghost burger"
            onClick={() => setMenu(!menu)}
            aria-label={t("menu")}
          >
            ☰
          </button>
          <b>
            {folder === "trash" ||
            (SYSTEM as readonly string[]).includes(folder)
              ? t(folder)
              : folder}
          </b>
          <button className="ghost" onClick={reload} disabled={loading}>
            ↻
          </button>
        </div>
        {error && <p className="error pad">{error}</p>}
        {!error && loading && !data && (
          <p className="muted pad">{t("loading")}</p>
        )}
        {data && !data.results.length && !loading && (
          <p className="muted pad">{t("empty")}</p>
        )}
        <ul>
          {data?.results.map((e) => (
            <li
              key={e.id}
              className={`${e.is_read ? "" : "unread"} ${open?.id === e.id ? "sel" : ""}`}
              onClick={() => openEntry(e)}
            >
              <span className="from ellipsis">
                {e.message.sender ?? t("deleted_user")}
              </span>
              <span className="subj ellipsis">{e.message.subject}</span>
              <span className="muted small date">
                {fmt(e.message.created_at)}
              </span>
            </li>
          ))}
        </ul>
        {data && lastPage > 1 && (
          <div className="pager">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ←
            </button>
            <span className="muted">
              {page} / {lastPage}
            </span>
            <button
              disabled={page >= lastPage}
              onClick={() => setPage(page + 1)}
            >
              →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

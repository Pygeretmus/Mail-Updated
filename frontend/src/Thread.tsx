import { useEffect, useMemo, useState } from "react";
import { api, errText } from "./api";
import { useI18n } from "./i18n";
import type { Entry, FullMessage, Label, Me, Page } from "./types";

interface Props {
  entry: Entry;
  me: Me | null;
  labels: Label[];
  inTrash: boolean;
  onClose: () => void;
  /** undefined: only refresh the list; null: refresh and close; Entry: refresh and show it */
  onChanged: (e?: Entry | null) => void;
}

// Deeper replies stop shifting right, so long chains stay readable on narrow screens
const MAX_INDENT = 4;
const INDENT_PX = 18;

interface Node {
  item: Entry<FullMessage>;
  depth: number;
}

/**
 * Orders a conversation as a tree: every reply sits right under the message it
 * answers, indented one step deeper. Siblings keep the server order (oldest first).
 * A message whose parent isn't in the list (e.g. you were never a recipient of it)
 * becomes a root.
 */
function arrange(items: Entry<FullMessage>[]): Node[] {
  const known = new Set(items.map((i) => i.message.id));
  const children = new Map<number | null, Entry<FullMessage>[]>();
  for (const item of items) {
    const parent = item.message.parent;
    const key = parent !== null && known.has(parent) ? parent : null;
    children.set(key, [...(children.get(key) ?? []), item]);
  }
  const out: Node[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const item of children.get(parent) ?? []) {
      out.push({ item, depth });
      walk(item.message.id, depth + 1);
    }
  };
  walk(null, 0);
  // Safety net: never drop a message, whatever the data looks like
  const placed = new Set(out.map((n) => n.item.id));
  for (const item of items)
    if (!placed.has(item.id)) out.push({ item, depth: 0 });
  return out;
}

/**
 * Which reply buttons can work for a message. Mirrors build_reply_recipients on the
 * backend (the backend stays the source of truth and still validates). Bcc
 * recipients never receive replies, and deleted accounts have no mailbox entries.
 */
function replyOptions(m: FullMessage, myEmail: string | undefined) {
  const own = m.sender !== null && m.sender === myEmail;
  const others = m.recipients.filter(
    (r) => r.role !== "bcc" && r.email !== myEmail,
  );
  return {
    reply: own ? others.some((r) => r.role === "to") : m.sender !== null,
    all: m.sender !== null && !own ? true : others.length > 0,
  };
}

export default function Thread({
  entry,
  me,
  labels,
  inTrash,
  onClose,
  onChanged,
}: Props) {
  const { t, fmt } = useI18n();
  const [msgs, setMsgs] = useState<Entry<FullMessage>[]>([]);
  // Key of the last finished request: while it differs from the current key, a request is in flight
  const [settled, setSettled] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // The message being answered (by message id) and whether it is "reply all"
  const [target, setTarget] = useState<{ id: number; all: boolean } | null>(
    null,
  );
  const [reply, setReply] = useState("");
  const [version, setVersion] = useState(0);
  const key = `${entry.message.thread}|${version}`;
  const loading = settled !== key;
  const nodes = useMemo(() => arrange(msgs), [msgs]);
  const byMessage = useMemo(
    () => new Map(msgs.map((i) => [i.message.id, i.message])),
    [msgs],
  );
  const who = (sender: string | null) => sender ?? t("deleted_user");

  useEffect(() => {
    let off = false;
    api<Entry<FullMessage>[] | Page<Entry<FullMessage>>>(
      `/messages/thread/${entry.message.thread}/`,
    )
      .then((r) => {
        if (!off) setMsgs(Array.isArray(r) ? r : r.results);
      })
      .catch((e) => {
        if (!off) setError(errText(e));
      })
      .finally(() => {
        if (!off) setSettled(key);
      });
    return () => {
      off = true;
    };
  }, [entry.message.thread, key]);

  async function run(
    fn: () => Promise<unknown>,
    result: "close" | "keep" | "reload",
  ) {
    setBusy(true);
    setError("");
    try {
      const r = await fn();
      onChanged(
        result === "close"
          ? null
          : result === "keep"
            ? (r as Entry)
            : undefined,
      );
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }

  const names = entry.labels.map((l) => l.name);
  const relabel = (add: string[], remove: string[]) => {
    const current = new Map(entry.labels.map((l) => [l.name, l.id]));
    remove.forEach((n) => current.delete(n));
    labels
      .filter((l) => add.includes(l.name))
      .forEach((l) => current.set(l.name, l.id));
    return api<Entry>(`/mailbox/${entry.id}/update_state/`, {
      method: "PATCH",
      body: { label_ids: [...current.values()] },
    });
  };
  const starred = names.includes("starred");
  const custom = labels.filter((l) => !l.is_system);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggle = (id: number) =>
    setExpanded((p) => {
      const n = new Set(p);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  useEffect(() => {
    if (!loading)
      document
        .getElementById(`m-${entry.id}`)
        ?.scrollIntoView({ block: "nearest" });
  }, [loading, entry.id]);

  return (
    <section className="reader">
      <div className="toolbar">
        <button className="ghost back" onClick={onClose}>
          ← {t("back")}
        </button>
        {inTrash ? (
          <>
            <button
              disabled={busy}
              onClick={() =>
                run(
                  () =>
                    api(`/mailbox/${entry.id}/restore_entry/`, {
                      method: "POST",
                    }),
                  "close",
                )
              }
            >
              {t("restore")}
            </button>
            <button
              disabled={busy}
              className="danger"
              onClick={() => {
                if (confirm(t("confirm_erase")))
                  run(
                    () =>
                      api(`/mailbox/${entry.id}/erase_entry/`, {
                        method: "DELETE",
                      }),
                    "close",
                  );
              }}
            >
              {t("erase")}
            </button>
          </>
        ) : (
          <>
            <button
              disabled={busy}
              onClick={() =>
                run(
                  () =>
                    relabel(
                      starred ? [] : ["starred"],
                      starred ? ["starred"] : [],
                    ),
                  "keep",
                )
              }
            >
              {starred ? t("unstar") : t("star")}
            </button>
            <details className="menu">
              <summary>🏷 {t("labels")}</summary>
              <div className="pop">
                {custom.length ? (
                  custom.map((l) => (
                    <label key={l.id}>
                      <input
                        type="checkbox"
                        checked={names.includes(l.name)}
                        disabled={busy}
                        onChange={(e) =>
                          run(
                            () =>
                              relabel(
                                e.target.checked ? [l.name] : [],
                                e.target.checked ? [] : [l.name],
                              ),
                            "keep",
                          )
                        }
                      />{" "}
                      {l.name}
                    </label>
                  ))
                ) : (
                  <span className="muted small">{t("no_labels_hint")}</span>
                )}
              </div>
            </details>
            <button
              disabled={busy}
              onClick={() =>
                run(() => relabel(["archive"], ["inbox"]), "close")
              }
            >
              {t("archive")}
            </button>
            <button
              disabled={busy}
              onClick={() => run(() => relabel(["spam"], ["inbox"]), "close")}
            >
              {t("spam")}
            </button>
            <button
              disabled={busy}
              onClick={() =>
                run(
                  () =>
                    api(`/mailbox/${entry.id}/update_state/`, {
                      method: "PATCH",
                      body: { is_read: false },
                    }),
                  "close",
                )
              }
            >
              {t("mark_unread")}
            </button>
            <button
              disabled={busy}
              className="danger"
              onClick={() =>
                run(
                  () =>
                    api(`/mailbox/${entry.id}/delete_entry/`, {
                      method: "POST",
                    }),
                  "close",
                )
              }
            >
              {t("delete")}
            </button>
          </>
        )}
      </div>
      <h2>{entry.message.subject}</h2>
      {entry.labels.some((l) => !l.is_system) && (
        <div className="chips">
          {entry.labels
            .filter((l) => !l.is_system)
            .map((l) => (
              <span key={l.id} className="chip">
                {l.name}
              </span>
            ))}
        </div>
      )}
      {msgs.length > 1 && (
        <p className="muted small">{t("thread_info", { n: msgs.length })}</p>
      )}
      {error && !target && <p className="error">{error}</p>}
      {loading && !msgs.length && <p className="muted">{t("loading")}</p>}
      {nodes.map(({ item, depth }) => {
        const { message: m, id } = item;
        const current = id === entry.id;
        const parent = m.parent !== null ? byMessage.get(m.parent) : undefined;
        const nesting = {
          className: `msg ${depth ? "nested" : ""} ${current ? "current" : ""}`,
          style: { marginLeft: Math.min(depth, MAX_INDENT) * INDENT_PX },
        };
        if (!current && !expanded.has(id))
          return (
            <article
              key={id}
              id={`m-${id}`}
              {...nesting}
              className={`${nesting.className} collapsed`}
              onClick={() => toggle(id)}
            >
              <div className="meta">
                <b>{who(m.sender)}</b>
                <span className="muted small">{fmt(m.created_at)}</span>
              </div>
              <div className="muted ellipsis">{m.body}</div>
            </article>
          );
        const opts = replyOptions(m, me?.email.toLowerCase());
        return (
          <article key={id} id={`m-${id}`} {...nesting}>
            <div className="meta">
              <b>
                {who(m.sender)}{" "}
                {current && <span className="badge">{t("this_message")}</span>}
              </b>
              <span className="muted">{fmt(m.created_at)}</span>
            </div>
            {parent && (
              <div className="muted small">
                {t("in_reply_to", { sender: who(parent.sender) })}
              </div>
            )}
            <div className="muted small">
              {m.recipients
                .map((r) => `${t("role_" + r.role)}: ${r.email}`)
                .join(" · ")}
            </div>
            <p className="body">{m.body}</p>
            <div className="actions">
              {!inTrash && (
                <>
                  <button
                    className="link small"
                    disabled={!opts.reply}
                    onClick={() => setTarget({ id: m.id, all: false })}
                  >
                    {t("reply")}
                  </button>
                  <button
                    className="link small"
                    disabled={!opts.all}
                    onClick={() => setTarget({ id: m.id, all: true })}
                  >
                    {t("reply_all")}
                  </button>
                </>
              )}
              {!current && (
                <button className="link small" onClick={() => toggle(id)}>
                  {t("collapse")}
                </button>
              )}
            </div>
            {!inTrash && !opts.all && (
              <p className="muted small">{t("cant_reply")}</p>
            )}
            {target?.id === m.id && (
              <form
                className="reply"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api(`/messages/${m.id}/reply/`, {
                      method: "POST",
                      body: { body: reply, reply_all: target.all },
                    });
                    setReply("");
                    setTarget(null);
                    setVersion((v) => v + 1);
                  }, "reload");
                }}
              >
                <div className="muted small">
                  {target.all
                    ? t("replying_all")
                    : t("replying_to", { sender: who(m.sender) })}
                </div>
                <textarea
                  rows={4}
                  required
                  autoFocus
                  placeholder={t("reply_ph", { sender: who(m.sender) })}
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                />
                {error && <p className="error">{error}</p>}
                <div className="row between">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setTarget(null);
                      setError("");
                    }}
                  >
                    {t("cancel")}
                  </button>
                  <button className="primary" disabled={busy || !reply.trim()}>
                    {t("send")}
                  </button>
                </div>
              </form>
            )}
          </article>
        );
      })}
    </section>
  );
}

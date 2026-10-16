import { useState, type FormEvent } from "react";
import { api, errText } from "./api";
import { useI18n } from "./i18n";

const split = (s: string) => s.split(/[,;\s]+/).filter(Boolean);

export default function Compose({
  onClose,
  onSent,
}: {
  onClose: () => void;
  onSent: () => void;
}) {
  const { t } = useI18n();
  const [f, setF] = useState({
    to: "",
    cc: "",
    bcc: "",
    subject: "",
    body: "",
  });
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/messages/compose/", {
        method: "POST",
        body: {
          to: split(f.to),
          cc: split(f.cc),
          bcc: split(f.bcc),
          subject: f.subject,
          body: f.body,
        },
      });
      onSent();
    } catch (err) {
      setError(errText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <form className="modal" onSubmit={submit}>
        <header>
          <b>{t("new_message")}</b>
          <button type="button" className="ghost" onClick={onClose}>
            ✕
          </button>
        </header>
        <input
          placeholder={t("to_ph")}
          required
          value={f.to}
          onChange={set("to")}
        />
        {more ? (
          <>
            <input placeholder={t("cc_ph")} value={f.cc} onChange={set("cc")} />
            <input
              placeholder={t("bcc_ph")}
              value={f.bcc}
              onChange={set("bcc")}
            />
          </>
        ) : (
          <button type="button" className="link" onClick={() => setMore(true)}>
            {t("add_cc")}
          </button>
        )}
        <input
          placeholder={t("subject")}
          required
          maxLength={255}
          value={f.subject}
          onChange={set("subject")}
        />
        <textarea
          placeholder={t("body_ph")}
          required
          rows={10}
          value={f.body}
          onChange={set("body")}
        />
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? t("sending") : t("send")}
        </button>
      </form>
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { api, errText, logout } from "./api";
import { useI18n } from "./i18n";

export default function DeleteAccount({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/accounts/destroy/", {
        method: "POST",
        body: { current_password: password },
      });
      logout();
    } catch (err) {
      setError(errText(err));
      setBusy(false);
    }
  }

  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && !busy && onClose()}
    >
      <form className="modal" onSubmit={submit}>
        <header>
          <b>{t("da_title")}</b>
        </header>
        <p>{t("da_text")}</p>
        <label className="small muted">{t("da_password")}</label>
        <input
          type="password"
          placeholder={t("da_password_ph")}
          autoComplete="current-password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <div className="row between">
          <button type="button" onClick={onClose} disabled={busy}>
            {t("cancel")}
          </button>
          <button className="primary danger-bg" disabled={busy || !password}>
            {t("da_btn")}
          </button>
        </div>
      </form>
    </div>
  );
}

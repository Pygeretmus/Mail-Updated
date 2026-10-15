import { useState, type FormEvent } from "react";
import { api, errText, login } from "./api";
import { useI18n } from "./i18n";
import { LangToggle } from "./LangControls";

interface Props {
  onDone: () => void;
  theme: string;
  toggleTheme: () => void;
}

export default function Auth({ onDone, theme, toggleTheme }: Props) {
  const { t } = useI18n();
  const [register, setRegister] = useState(false);
  const [f, setF] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (register)
        await api("/accounts/", { method: "POST", body: f, auth: false });
      await login(f.email, f.password);
      onDone();
    } catch (err) {
      setError(errText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="theme row">
        <LangToggle />
        <button className="ghost" onClick={toggleTheme}>
          {theme === "dark" ? "☀️" : "🌙"}
        </button>
      </div>
      <form className="card" onSubmit={submit}>
        <h1>{register ? t("register_title") : t("login_title")}</h1>
        {register && (
          <div className="row">
            <input
              placeholder={t("first_name")}
              required
              value={f.first_name}
              onChange={set("first_name")}
            />
            <input
              placeholder={t("last_name")}
              required
              value={f.last_name}
              onChange={set("last_name")}
            />
          </div>
        )}
        <input
          type="email"
          placeholder={t("email")}
          required
          autoComplete="email"
          value={f.email}
          onChange={set("email")}
        />
        <input
          type="password"
          placeholder={t("password")}
          required
          autoComplete={register ? "new-password" : "current-password"}
          value={f.password}
          onChange={set("password")}
        />
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? t("wait") : register ? t("create_account") : t("sign_in")}
        </button>
        <button
          type="button"
          className="link"
          onClick={() => {
            setRegister(!register);
            setError("");
          }}
        >
          {register ? t("have_account") : t("no_account")}
        </button>
      </form>
    </div>
  );
}

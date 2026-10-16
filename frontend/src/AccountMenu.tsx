import { useEffect, useRef, useState } from "react";
import { logout } from "./api";
import { useI18n } from "./i18n";
import { LangSwitch } from "./LangControls";
import type { Me } from "./types";

interface Props {
  me: Me | null;
  theme: string;
  toggleTheme: () => void;
  onDelete: () => void;
}

export default function AccountMenu({
  me,
  theme,
  toggleTheme,
  onDelete,
}: Props) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const name = [me?.first_name, me?.last_name].filter(Boolean).join(" ");
  const initial = (me?.first_name || me?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="acc" ref={ref}>
      {open && (
        <div className="acc-pop" role="menu">
          <div className="item">
            <span className="muted small">{t("language")}</span>
            <LangSwitch />
          </div>
          <button className="menuitem" role="menuitem" onClick={toggleTheme}>
            {theme === "dark" ? t("theme_light") : t("theme_dark")}
          </button>
          <button className="menuitem" role="menuitem" onClick={logout}>
            {t("logout")}
          </button>
          <div className="danger-zone">
            <button
              className="menuitem"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onDelete();
              }}
            >
              {t("delete_account")}
            </button>
          </div>
        </div>
      )}
      <button
        className="acc-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="avatar">{initial}</span>
        <span className="acc-text">
          {name && <b className="ellipsis small">{name}</b>}
          <span className="muted small ellipsis">{me?.email}</span>
        </span>
        <span className="muted">{open ? "▾" : "▴"}</span>
      </button>
    </div>
  );
}

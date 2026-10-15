import { useI18n } from "./i18n";

export function LangSwitch() {
  const { lang, setLang } = useI18n();
  return (
    <div className="seg" role="group" aria-label="Language">
      {(["en", "uk"] as const).map((l) => (
        <button
          key={l}
          type="button"
          className={lang === l ? "active" : ""}
          onClick={() => setLang(l)}
        >
          {l === "en" ? "EN" : "УК"}
        </button>
      ))}
    </div>
  );
}

/** Compact language toggle (for the sign-in screen). */
export function LangToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <button
      className="ghost"
      type="button"
      aria-label={t("language")}
      onClick={() => setLang(lang === "en" ? "uk" : "en")}
    >
      🌐 {lang === "en" ? "EN" : "УК"}
    </button>
  );
}

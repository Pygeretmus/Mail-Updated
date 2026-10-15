import { useEffect, useState, type ReactNode } from "react";
import {
  I18nContext,
  getCurrentLang,
  setCurrentLang,
  tr,
  type Lang,
} from "./i18n";

export default function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setL] = useState<Lang>(getCurrentLang());
  const setLang = (l: Lang) => {
    setCurrentLang(l);
    setL(l);
  };
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = tr("app_title");
  }, [lang]);
  return (
    <I18nContext.Provider value={{ lang, setLang }}>
      {children}
    </I18nContext.Provider>
  );
}

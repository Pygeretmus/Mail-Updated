import { useEffect, useState } from "react";
import { api, hasSession, setLogoutHandler } from "./api";
import { useTheme } from "./theme";
import type { Me } from "./types";
import Auth from "./Auth";

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [authed, setAuthed] = useState(hasSession());

  useEffect(() => {
    setLogoutHandler(() => {
      setAuthed(false);
    });
  }, []);
  useEffect(() => {
    if (authed) api<Me>("/accounts/me/").catch(() => {});
  }, [authed]);

  return (
    <Auth
      onDone={() => setAuthed(true)}
      theme={theme}
      toggleTheme={toggleTheme}
    />
  );
}

import { useEffect, useState } from "react";
import { api, hasSession, setLogoutHandler } from "./api";
import { useTheme } from "./theme";
import type { Me } from "./types";
import Auth from "./Auth";
import Mailbox from "./Mailbox";

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [authed, setAuthed] = useState(hasSession());
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    setLogoutHandler(() => {
      setAuthed(false);
      setMe(null);
    });
  }, []);
  useEffect(() => {
    if (authed)
      api<Me>("/accounts/me/")
        .then(setMe)
        .catch(() => {});
  }, [authed]);

  if (!authed)
    return (
      <Auth
        onDone={() => setAuthed(true)}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    );
  return <Mailbox me={me} />;
}

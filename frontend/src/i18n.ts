import { createContext, useContext } from "react";

export type Lang = "en" | "uk";

const DICT: Record<Lang, Record<string, string>> = {
  en: {
    app_title: "Mail",
    login_title: "Sign in",
    register_title: "Create account",
    first_name: "First name",
    last_name: "Last name",
    email: "Email",
    password: "Password",
    wait: "Please wait…",
    create_account: "Create account",
    sign_in: "Sign in",
    have_account: "Already have an account? Sign in",
    no_account: "Don't have an account? Register",
    new_message: "New message",
    to_ph: "To (comma separated)",
    add_cc: "+ Cc / Bcc",
    cc_ph: "Cc",
    bcc_ph: "Bcc",
    subject: "Subject",
    body_ph: "Message",
    sending: "Sending…",
    send: "Send",
    back: "Back",
    restore: "Restore",
    erase: "Delete forever",
    confirm_erase: "Delete this message forever? This cannot be undone.",
    star: "☆ Star",
    unstar: "★ Unstar",
    labels: "Labels",
    no_labels_hint: "Create a label in the sidebar first",
    archive: "Archive",
    spam: "Spam",
    mark_unread: "Mark unread",
    delete: "Delete",
    loading: "Loading…",
    role_to: "To",
    role_cc: "Cc",
    role_bcc: "Bcc",
    thread_info:
      "Conversation of {n} messages. The opened message is highlighted, others can be expanded.",
    this_message: "This message",
    collapse: "Collapse",
    reply: "Reply",
    reply_ph: "Reply to {sender}…",
    reply_all: "Reply all",
    in_reply_to: "↪ In reply to {sender}",
    replying_to: "Replying to {sender}",
    replying_all: "Replying to everyone",
    cant_reply: "Nobody to reply to: those accounts were deleted.",
    deleted_user: "Deleted user",
    write: "Compose",
    inbox: "Inbox",
    starred: "Starred",
    sent: "Sent",
    trash: "Trash",
    labels_section: "Labels",
    new_label: "New label",
    add_label: "Add label",
    delete_label: "Delete label",
    confirm_delete_label: 'Delete label "{name}"? Messages will be kept.',
    theme_light: "☀️ Light",
    theme_dark: "🌙 Dark",
    logout: "Log out",
    menu: "Menu",
    empty: "Nothing here yet.",
    language: "Language",
    select_message: "Select a message",
    delete_account: "Delete account",
    da_title: "Delete account",
    da_text:
      "Your account, labels and all your messages will be permanently deleted. This cannot be undone.",
    da_password: "Enter your password to confirm",
    da_password_ph: "Password",
    da_btn: "Delete my account",
    cancel: "Cancel",
    err_network: "No connection to the server.",
    err_session: "Session expired, please sign in again.",
    err_throttle: "Too many attempts, try again later.",
    err_generic: "Something went wrong.",
    err_request: "Request failed.",
  },
  uk: {
    app_title: "Пошта",
    login_title: "Вхід",
    register_title: "Реєстрація",
    first_name: "Ім'я",
    last_name: "Прізвище",
    email: "Email",
    password: "Пароль",
    wait: "Зачекайте…",
    create_account: "Створити акаунт",
    sign_in: "Увійти",
    have_account: "Вже є акаунт? Увійти",
    no_account: "Немає акаунта? Зареєструватися",
    new_message: "Новий лист",
    to_ph: "Кому (через кому)",
    add_cc: "+ Копія / прихована копія",
    cc_ph: "Копія",
    bcc_ph: "Прихована копія",
    subject: "Тема",
    body_ph: "Текст листа",
    sending: "Надсилання…",
    send: "Надіслати",
    back: "Назад",
    restore: "Відновити",
    erase: "Видалити назавжди",
    confirm_erase: "Видалити лист назавжди? Це неможливо скасувати.",
    star: "☆ В обране",
    unstar: "★ Прибрати з обраного",
    labels: "Мітки",
    no_labels_hint: "Спочатку створіть мітку на бічній панелі",
    archive: "В архів",
    spam: "У спам",
    mark_unread: "Непрочитане",
    delete: "Видалити",
    loading: "Завантаження…",
    role_to: "Кому",
    role_cc: "Копія",
    role_bcc: "Прихована копія",
    thread_info:
      "Листування з {n} листів. Відкритий лист виділено, інші можна розгорнути.",
    this_message: "Цей лист",
    collapse: "Згорнути",
    reply: "Відповісти",
    reply_ph: "Відповідь для {sender}…",
    reply_all: "Відповісти всім",
    in_reply_to: "↪ У відповідь для {sender}",
    replying_to: "Відповідь для {sender}",
    replying_all: "Відповідь усім",
    cant_reply: "Немає кому відповідати: ці акаунти видалено.",
    deleted_user: "Видалений користувач",
    write: "Написати",
    inbox: "Вхідні",
    starred: "Обране",
    sent: "Надіслані",
    trash: "Кошик",
    labels_section: "Мітки",
    new_label: "Нова мітка",
    add_label: "Додати мітку",
    delete_label: "Видалити мітку",
    confirm_delete_label: "Видалити мітку «{name}»? Листи залишаться.",
    theme_light: "☀️ Світла",
    theme_dark: "🌙 Темна",
    logout: "Вийти",
    menu: "Меню",
    empty: "Тут поки порожньо.",
    language: "Мова",
    select_message: "Виберіть лист",
    delete_account: "Видалити акаунт",
    da_title: "Видалення акаунта",
    da_text:
      "Ваш акаунт, мітки та всі листи буде видалено назавжди. Це неможливо скасувати.",
    da_password: "Введіть пароль для підтвердження",
    da_password_ph: "Пароль",
    da_btn: "Видалити мій акаунт",
    cancel: "Скасувати",
    err_network: "Немає зв'язку з сервером.",
    err_session: "Сесія завершилась, увійдіть знову.",
    err_throttle: "Забагато спроб, спробуйте пізніше.",
    err_generic: "Щось пішло не так.",
    err_request: "Не вдалося виконати запит.",
  },
};

const detect = (): Lang => {
  const saved = localStorage.getItem("lang");
  if (saved === "en" || saved === "uk") return saved;
  return navigator.language.toLowerCase().startsWith("uk") ? "uk" : "en";
};
let current: Lang = detect();

/** Switches the language used by `tr` (called by I18nProvider). */
export const setCurrentLang = (l: Lang) => {
  current = l;
  localStorage.setItem("lang", l);
};
export const getCurrentLang = () => current;

/** Translation outside React (e.g. in api.ts). */
export const tr = (key: string, vars: Record<string, string | number> = {}) => {
  let s = DICT[current][key] ?? DICT.en[key] ?? key;
  for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
};

export const I18nContext = createContext<{
  lang: Lang;
  setLang: (l: Lang) => void;
}>({
  lang: current,
  setLang: () => {},
});

export function useI18n() {
  const { lang, setLang } = useContext(I18nContext);
  const fmt = (iso: string) =>
    new Intl.DateTimeFormat(lang, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  return { lang, setLang, t: tr, fmt };
}

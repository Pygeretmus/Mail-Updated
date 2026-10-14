export interface Label {
  id: number;
  name: string;
  is_system: boolean;
}
export interface Recipient {
  email: string;
  role: string;
}
export interface Preview {
  id: number;
  thread: number;
  sender: string | null;
  subject: string;
  created_at: string;
}
export interface FullMessage extends Preview {
  parent: number | null;
  body: string;
  recipients: Recipient[];
}
export interface Entry<M = Preview> {
  id: number;
  message: M;
  role: string;
  is_read: boolean;
  deleted_at: string | null;
  labels: Label[];
}
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export interface Me {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export type Conversation = {
  id: string;
  title: string;
  platform: string;
  conversation_type: "direct" | "group";
  started_at: string | null;
  ended_at: string | null;
  message_count: number;
  metadata?: { source_timezone?: string };
};
export type Person = {
  id: string;
  display_name: string;
  is_current_user: boolean;
};
export type Preview = Conversation & {
  participants: Person[];
  warnings: string[];
  selection_index: number;
};
export type Message = {
  id: string;
  timestamp: string;
  sender_name: string | null;
  sender_id: string | null;
  text: string | null;
  message_type: string;
  reply_to_id: string | null;
  reactions: { emoji: string; count: number }[];
  attachments: { reference: string }[];
  metadata: Record<string, unknown>;
};
export type Activity = {
  daily: { date: string; count: number }[];
  weekly: { date: string; count: number }[];
  monthly: { date: string; count: number }[];
  hourly: { label: string; count: number }[];
  weekday: { label: string; count: number }[];
};
export type StatsPerson = {
  id: string;
  name: string;
  is_current_user: boolean;
  message_count: number;
  percentage: number;
  text_count: number;
  media_count: number;
  total_characters: number;
  average_length: number;
  median_length: number;
  active_days: number;
  sessions_started: number;
  response_times: {
    median: number;
    mean: number;
    p25: number;
    p75: number;
    p90: number;
    count: number;
  } | null;
  activity: Activity;
  types: Record<string, number>;
};
export type Analytics = {
  total_messages: number;
  text_messages: number;
  media_messages: number;
  active_days: number;
  messages_per_active_day: number;
  longest_inactivity_seconds: number;
  sessions: {
    total: number;
    average_messages: number;
    median_length_seconds: number;
    longest_seconds: number;
    gap_hours: number;
  };
  participants: StatsPerson[];
  activity: Activity;
  interactions: {
    participants: { id: string; name: string }[];
    matrix: number[][];
    signals: number;
  } | null;
  reactions: {
    total: number;
    given: Record<string, number>;
    received: Record<string, number>;
    common: Record<string, number>;
    note: string;
  } | null;
  response_method: string;
  timezone: string;
};

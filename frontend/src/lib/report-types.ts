export type Tone = "fun" | "balanced" | "analytical";
export type Finding = {
  id: string;
  family: string;
  score?: number;
  display_score?: number;
  category: string;
  section: string;
  title: string;
  description: string;
  value: string;
  label: string;
  participant_ids: string[];
  facts: { label: string; value: number; unit: string }[];
  evidence_ids: string[];
  evidence_total: number;
  method: string;
  caveat: string | null;
  visual_type: "bars" | "trend" | "pair" | "none";
  visual: { label: string; value: number; secondary?: number | null }[];
  interpretation: boolean;
  source: "measured" | "ai";
  moment_kind?: string | null;
  source_quotes?: {
    message_id: string;
    text: string;
    sender_name: string;
    sender_id?: string;
    timestamp: string;
  }[];
};
export type Era = {
  period: string;
  title: string;
  summary: string;
  message_count: number;
  active_days: number;
  late_share: number;
  weekend_share: number;
  average_length: number;
  leader: string | null;
  evidence_ids: string[];
  partial: boolean;
};
export type Synthesis = {
  insights: Finding[];
  model: string;
  created_at: string;
  coverage: { sampled_messages: number; eligible_messages: number };
  calls: number;
  usage: { input_tokens: number; output_tokens: number };
  rejected_candidates: number;
  note: string;
};
export type ChatReport = {
  behaviors?: {
    version?: number;
    processed: number;
    total: number;
    truncated?: number;
    participant_messages?: Record<string, number>;
    definitions: Record<string, { title: string; description: string }>;
    categories: Record<
      string,
      Record<string, { count: number; evidence_ids: string[] }>
    >;
    interests: Record<
      string,
      Record<string, { count: number; evidence_ids: string[] }>
    >;
  } | null;
  verdict?: {
    summary: string;
    suggestion: string;
    finding_ids: string[];
  } | null;
  cover?: import("@/components/report/story-timeline").StoryCover | null;
  version: string;
  conversation_id: string;
  title: string;
  tone: Tone;
  timezone: string;
  session_gap_hours: number;
  snapshot: {
    messages: number;
    all_records: number;
    participants: number;
    active_days: number;
    sessions: number;
    first: string | null;
    last: string | null;
  };
  insights: Finding[];
  timeline: Era[];
  coverage: {
    explicit_replies: number;
    known_reactions: number;
    unknown_reaction_actors: number;
    reaction_data_available: boolean;
    eligible_findings: number;
    shown_findings: number;
    small_sample: boolean;
    months: number;
  };
  methodology: string[];
  fingerprint: string;
  synthesis: Synthesis | null;
};
export type ProviderStatus = {
  configured: boolean;
  provider: string;
  model: string;
  max_messages: number;
  max_text_characters: number;
  max_calls: number;
  consent_required: boolean;
};

export type AssistantMessageRole = "user" | "assistant";

export interface AssistantMessage {
  id: string;
  patient_id: string;
  role: AssistantMessageRole;
  content: string;
  is_emergency_override: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  extra_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  has_2fa: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  requires_2fa?: boolean;
}

export interface Session {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  is_current: boolean;
  created_at: string;
  last_used_at: string;
}

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface Enable2FAResponse {
  secret: string;
  qr_uri: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number | null;
  chunk_count: number;
  status: "pending" | "processing" | "ready" | "failed";
  error_message: string | null;
  tags: string[];
  folder: string | null;
  created_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface SourceCitation {
  document_id: string;
  document_name: string;
  page_number: number | null;
  chunk_text: string;
  relevance_score: number;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  sources: SourceCitation[];
  follow_up_suggestions: string[];
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: string | null;
  feedback: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  model: string | null;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export interface APIKey {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  key?: string;
}

export interface AdminStats {
  users: number;
  documents: number;
  conversations: number;
  messages: number;
  feedback: { positive: number; negative: number };
}

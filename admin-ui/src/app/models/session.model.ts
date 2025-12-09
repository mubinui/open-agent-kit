export interface Session {
  session_id: string;
  workflow_id: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  active: boolean;
  turn_count: number;
  metadata: Record<string, any>;
}

export interface Message {
  role: string;
  content: string;
  name?: string;
  timestamp: string;
}

export interface ConversationResult {
  session_id: string;
  response: string;
  chat_history: Message[];
  summary: string;
  cost: Record<string, any>;
  turn_count: number;
  safety_passed: boolean;
  metadata: Record<string, any>;
}

export enum ConversationPattern {
  TWO_AGENT = 'two_agent',
  SEQUENTIAL = 'sequential',
  GROUP_CHAT = 'group_chat',
  NESTED = 'nested'
}

export interface WorkflowStep {
  sender_id: string;
  recipient_id: string;
  message?: string;
  max_turns: number;
  summary_method: string;
}

export interface GroupChatConfig {
  agents: string[];
  max_round: number;
  speaker_selection_method: string;
  allowed_transitions?: Record<string, string[]>;
  send_introductions: boolean;
}

export interface WorkflowConfig {
  id: string;
  name: string;
  description: string;
  pattern: ConversationPattern;
  steps?: WorkflowStep[];
  group_chat?: GroupChatConfig;
  entry_agent_id: string;
  recipient_agent_id?: string;
  max_turns?: number;
  summary_method?: string;
  metadata?: Record<string, any>;
  version?: number;
  last_updated?: string;
  updated_by?: string;
  etag?: string;
  workflow_type?: string;
  persistence?: string;
  enabled?: boolean;
}

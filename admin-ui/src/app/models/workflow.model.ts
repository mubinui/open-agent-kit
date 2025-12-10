export enum ConversationPattern {
  TWO_AGENT = 'two_agent',
  SEQUENTIAL = 'sequential',
  GROUP_CHAT = 'group_chat',
  NESTED = 'nested',
  SELECTOR = 'selector'
}

export interface WorkflowStep {
  sender_id: string;
  recipient_id: string;
  message?: string;
  max_turns: number;
  summary_method: string;
  carryover?: boolean;
  clear_history?: boolean;
}

export interface GroupChatConfig {
  agents: string[];
  max_round: number;
  speaker_selection_method: string;
  allowed_transitions?: Record<string, string[]>;
  send_introductions: boolean;
  admin_name?: string;
  select_speaker_message_template?: string;
  select_speaker_auto_verbose?: boolean;
}

export interface NestedChatConfig {
  trigger_agent_id: string;
  nested_chats: Array<{
    recipient_id: string;
    message?: string;
    max_turns?: number;
    summary_method?: string;
  }>;
  trigger_condition?: string;
  position?: number;
}

export interface SelectorConfig {
  routing_agents: Record<string, string>;
  default_agent: string;
  max_routing_attempts: number;
}

export interface WorkflowNodePosition {
  x: number;
  y: number;
}

export interface WorkflowNode {
  id: string;
  agent_id: string;
  position: WorkflowNodePosition;
  config: Record<string, any>;
}

export interface WorkflowConnection {
  from_node: string;
  to_node: string;
  type: string;
}

export interface WorkflowConfig {
  id: string;
  name: string;
  description: string;
  pattern: ConversationPattern;
  steps?: WorkflowStep[];
  group_chat?: GroupChatConfig;
  nested_chats?: NestedChatConfig[];
  selector_config?: SelectorConfig;
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
  nodes?: WorkflowNode[];
  connections?: WorkflowConnection[];
}

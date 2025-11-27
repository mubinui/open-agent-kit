export enum AgentType {
  CONVERSABLE = 'conversable',
  RETRIEVE_USER_PROXY = 'retrieve_user_proxy',
  GROUP_CHAT_MANAGER = 'group_chat_manager'
}

export enum HumanInputMode {
  ALWAYS = 'ALWAYS',
  NEVER = 'NEVER',
  TERMINATE = 'TERMINATE'
}

export interface LLMConfig {
  provider_id: string;
  model: string;
  temperature: number;
  max_tokens?: number;
  cache_seed?: number;
  timeout: number;
}

export interface RetrieveConfig {
  task: string;
  docs_path: string[];
  chunk_token_size: number;
  vector_db: string;
  collection_name: string;
  embedding_model: string;
  get_or_create: boolean;
  db_config?: Record<string, any>;
}

export interface AgentConfig {
  id: string;
  type: AgentType;
  name: string;
  system_message?: string;
  llm_config?: LLMConfig;
  human_input_mode: HumanInputMode;
  code_execution_config?: Record<string, any> | boolean;
  tools: string[];
  max_consecutive_auto_reply: number;
  retrieve_config?: RetrieveConfig;
  description?: string;
  version?: number;
  last_updated?: string;
  updated_by?: string;
  etag?: string;
}

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AgentConfig } from '../models/agent.model';
import { ToolConfig } from '../models/tool.model';
import { WorkflowConfig } from '../models/workflow.model';

export interface ApiProviderModel {
  name: string;
  default?: boolean;
  capabilities?: string[];
  pricing?: {
    input_per_million_tokens: number;
    output_per_million_tokens: number;
    currency: string;
  };
}

export interface ApiProvider {
  id: string;
  name: string;
  type: string;
  description?: string;
  base_url?: string;
  models?: ApiProviderModel[];
  enabled?: boolean;
}

export interface Session {
  session_id: string;
  workflow_id: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  active: boolean;
  metadata: Record<string, any>;
}

export interface Message {
  role: string;
  content: string;
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

export interface DashboardMetrics {
  active_sessions: number;
  total_requests: number;
  error_rate: number;
  total_cost: number;
  request_rate_history: { timestamp: string; count: number }[];
  error_rate_history: { timestamp: string; rate: number }[];
  cost_history: { timestamp: string; cost: number }[];
}

export interface ConfigVersion {
  version: number;
  etag: string;
  last_updated: string;
  updated_by: string;
  config: any;
}

export interface ConflictResponse {
  status: 'conflict';
  current_version: number;
  current_config: any;
  your_version: number;
  diff: {
    added: string[];
    removed: string[];
    modified: Array<{ field: string; current: any; yours: any }>;
  };
}

export interface ConfigHistoryEntry {
  version: number;
  timestamp: string;
  updated_by: string;
  summary: string;
  config: any;
}

export interface VectorDbConfig {
  id: string;
  type: string;
  enabled: boolean;
  base_url: string;
  default_collection: string;
  timeout: number;
  description: string;
  health_status?: string;
  health_details?: Record<string, any>;
}

export interface RagCollections {
  collections: string[];
  total: number;
}

export interface ToolExecutionResponse {
  status: string;
  result: any;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = '/api/v1';

  // Session endpoints
  createSession(workflowId: string, userId?: string, headers?: Record<string, string>): Observable<Session> {
    const options = headers ? { headers } : {};
    return this.http.post<Session>(`${this.baseUrl}/sessions`, { workflow_id: workflowId, user_id: userId }, options);
  }

  getSession(sessionId: string): Observable<Session> {
    return this.http.get<Session>(`${this.baseUrl}/sessions/${sessionId}`);
  }

  deleteSession(sessionId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/sessions/${sessionId}`);
  }

  sendMessage(sessionId: string, message: string, pattern?: string, headers?: Record<string, string>): Observable<ConversationResult> {
    const options = headers ? { headers } : {};
    return this.http.post<ConversationResult>(`${this.baseUrl}/sessions/${sessionId}/messages`, { message, pattern }, options);
  }

  getChatHistory(sessionId: string): Observable<Message[]> {
    return this.http.get<Message[]>(`${this.baseUrl}/sessions/${sessionId}/history`);
  }

  // Agent endpoints
  getAgents(): Observable<AgentConfig[]> {
    return this.http.get<AgentConfig[]>(`${this.baseUrl}/agents`);
  }

  getAgent(agentId: string): Observable<AgentConfig> {
    return this.http.get<AgentConfig>(`${this.baseUrl}/agents/${agentId}`);
  }

  getAgentWithVersion(agentId: string): Observable<{ config: AgentConfig; version: string }> {
    return this.http.get<{ config: AgentConfig; version: string }>(`${this.baseUrl}/configs/agent/${agentId}`);
  }

  createAgent(agent: AgentConfig): Observable<AgentConfig> {
    return this.http.post<AgentConfig>(`${this.baseUrl}/agents`, agent);
  }

  updateAgent(agentId: string, agent: AgentConfig, versionToken?: string): Observable<AgentConfig> {
    const options = versionToken ? { headers: { 'If-Match': versionToken } } : {};
    return this.http.put<AgentConfig>(`${this.baseUrl}/agents/${agentId}`, agent, options);
  }

  deleteAgent(agentId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/agents/${agentId}`);
  }

  getAgentHistory(agentId: string, limit: number = 10): Observable<ConfigHistoryEntry[]> {
    return this.http.get<ConfigHistoryEntry[]>(`${this.baseUrl}/configs/agent/${agentId}/history`, { params: { limit: limit.toString() } });
  }

  rollbackAgent(agentId: string, targetVersion: number): Observable<AgentConfig> {
    return this.http.post<AgentConfig>(`${this.baseUrl}/configs/agent/${agentId}/rollback`, { target_version: targetVersion });
  }

  // Tool endpoints
  getTools(): Observable<ToolConfig[]> {
    return this.http.get<ToolConfig[]>(`${this.baseUrl}/tools`);
  }

  getTool(toolId: string): Observable<ToolConfig> {
    return this.http.get<ToolConfig>(`${this.baseUrl}/tools/${toolId}`);
  }

  getToolWithVersion(toolId: string): Observable<{ config: ToolConfig; version: string }> {
    return this.http.get<{ config: ToolConfig; version: string }>(`${this.baseUrl}/configs/tool/${toolId}`);
  }

  createTool(tool: ToolConfig): Observable<ToolConfig> {
    return this.http.post<ToolConfig>(`${this.baseUrl}/tools`, tool);
  }

  updateTool(toolId: string, tool: ToolConfig, versionToken?: string): Observable<ToolConfig> {
    const options = versionToken ? { headers: { 'If-Match': versionToken } } : {};
    return this.http.put<ToolConfig>(`${this.baseUrl}/tools/${toolId}`, tool, options);
  }

  deleteTool(toolId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/tools/${toolId}`);
  }

  getToolHistory(toolId: string, limit: number = 10): Observable<ConfigHistoryEntry[]> {
    return this.http.get<ConfigHistoryEntry[]>(`${this.baseUrl}/configs/tool/${toolId}/history`, { params: { limit: limit.toString() } });
  }

  rollbackTool(toolId: string, targetVersion: number): Observable<ToolConfig> {
    return this.http.post<ToolConfig>(`${this.baseUrl}/configs/tool/${toolId}/rollback`, { target_version: targetVersion });
  }

  executeTool(toolId: string, args: Record<string, any>, headers?: Record<string, string>): Observable<ToolExecutionResponse> {
    const options = headers ? { headers } : {};
    return this.http.post<ToolExecutionResponse>(`${this.baseUrl}/tools/${toolId}/execute`, { args }, options);
  }

  // Workflow endpoints
  getWorkflows(): Observable<WorkflowConfig[]> {
    return this.http.get<WorkflowConfig[]>(`${this.baseUrl}/workflows`);
  }

  getWorkflow(workflowId: string): Observable<WorkflowConfig> {
    return this.http.get<WorkflowConfig>(`${this.baseUrl}/workflows/${workflowId}`);
  }

  getWorkflowWithVersion(workflowId: string): Observable<{ config: WorkflowConfig; version: string }> {
    return this.http.get<{ config: WorkflowConfig; version: string }>(`${this.baseUrl}/configs/workflow/${workflowId}`);
  }

  createWorkflow(workflow: WorkflowConfig): Observable<WorkflowConfig> {
    return this.http.post<WorkflowConfig>(`${this.baseUrl}/workflows`, workflow);
  }

  updateWorkflow(workflowId: string, workflow: WorkflowConfig, versionToken?: string): Observable<WorkflowConfig> {
    const options = versionToken ? { headers: { 'If-Match': versionToken } } : {};
    return this.http.put<WorkflowConfig>(`${this.baseUrl}/workflows/${workflowId}`, workflow, options);
  }

  deleteWorkflow(workflowId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/workflows/${workflowId}`);
  }

  getWorkflowHistory(workflowId: string, limit: number = 10): Observable<ConfigHistoryEntry[]> {
    return this.http.get<ConfigHistoryEntry[]>(`${this.baseUrl}/configs/workflow/${workflowId}/history`, { params: { limit: limit.toString() } });
  }

  rollbackWorkflow(workflowId: string, targetVersion: number): Observable<WorkflowConfig> {
    return this.http.post<WorkflowConfig>(`${this.baseUrl}/configs/workflow/${workflowId}/rollback`, { target_version: targetVersion });
  }

  // Metrics endpoint
  getMetrics(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>(`${this.baseUrl}/metrics/dashboard`);
  }

  // Health check
  getHealth(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>('/health');
  }

  // API Providers endpoints
  getApiProviders(): Observable<ApiProvider[]> {
    return this.http.get<ApiProvider[]>(`${this.baseUrl}/api-providers`);
  }

  getApiProvider(providerId: string): Observable<ApiProvider> {
    return this.http.get<ApiProvider>(`${this.baseUrl}/api-providers/${providerId}`);
  }

  // RAG Service endpoints
  getRagService(): Observable<VectorDbConfig> {
    return this.http.get<VectorDbConfig>(`${this.baseUrl}/rag-service`);
  }

  getRagCollections(): Observable<RagCollections> {
    return this.http.get<RagCollections>(`${this.baseUrl}/rag-service/collections`);
  }
}

export interface ToolConfig {
  id: string;
  name: string;
  description: string;
  type?: 'function' | 'api';  // Tool type: function-based or API-based
  entrypoint?: string;  // For function tools: module.path:function_name
  enabled?: boolean;
  settings?: Record<string, any>;
  
  // API-specific fields
  api_url?: string;          // Base URL for API tool
  http_method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';  // HTTP method
  headers?: Record<string, string>;  // HTTP headers
  auth_type?: 'none' | 'bearer' | 'api_key' | 'basic';  // Authentication type
  auth_header?: string;      // Header name for API key auth (e.g., 'X-API-Key')
  auth_env_var?: string;     // Environment variable containing auth credentials
  body_template?: string;    // Request body template with {variable} placeholders
  response_path?: string;    // JSON path to extract response (e.g., 'data.result')
  timeout?: number;          // Request timeout in seconds
  forward_user_context?: boolean; // Whether to forward user context headers
  client_username?: string;  // Override x-client-username header value
  client_roles?: string;     // Override x-client-ref header value (comma-separated)
  
  // Versioning fields
  version?: number;
  last_updated?: string;
  updated_by?: string;
  etag?: string;
}

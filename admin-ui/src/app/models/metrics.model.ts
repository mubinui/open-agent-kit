export interface DashboardMetrics {
  active_sessions: number;
  total_requests: number;
  error_rate: number;
  total_cost: number;
  request_rate_history: TimeSeriesData[];
  error_rate_history: TimeSeriesData[];
  cost_history: TimeSeriesData[];
}

export interface TimeSeriesData {
  timestamp: string;
  value: number;
}

export interface ErrorLog {
  timestamp: string;
  error_code: string;
  error_message: string;
  error_type: string;
  request_id: string;
  details?: Record<string, any>;
}

export interface InterfaceAlert {
  id: string;
  name: string;
  description?: string;
  firewall?: {
    id: string;
    name: string;
    ip_address: string;
    firewall_type: {
      id: string;
      name: string;
    };
  } | null;
  firewalls?: Array<{
    id: string;
    name: string;
    ip_address: string;
  }>;
  firewall_type?: string;
  alert_type: 'interface_down' | 'interface_up' | 'bandwidth_high' | 'error_count' | 'custom';
  check_interval: number; // in seconds
  threshold_value?: number;
  command_template: string;
  conditions: Record<string, any>;
  recipients: Array<{
    id: string;
    username: string;
    email: string;
  }>;
  include_admin: boolean;
  include_superuser: boolean;
  is_active: boolean;
  last_check?: string | null;
  last_status: 'unknown' | 'up' | 'down' | 'error' | 'warning';
  next_check?: string | null;
  created_by: {
    id: string;
    username: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
}

export interface InterfaceStatus {
  id: string;
  alert: string;
  interface_name: string;
  status: 'up' | 'down' | 'error' | 'warning' | 'unknown';
  bandwidth_in?: number;
  bandwidth_out?: number;
  error_count: number;
  raw_output: string;
  last_seen: string;
}

export interface AlertExecution {
  id: string;
  alert: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  duration?: number;
  interfaces_checked: number;
  alerts_triggered: number;
  emails_sent: number;
  details: Record<string, any>;
  error_message?: string;
}

export interface InterfaceStatusLog {
  id: string;
  alert: any;
  firewall: any;
  check_time: string;
  total_interfaces: number;
  up_interfaces: number;
  down_interfaces: number;
  alert_triggered: boolean;
  alert_sent: boolean;
}

export interface MonitoringStats {
  total_alerts: number;
  active_alerts: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  total_emails_sent: number;
  last_24h_executions: number;
  last_24h_alerts: number;
}

export interface MonitoringStatus {
  system_status: 'healthy' | 'warning' | 'error';
  active_monitors: number;
  last_health_check: string;
  alerts_scheduled: number;
  next_scheduled_check: string;
}

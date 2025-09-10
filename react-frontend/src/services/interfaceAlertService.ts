import axios from 'axios';
import { API_URL } from '../config';
import { 
  InterfaceAlert, 
  InterfaceStatus, 
  AlertExecution, 
  InterfaceStatusLog,
  MonitoringStats,
  MonitoringStatus
} from '../types/interfaceMonitor';

// Interface for creating alerts - matches what the backend expects
export interface CreateAlertPayload {
  name: string;
  description?: string;
  firewall: string; // This is the firewall ID string
  // Optional multi-targeting
  firewalls?: string[];
  firewall_type?: string;
  alert_type: 'interface_down' | 'interface_up' | 'bandwidth_high' | 'error_count' | 'custom';
  check_interval: number;
  threshold_value?: number;
  command_template: string;
  conditions: Record<string, any>;
  recipients: string[];
  include_admin: boolean;
  include_superuser: boolean;
  is_active?: boolean;
}

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Helper function to handle service unavailability
const handleServiceUnavailable = (endpoint: string) => {
  console.warn(`Interface Monitor Service not available: ${endpoint}`);
  return {
    data: [],
    message: 'Service temporarily unavailable'
  };
};

export const interfaceAlertService = {
  // Interface Alerts
  list: async (): Promise<InterfaceAlert[]> => {
    try {
      const { data } = await api.get('/interface-monitor/api/alerts/');
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return handleServiceUnavailable('/alerts').data;
      }
      throw error;
    }
  },
  
  create: async (payload: CreateAlertPayload): Promise<InterfaceAlert> => {
    try {
      const { data } = await api.post('/interface-monitor/api/alerts/', payload);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Interface Monitor Service not available. Please try again later.');
      }
      throw error;
    }
  },
  
  update: async (id: string, payload: Partial<InterfaceAlert>): Promise<InterfaceAlert> => {
    try {
      const { data } = await api.patch(`/interface-monitor/api/alerts/${id}/`, payload);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Interface Monitor Service not available. Please try again later.');
      }
      throw error;
    }
  },
  
  remove: async (id: string): Promise<void> => {
    try {
      await api.delete(`/interface-monitor/api/alerts/${id}/`);
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Interface Monitor Service not available. Please try again later.');
      }
      throw error;
    }
  },
  
  get: async (id: string): Promise<InterfaceAlert> => {
    try {
      const { data } = await api.get(`/interface-monitor/api/alerts/${id}/`);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Interface Monitor Service not available. Please try again later.');
      }
      throw error;
    }
  },

  // Alert Actions
  toggleActive: async (id: string): Promise<InterfaceAlert> => {
    try {
      const alert = await interfaceAlertService.get(id);
      const updated = await interfaceAlertService.update(id, { is_active: !alert.is_active });
      return updated;
    } catch (error: any) {
      throw error;
    }
  },
  
  test: async (id: string): Promise<any> => {
    try {
      if (!id || id === 'undefined') {
        throw new Error('ID alerte invalide');
      }
      const { data } = await api.post(`/interface-monitor/api/alerts/${id}/test/`);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Interface Monitor Service not available. Please try again later.');
      }
      throw error;
    }
  },

  // Interface Status
  getStatus: async (alertId: string): Promise<InterfaceStatus[]> => {
    try {
      const { data } = await api.get(`/interface-monitor/api/status/?alert=${alertId}`);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return handleServiceUnavailable('/status').data;
      }
      throw error;
    }
  },

  // Alert Executions
  getExecutions: async (alertId: string): Promise<AlertExecution[]> => {
    try {
      const { data } = await api.get(`/interface-monitor/api/executions/?alert=${alertId}`);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return handleServiceUnavailable('/executions').data;
      }
      throw error;
    }
  },

  // Monitoring
  getMonitoringStats: async (): Promise<MonitoringStats> => {
    try {
      const { data } = await api.get('/interface-monitor/api/monitoring/stats/');
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Return default stats when service is unavailable
        return {
          total_alerts: 0,
          active_alerts: 0,
          total_executions: 0,
          successful_executions: 0,
          failed_executions: 0,
          total_emails_sent: 0,
          last_24h_executions: 0,
          last_24h_alerts: 0
        };
      }
      throw error;
    }
  },

  getMonitoringStatus: async (): Promise<MonitoringStatus> => {
    try {
      const { data } = await api.get('/interface-monitor/api/monitoring/status/');
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Return default status when service is unavailable
        return {
          system_status: 'error',
          active_monitors: 0,
          last_health_check: new Date().toISOString(),
          alerts_scheduled: 0,
          next_scheduled_check: new Date().toISOString()
        };
      }
      throw error;
    }
  },

  // Legacy endpoints for backward compatibility
  checkNow: async (id: string): Promise<any> => {
    return interfaceAlertService.test(id);
  },
  
  reportNow: async (id: string): Promise<any> => {
    try {
      const executions = await interfaceAlertService.getExecutions(id);
      const latest = executions[0]; // Most recent execution
      return latest || { message: 'Aucun rapport disponible' };
    } catch (error: any) {
      return { message: 'Service temporairement indisponible' };
    }
  },

  // Logs and Statistics
  logs: async (): Promise<InterfaceStatusLog[]> => {
    try {
      const executions = await api.get('/interface-monitor/api/executions/');
      return executions.data.results || executions.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return handleServiceUnavailable('/executions').data;
      }
      throw error;
    }
  },
  
  recentAlerts: async (): Promise<InterfaceStatusLog[]> => {
    try {
      const executions = await api.get('/interface-monitor/api/executions/?status=completed');
      return executions.data.results || executions.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return handleServiceUnavailable('/executions/recent').data;
      }
      throw error;
    }
  },
  
  statistics: async (): Promise<any> => {
    return interfaceAlertService.getMonitoringStats();
  }
};

export type { InterfaceAlert, InterfaceStatus, AlertExecution, InterfaceStatusLog };

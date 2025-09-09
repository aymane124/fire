import api from '../utils/axiosConfig';

export interface DashboardStats {
  total_firewalls: number;
  active_firewalls: number;
  total_datacenters: number;
  recent_commands: number;
  pending_tasks: number;
  system_health: 'excellent' | 'good' | 'warning' | 'critical';
  last_updated: string;
  user_info: {
    username: string;
    email: string;
    is_staff: boolean;
  };
}

export interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  url: string;
  color: string;
}

export interface DashboardResponse {
  success: boolean;
  data: DashboardStats;
}

export interface QuickActionsResponse {
  success: boolean;
  data: QuickAction[];
}

export interface AdminStatsTotals {
  firewalls: number;
  datacenters: number;
  users: number;
  recent_commands_24h: number;
  commands_last_7_days: number;
  active_terminal_commands: number;
}

export interface AdminTopUser {
  user__id: string;
  user__username: string;
  command_count: number;
}

export interface AdminRecentActivityItem {
  user__id: string;
  user__username: string;
  commands: number;
}

export interface AdminDashboardData {
  totals: AdminStatsTotals;
  top_users_7d: AdminTopUser[];
  recent_activity_24h: AdminRecentActivityItem[];
  generated_at: string;
}

export interface AdminDashboardResponse {
  success: boolean;
  data: AdminDashboardData;
}

class DashboardService {
  /**
   * Récupère toutes les statistiques du dashboard en une seule requête
   */
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const response = await api.get<DashboardResponse>('/dashboard/stats/');
      
      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error('Failed to fetch dashboard stats');
      }
    } catch (error: any) {
      console.error('Error fetching dashboard stats:', error);
      
      // Retourner des données par défaut en cas d'erreur
      return {
        total_firewalls: 0,
        active_firewalls: 0,
        total_datacenters: 0,
        recent_commands: 0,
        pending_tasks: 0,
        system_health: 'warning',
        last_updated: new Date().toISOString(),
        user_info: {
          username: 'Unknown',
          email: '',
          is_staff: false
        }
      };
    }
  }

  /**
   * Récupère les actions rapides disponibles
   */
  async getQuickActions(): Promise<QuickAction[]> {
    try {
      const response = await api.get<QuickActionsResponse>('/dashboard/quick-actions/');
      
      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error('Failed to fetch quick actions');
      }
    } catch (error: any) {
      console.error('Error fetching quick actions:', error);
      
      // Retourner des actions par défaut en cas d'erreur
      return [
        {
          id: 'create_firewall',
          title: 'Créer un pare-feu',
          description: 'Ajouter un nouveau pare-feu',
          icon: 'shield-plus',
          url: '/firewalls/create',
          color: 'blue'
        },
        {
          id: 'upload_csv',
          title: 'Importer CSV',
          description: 'Importer des pare-feux via CSV',
          icon: 'upload',
          url: '/settings',
          color: 'green'
        }
      ];
    }
  }

  /**
   * Récupère les statistiques administrateur enrichies
   */
  async getAdminStats(): Promise<AdminDashboardData | null> {
    try {
      const response = await api.get<AdminDashboardResponse>('/dashboard/admin-stats/');
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error: any) {
      // 403/401: l'utilisateur n'est pas admin ou non authentifié
      return null;
    }
  }

  /**
   * Récupère les statistiques en temps réel (avec cache)
   */
  private cache: {
    stats: DashboardStats | null;
    timestamp: number;
  } = {
    stats: null,
    timestamp: 0
  };

  private readonly CACHE_DURATION = 30000; // 30 secondes

  async getDashboardStatsWithCache(): Promise<DashboardStats> {
    const now = Date.now();
    
    // Vérifier si le cache est encore valide
    if (this.cache.stats && (now - this.cache.timestamp) < this.CACHE_DURATION) {
      return this.cache.stats;
    }
    
    // Récupérer les nouvelles données
    const stats = await this.getDashboardStats();
    
    // Mettre à jour le cache
    this.cache.stats = stats;
    this.cache.timestamp = now;
    
    return stats;
  }

  /**
   * Efface le cache
   */
  clearCache(): void {
    this.cache.stats = null;
    this.cache.timestamp = 0;
  }
}

export default new DashboardService();

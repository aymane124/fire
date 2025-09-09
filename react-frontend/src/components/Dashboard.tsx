import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Server, 
  Activity, 
  Users, 
  Map, 
  Terminal, 
  Settings, 
  FileText,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  Plus,
  Eye,
  Database,
  Network,
  Globe
} from 'lucide-react';
import { Link } from 'react-router-dom';
import dashboardService, { DashboardStats as ServiceDashboardStats, QuickAction as ServiceQuickAction, AdminDashboardData } from '../services/dashboardService';
import { useAuth } from '../contexts/AuthContext';

interface DashboardStats {
  totalFirewalls: number;
  activeFirewalls: number;
  totalDataCenters: number;
  systemHealth: 'excellent' | 'good' | 'warning' | 'critical';
}

interface QuickAction {
  title: string;
  description: string;
  icon: React.ElementType;
  path: string;
  color: string;
  gradient: string;
}

const Dashboard = () => {
  const { isAuthenticated, token } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalFirewalls: 0,
    activeFirewalls: 0,
    totalDataCenters: 0,
    systemHealth: 'good'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [adminData, setAdminData] = useState<AdminDashboardData | null>(null);

  const quickActions: QuickAction[] = [
    {
      title: 'Gérer les Pare-feux',
      description: 'Configurer et surveiller vos pare-feux',
      icon: Shield,
      path: '/firewalls',
      color: 'from-blue-500 to-blue-600',
      gradient: 'bg-gradient-to-r from-blue-500 to-blue-600'
    },
    {
      title: 'Daily Check',
      description: 'Vérifications quotidiennes du système',
      icon: CheckCircle,
      path: '/daily-check',
      color: 'from-green-500 to-green-600',
      gradient: 'bg-gradient-to-r from-green-500 to-green-600'
    },
    {
      title: 'Configuration',
      description: 'Sauvegarder et restaurer les configurations',
      icon: Database,
      path: '/config',
      color: 'from-purple-500 to-purple-600',
      gradient: 'bg-gradient-to-r from-purple-500 to-purple-600'
    },
    {
      title: 'Cartographie',
      description: 'Visualiser vos infrastructures',
      icon: Map,
      path: '/map',
      color: 'from-orange-500 to-orange-600',
      gradient: 'bg-gradient-to-r from-orange-500 to-orange-600'
    },
    {
      title: 'Terminaux',
      description: 'Accès SSH aux pare-feux',
      icon: Terminal,
      path: '/terminals',
      color: 'from-indigo-500 to-indigo-600',
      gradient: 'bg-gradient-to-r from-indigo-500 to-indigo-600'
    },
    {
      title: 'Paramètres',
      description: 'Configuration du système',
      icon: Settings,
      path: '/settings',
      color: 'from-gray-500 to-gray-600',
      gradient: 'bg-gradient-to-r from-gray-500 to-gray-600'
    }
  ];

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        
        // Vérifier l'authentification
        if (!isAuthenticated || !token) {
          console.log('User not authenticated, using mock data');
          setStats({
            totalFirewalls: 0,
            activeFirewalls: 0,
            totalDataCenters: 0,
            systemHealth: 'warning'
          });
          return;
        }

        console.log('Fetching dashboard data using dashboard service...');

        // Utiliser le nouveau service dashboard
        const dashboardData = await dashboardService.getDashboardStatsWithCache();
        // Si l'utilisateur est staff, récupérer les stats admin enrichies
        if (dashboardData.user_info?.is_staff) {
          const data = await dashboardService.getAdminStats();
          setAdminData(data);
        } else {
          setAdminData(null);
        }
        
        console.log('Dashboard data received:', dashboardData);

        // Convertir les données du service vers le format local
        setStats({
          totalFirewalls: dashboardData.total_firewalls,
          activeFirewalls: dashboardData.active_firewalls,
          totalDataCenters: dashboardData.total_datacenters,
          systemHealth: dashboardData.system_health
        });

        console.log('Stats updated:', {
          totalFirewalls: dashboardData.total_firewalls,
          activeFirewalls: dashboardData.active_firewalls,
          totalDataCenters: dashboardData.total_datacenters,
          systemHealth: dashboardData.system_health
        });

      } catch (error: any) {
        console.error('Error fetching dashboard data:', error);
        
        // Utiliser les données par défaut en cas d'erreur
        setStats({
          totalFirewalls: 0,
          activeFirewalls: 0,
          totalDataCenters: 0,
          systemHealth: 'warning'
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [isAuthenticated, token]);

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'excellent': return 'text-green-500';
      case 'good': return 'text-blue-500';
      case 'warning': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'excellent': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'good': return <Activity className="h-5 w-5 text-blue-500" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'critical': return <AlertTriangle className="h-5 w-5 text-red-500" />;
      default: return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg">Chargement du tableau de bord...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Tableau de bord</h1>
            <p className="text-slate-600">Bienvenue dans votre centre de contrôle INWI Firewall</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-white/50 backdrop-blur-sm rounded-xl px-4 py-2 border border-white/20">
              {getHealthIcon(stats.systemHealth)}
              <span className={`font-medium ${getHealthColor(stats.systemHealth)}`}>
                Système {stats.systemHealth === 'excellent' ? 'optimal' : stats.systemHealth}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg hover:shadow-xl transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Pare-feux Total</p>
              <p className="text-3xl font-bold text-slate-900">{stats.totalFirewalls}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-xl">
              <Shield className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
            <span className="text-green-600 font-medium">{stats.activeFirewalls} actifs</span>
          </div>
        </div>

        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg hover:shadow-xl transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Data Centers</p>
              <p className="text-3xl font-bold text-slate-900">{stats.totalDataCenters}</p>
            </div>
            <div className="bg-purple-100 p-3 rounded-xl">
              <Server className="h-8 w-8 text-purple-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <Globe className="h-4 w-4 text-purple-500 mr-1" />
            <span className="text-purple-600 font-medium">Infrastructure</span>
          </div>
        </div>
      </div>

      {adminData && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Vue administrateur</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
              <p className="text-slate-600 text-sm font-medium mb-1">Utilisateurs actifs</p>
              <p className="text-3xl font-bold text-slate-900">{adminData.totals.users}</p>
            </div>
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
              <p className="text-slate-600 text-sm font-medium mb-1">Commandes 24h</p>
              <p className="text-3xl font-bold text-slate-900">{adminData.totals.recent_commands_24h}</p>
            </div>
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
              <p className="text-slate-600 text-sm font-medium mb-1">Cmds 7 jours</p>
              <p className="text-3xl font-bold text-slate-900">{adminData.totals.commands_last_7_days}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
              <h3 className="text-xl font-bold text-slate-900 mb-4">Top utilisateurs (7 jours)</h3>
              <div className="space-y-3">
                {adminData.top_users_7d.length === 0 && (
                  <p className="text-slate-500 text-sm">Aucune activité récente.</p>
                )}
                {adminData.top_users_7d.map((u) => (
                  <div key={u.user__id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50/50">
                    <span className="text-slate-900 font-medium">{u.user__username}</span>
                    <span className="text-slate-600 text-sm">{u.command_count} commandes</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
              <h3 className="text-xl font-bold text-slate-900 mb-4">Activité des utilisateurs (24h)</h3>
              <div className="space-y-3">
                {adminData.recent_activity_24h.length === 0 && (
                  <p className="text-slate-500 text-sm">Aucune activité dans les 24 dernières heures.</p>
                )}
                {adminData.recent_activity_24h.map((u) => (
                  <div key={u.user__id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50/50">
                    <span className="text-slate-900 font-medium">{u.user__username}</span>
                    <span className="text-slate-600 text-sm">{u.commands} commandes</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">Actions rapides</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <Link
                key={index}
                to={action.path}
                className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-xl ${action.gradient} shadow-lg`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600 transition-colors duration-200" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">{action.title}</h3>
                <p className="text-slate-600 text-sm">{action.description}</p>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Recent Activity & System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Activity */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-slate-900">Activité récente</h3>
            <Link to="/history" className="text-purple-600 hover:text-purple-700 text-sm font-medium">
              Voir tout
            </Link>
          </div>
          <div className="space-y-4">
            {[
              { action: 'Configuration sauvegardée', time: 'Il y a 5 min', status: 'success' },
              { action: 'Pare-feu mis à jour', time: 'Il y a 15 min', status: 'success' },
              { action: 'Daily check terminé', time: 'Il y a 1 heure', status: 'success' },
              { action: 'Nouveau pare-feu ajouté', time: 'Il y a 2 heures', status: 'info' }
            ].map((item, index) => (
              <div key={index} className="flex items-center space-x-3 p-3 rounded-xl bg-slate-50/50">
                <div className={`w-2 h-2 rounded-full ${
                  item.status === 'success' ? 'bg-green-500' : 'bg-blue-500'
                }`}></div>
                <div className="flex-1">
                  <p className="text-slate-900 font-medium">{item.action}</p>
                  <p className="text-slate-500 text-sm">{item.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
          <h3 className="text-xl font-bold text-slate-900 mb-6">Statut du système</h3>
          <div className="space-y-4">
            {[
              { service: 'API Backend', status: 'online', color: 'green' },
              { service: 'Base de données', status: 'online', color: 'green' },
              { service: 'Services SSH', status: 'online', color: 'green' },
              { service: 'Monitoring', status: 'online', color: 'green' }
            ].map((service, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-slate-50/50">
                <span className="text-slate-900 font-medium">{service.service}</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full bg-${service.color}-500`}></div>
                  <span className={`text-${service.color}-600 text-sm font-medium capitalize`}>
                    {service.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

import React, { useEffect, useState } from 'react';
import { Clock, Shield, Server, Building, User, ChevronDown, ChevronUp, Settings, Terminal, Lock, Info } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext.tsx';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { getAuthToken } from '../services/authService';
import api from '../utils/axiosConfig.ts';

interface Action {
    id: string;
    action: string;
    action_description: string;
    entity_name: string;
    user: string;
    timestamp: string;
    details: any;
}

interface Service {
    actions: Action[];
    total_actions: number;
    last_updated: string;
}

interface HistoryData {
    services: {
        [key: string]: Service;
    };
    total_actions: number;
    last_updated: string;
}

const History = () => {
    const [history, setHistory] = useState<HistoryData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedAction, setExpandedAction] = useState<string | null>(null);

    const getServiceIcon = (serviceType: string) => {
        switch (serviceType.toLowerCase()) {
            case 'firewall':
                return <Shield className="h-5 w-5 text-purple-600" />;
            case 'data_center':
                return <Building className="h-5 w-5 text-blue-600" />;
            case 'firewall_type':
                return <Server className="h-5 w-5 text-green-600" />;
            case 'command':
                return <Terminal className="h-5 w-5 text-yellow-600" />;
            case 'config':
                return <Settings className="h-5 w-5 text-indigo-600" />;
            case 'auth':
                return <Lock className="h-5 w-5 text-red-600" />;
            default:
                return <Settings className="h-5 w-5 text-gray-600" />;
        }
    };

    const getServiceName = (serviceType: string) => {
        const serviceNames: { [key: string]: string } = {
            'firewall': 'Pare-feu',
            'data_center': 'Centre de données',
            'firewall_type': 'Type de pare-feu',
            'command': 'Commandes',
            'config': 'Configuration',
            'auth': 'Authentification'
        };
        return serviceNames[serviceType] || serviceType;
    };

    const formatDate = (dateString: string) => {
        try {
            return format(new Date(dateString), 'PPpp', { locale: fr });
        } catch (err) {
            return dateString;
        }
    };

    const getActionColor = (action: string) => {
        if (action.includes('create')) return 'bg-green-100 text-green-800';
        if (action.includes('update')) return 'bg-blue-100 text-blue-800';
        if (action.includes('delete')) return 'bg-red-100 text-red-800';
        if (action.includes('status')) return 'bg-yellow-100 text-yellow-800';
        if (action.includes('restore')) return 'bg-purple-100 text-purple-800';
        return 'bg-gray-100 text-gray-800';
    };

    const formatActionText = (action: string) => {
        const actionMap: { [key: string]: string } = {
            'firewall_create': 'Création de pare-feu',
            'firewall_update': 'Modification de pare-feu',
            'firewall_delete': 'Suppression de pare-feu',
            'firewall_type_create': 'Création de type de pare-feu',
            'firewall_type_update': 'Modification de type de pare-feu',
            'firewall_type_delete': 'Suppression de type de pare-feu',
            'create': 'Création',
            'update': 'Modification',
            'delete': 'Suppression',
            'add': 'Ajout',
            'remove': 'Suppression',
            'edit': 'Modification',
            'execute': 'Exécution',
            'save': 'Sauvegarde',
            'restore': 'Restauration',
            'download': 'Téléchargement',
            'ping': 'Test de connectivité',
            'login': 'Connexion',
            'logout': 'Déconnexion',
            'password_change': 'Changement de mot de passe',
            'ssh_key_update': 'Mise à jour de clé SSH'
        };
        return actionMap[action.toLowerCase()] || action;
    };

    const formatEntityName = (name: string, action: string, details: any) => {
        const entityName = details?.name || name || 'Unknown';
        return entityName === 'Unknown' ? action : entityName;
    };

    const formatDetails = (details: any) => {
        if (typeof details === 'string') {
            return details;
        }
        if (typeof details === 'object') {
            return JSON.stringify(details, null, 2);
        }
        return String(details);
    };

    const getAllActions = () => {
        if (!history || !history.services) return [];
        
        const allActions: (Action & { serviceType: string })[] = [];
        Object.entries(history.services).forEach(([serviceType, service]) => {
            service.actions.forEach(action => {
                allActions.push({ ...action, serviceType });
            });
        });
        
        return allActions.sort((a, b) => 
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
    };

    useEffect(() => {
        let isMounted = true;
        const fetchHistory = async () => {
            try {
                setLoading(true);
                const authToken = getAuthToken();
                if (!authToken) {
                    throw new Error('No authentication token found');
                }

                const response = await api.get('/history/');

                if (isMounted) {
                    setHistory(response.data);
                    setLoading(false);
                }
            } catch (err) {
                if (isMounted) {
                    console.error('Error fetching history:', err);
                    setError('Failed to load history data');
                    setLoading(false);
                }
            }
        };

        fetchHistory();
        return () => {
            isMounted = false;
        };
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="relative">
                        <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600"></div>
                        <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 border-2 border-purple-400 opacity-20"></div>
                    </div>
                    <p className="mt-4 text-slate-600 text-lg font-medium">Loading...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
                <div className="max-w-6xl mx-auto">
                    <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
                            Mon Historique
                        </h1>
                        <p className="text-slate-600 text-lg">Consultez l'historique de vos actions</p>
                    </div>
                    <div className="bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-2xl p-6 shadow-lg">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                            <span className="font-medium">{error}</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const allActions = getAllActions();

    if (allActions.length === 0) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-12 text-center">
                    <div className="relative">
                        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-r from-slate-100 to-purple-100 mb-6">
                            <Clock className="h-10 w-10 text-slate-400" />
                        </div>
                        <div className="absolute inset-0 animate-ping rounded-full w-20 h-20 bg-slate-400 opacity-20"></div>
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-3">Aucune action récente</h3>
                    <p className="text-slate-600 text-lg max-w-sm mx-auto">
                        Votre historique d'actions apparaîtra ici.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
            <div className="max-w-6xl mx-auto">
                {/* Header avec glassmorphism */}
                <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
                        Mon Historique
                    </h1>
                    <p className="text-slate-600 text-lg">Historique de vos actions sur les services</p>
                </div>

            {/* Liste des actions avec glassmorphism */}
            <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl overflow-hidden">
                {allActions.map((action) => (
                    <div key={action.id} className="border-b border-slate-200/50 last:border-b-0">
                        <div 
                            className="p-6 hover:bg-slate-50/50 cursor-pointer transition-all duration-200"
                            onClick={() => setExpandedAction(expandedAction === action.id ? null : action.id)}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-4">
                                    <div className="bg-gradient-to-r from-slate-50 to-purple-50 p-2 rounded-lg">
                                        {getServiceIcon(action.serviceType)}
                                    </div>
                                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getActionColor(action.action)} border`}>
                                        {formatActionText(action.action)}
                                    </span>
                                    <span className="text-lg font-semibold text-slate-900">
                                        {formatEntityName(action.entity_name, action.action, action.details)}
                                    </span>
                                    <span className="text-sm text-slate-600 bg-slate-100 px-3 py-1 rounded-lg">
                                        {getServiceName(action.serviceType)}
                                    </span>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <div className="flex items-center text-sm text-slate-600 bg-slate-100 px-3 py-2 rounded-lg">
                                        <Clock className="h-4 w-4 mr-2" />
                                        {formatDate(action.timestamp)}
                                    </div>
                                    {expandedAction === action.id ? (
                                        <ChevronUp className="h-6 w-6 text-slate-500" />
                                    ) : (
                                        <ChevronDown className="h-6 w-6 text-slate-500" />
                                    )}
                                </div>
                            </div>
                        </div>
                        
                        {expandedAction === action.id && (
                            <div className="px-6 pb-6 bg-gradient-to-r from-slate-50/50 to-purple-50/50">
                                <div className="flex items-start space-x-3">
                                    <Info className="h-6 w-6 text-purple-600 mt-1" />
                                    <div className="flex-1">
                                        <h4 className="text-lg font-semibold text-slate-900 mb-3">Détails de l'action</h4>
                                        <pre className="text-sm text-slate-700 whitespace-pre-wrap bg-white/80 backdrop-blur-sm p-4 rounded-xl border border-slate-200 shadow-sm">
                                            {formatDetails(action.details)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    </div>
    );
};

export default History; 
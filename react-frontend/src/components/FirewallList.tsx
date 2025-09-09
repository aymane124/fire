import React, { useEffect, useState } from 'react';
import { firewallService, Firewall } from '../services/firewallService';
import { Shield, Server, Building, Trash2, Edit, RefreshCw, Search, Terminal } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ApiResponse {
    results?: Firewall[];
}

const FirewallList = () => {
    const [firewalls, setFirewalls] = useState<Firewall[]>([]);
    const [filteredFirewalls, setFilteredFirewalls] = useState<Firewall[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchAllFirewalls = async () => {
            try {
                setLoading(true);
                let allFirewalls: Firewall[] = [];
                let page = 1;
                let hasNext = true;
                while (hasNext) {
                    const data = await firewallService.getFirewalls(page);
                    const results: Firewall[] = data.results || [];
                    allFirewalls = allFirewalls.concat(results);
                    if (data.next) {
                        page += 1;
                    } else {
                        hasNext = false;
                    }
                }
                setFirewalls(allFirewalls);
                setFilteredFirewalls(allFirewalls);
                setError(null);
            } catch (err: any) {
                setError(`Erreur lors de la récupération des pare-feux: ${err.message || 'Erreur inconnue'}`);
            } finally {
                setLoading(false);
            }
        };

        fetchAllFirewalls();
    }, [refreshKey]);

    useEffect(() => {
        if (!searchQuery.trim()) {
            setFilteredFirewalls(firewalls);
            return;
        }

        const query = searchQuery.toLowerCase().trim();
        const filtered = firewalls.filter(firewall => 
            firewall.name.toLowerCase().includes(query) ||
            firewall.ip_address.toLowerCase().includes(query)
        );
        setFilteredFirewalls(filtered);
    }, [searchQuery, firewalls]);

    const handleRefresh = () => {
        setRefreshKey(prev => prev + 1);
    };

    const handleDelete = async (id: string) => {
        if (window.confirm('Êtes-vous sûr de vouloir supprimer ce pare-feu ?')) {
            try {
                await firewallService.deleteFirewall(id);
                setFirewalls(firewalls.filter(fw => fw.id !== id));
            } catch (err) {
                setError('Erreur lors de la suppression du pare-feu');
            }
        }
    };

    const handleOpenTerminal = (firewallId: string) => {
        // Ouvrir le terminal dans une nouvelle page
        navigate(`/terminal/${firewallId}`);
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="relative">
                    <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600"></div>
                    <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 border-2 border-purple-400 opacity-20"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
            {/* Header avec glassmorphism */}
            <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
                            Liste des Pare-feux
                        </h1>
                        <p className="text-slate-600 text-lg">Gérez vos pare-feux et leurs configurations</p>
                    </div>
                    <button
                        onClick={handleRefresh}
                        className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 flex items-center gap-3 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                    >
                        <RefreshCw className="w-5 h-5" />
                        Rafraîchir
                    </button>
                </div>
            </div>

            {/* Barre de recherche avec glassmorphism */}
            <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-6 mb-8">
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="h-6 w-6 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-12 pr-4 py-4 border border-slate-200 rounded-xl leading-5 bg-white/50 backdrop-blur-sm placeholder-slate-500 focus:outline-none focus:placeholder-slate-400 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-lg transition-all duration-200"
                        placeholder="Rechercher par nom ou adresse IP..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                {searchQuery && (
                    <p className="mt-3 text-sm font-medium text-slate-600">
                        {filteredFirewalls.length} pare-feu{filteredFirewalls.length !== 1 ? 'x' : ''} trouvé{filteredFirewalls.length !== 1 ? 's' : ''}
                    </p>
                )}
            </div>

            {error && (
                <div className="mb-8 p-6 bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-2xl shadow-lg">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                        <span className="font-medium">{error}</span>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {filteredFirewalls.map((firewall) => (
                    <div key={firewall.id} className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105">
                        <div className="p-8">
                            <div className="flex items-start justify-between mb-6">
                                <div className="flex items-center">
                                    <div className="relative">
                                        <Shield className="h-10 w-10 text-purple-600" />
                                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>
                                    </div>
                                    <div className="ml-4">
                                        <h3 className="text-2xl font-bold text-slate-900 mb-1">{firewall.name}</h3>
                                        <p className="text-slate-600 font-medium">{firewall.ip_address}</p>
                                    </div>
                                </div>
                                <div className="flex space-x-3">
                                    <button
                                        onClick={() => handleOpenTerminal(firewall.id)}
                                        className="p-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-110"
                                        title="Ouvrir le terminal"
                                    >
                                        <Terminal className="h-5 w-5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(firewall.id)}
                                        className="p-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-110"
                                        title="Supprimer le pare-feu"
                                    >
                                        <Trash2 className="h-5 w-5" />
                                    </button>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center p-3 bg-gradient-to-r from-slate-50 to-purple-50 rounded-xl border border-white/50">
                                    <Building className="h-6 w-6 text-purple-600 mr-3" />
                                    <div>
                                        <p className="text-sm font-medium text-slate-700">Data Center</p>
                                        <p className="text-slate-900 font-semibold">{firewall.data_center_info?.name || 'N/A'}</p>
                                    </div>
                                </div>
                                <div className="flex items-center p-3 bg-gradient-to-r from-slate-50 to-blue-50 rounded-xl border border-white/50">
                                    <Server className="h-6 w-6 text-blue-600 mr-3" />
                                    <div>
                                        <p className="text-sm font-medium text-slate-700">Type</p>
                                        <p className="text-slate-900 font-semibold">{typeof firewall.firewall_type === 'object' && firewall.firewall_type ? firewall.firewall_type.name : 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {filteredFirewalls.length === 0 && !loading && (
                <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-12 text-center">
                    <div className="relative">
                        <Shield className="h-20 w-20 text-slate-400 mx-auto mb-6" />
                        <div className="absolute inset-0 animate-ping rounded-full h-20 w-20 bg-slate-400 opacity-20"></div>
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-3">
                        {searchQuery ? 'Aucun résultat trouvé' : 'Aucun pare-feu trouvé'}
                    </h3>
                    <p className="text-slate-600 text-lg">
                        {searchQuery 
                            ? 'Essayez de modifier votre recherche'
                            : 'Commencez par ajouter un nouveau pare-feu.'}
                    </p>
                </div>
            )}
        </div>
    );
};

export default FirewallList; 
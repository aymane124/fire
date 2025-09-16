import React, { useState, useEffect } from 'react';
import { Save, Play, Building, Shield, Server, FileText, Clock } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config.ts';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

// Fonction pour obtenir le token JWT
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Create axios instance with auth header
const api = axios.create({
  baseURL: API_URL
});

// Add a request interceptor to add the token before each request
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Rediriger vers la page de connexion si le token est invalide
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

interface FirewallType {
  id: string;
  name: string;
  description: string;
  data_center: {
    id: string;
    name: string;
  };
}

interface DataCenter {
  id: string;
  name: string;
  description: string;
  location: string;
  firewall_types: FirewallType[];
}

interface Firewall {
  id: string;
  name: string;
  ip_address: string;
  data_center: {
    id: string;
    name: string;
  };
  firewall_type: {
    id: string;
    name: string;
  };
  created_at: string;
}

interface HierarchyFirewall {
  id: string;
  name: string;
  ip_address: string;
}

interface HierarchyData {
  id: string;
  name: string;
  description: string;
  firewall_types: {
    id: string;
    name: string;
    description: string;
    firewalls: HierarchyFirewall[];
  }[];
}

interface DailyCheck {
  id: string;
  firewall: Firewall;
  check_date: string;
  status: 'SUCCESS' | 'FAILED' | 'PENDING';
  notes: string | null;
  excel_report: string | null;
  commands: {
    id: string;
    command: string;
    status: string;
    actual_output: string;
    execution_time: string;
  }[];
  historique_dailycheck: {
    entries: Array<{
      timestamp: string;
      action: string;
      status: string;
      details: string | null;
      user: string | null;
      ip_address: string | null;
    }>;
  };
}

function DailyCheck() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedFirewalls, setSelectedFirewalls] = useState<string[]>([]);
  const [dailyChecks, setDailyChecks] = useState<DailyCheck[]>([]);
  const [commands, setCommands] = useState<string>('config global\nget system status\ndiagnose autoupdate versions\nget hardware memory');

  // States for hierarchy data
  const [hierarchy, setHierarchy] = useState<HierarchyData[]>([]);
  const [selectedDataCenter, setSelectedDataCenter] = useState<string>('');
  const [selectedFirewallType, setSelectedFirewallType] = useState<string>('');

  // Fetch hierarchy data
  useEffect(() => {
    const fetchHierarchy = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await api.get('/datacenters/hierarchy/');
        setHierarchy(response.data);
      } catch (error) {
        console.error('Error fetching hierarchy:', error);
        setError('Failed to fetch hierarchy data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchHierarchy();
  }, []);

  // Fetch daily checks
  useEffect(() => {
    const fetchDailyChecks = async () => {
      try {
        const response = await api.get('/daily-check/daily-checks/');
        // La réponse de l'API contient les résultats dans response.data.results
        setDailyChecks(response.data.results || []);
      } catch (error) {
        console.error('Error fetching daily checks:', error);
        setDailyChecks([]); // En cas d'erreur, initialiser avec un tableau vide
      }
    };

    fetchDailyChecks();
  }, []);

  // Get available firewall types based on selected datacenter
  const getAvailableFirewallTypes = () => {
    if (!selectedDataCenter) return [];
    const dc = hierarchy.find(dc => dc.id === selectedDataCenter);
    return dc ? dc.firewall_types : [];
  };

  // Get available firewalls based on selected firewall type
  const getAvailableFirewalls = () => {
    if (!selectedFirewallType) return [];
    const dc = hierarchy.find(dc => dc.id === selectedDataCenter);
    if (!dc) return [];
    const ft = dc.firewall_types.find(ft => ft.id === selectedFirewallType);
    return ft ? ft.firewalls : [];
  };

  // Handle selection changes
  const handleDataCenterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const dcId = e.target.value;
    setSelectedDataCenter(dcId);
    setSelectedFirewallType('');
    setSelectedFirewalls([]);
  };

  const handleFirewallTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ftId = e.target.value;
    setSelectedFirewallType(ftId);
    setSelectedFirewalls([]);
  };

  // Handle select all firewalls
  const handleSelectAllFirewalls = () => {
    const availableFirewalls = getAvailableFirewalls();
    if (selectedFirewalls.length === availableFirewalls.length) {
      setSelectedFirewalls([]);
    } else {
      setSelectedFirewalls(availableFirewalls.map(fw => fw.id));
    }
  };

  // Handle individual firewall selection
  const handleFirewallSelection = (firewallId: string) => {
    setSelectedFirewalls(prev => {
      if (prev.includes(firewallId)) {
        return prev.filter(id => id !== firewallId);
      } else {
        return [...prev, firewallId];
      }
    });
  };

  const handleRunDailyCheck = async () => {
    if (!selectedFirewalls.length) {
      setError('Please select at least one firewall');
      return;
    }

    if (!commands.trim()) {
      setError('Please enter at least one command');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Run commands for all selected firewalls at once
      const commandsList = commands.split('\n').filter(cmd => cmd.trim());
      const response = await api.post('/daily-check/daily-checks/run_multiple_checks/', {
        firewalls: selectedFirewalls,
        commands: commandsList
      });

      if (response.data.status === 'success') {
        setSuccess('Daily checks started. You can leave this page, the checks will continue in the background.');
        
        // Start polling for task status
        const taskId = response.data.task_id;
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await api.get(`/daily-check/daily-checks/check_task_status/?task_id=${taskId}`);
            const taskStatus = statusResponse.data;
            
            // Update progress message
            setSuccess(`${taskStatus.message} (${taskStatus.progress}%)`);
            
            if (taskStatus.status === 'completed') {
              clearInterval(pollInterval);
              setSuccess('All daily checks completed successfully');
              
              // Refresh daily checks list
              const checksResponse = await api.get('/daily-check/daily-checks/');
              setDailyChecks(checksResponse.data.results || []);
              
              // Download all reports
              if (taskStatus.results && taskStatus.results.length > 0) {
                const uniqueReportPaths = [...new Set(
                  taskStatus.results
                    .filter((result: any) => result.success && result.report_path)
                    .map((result: any) => result.report_path)
                )];
                
                for (const reportPath of uniqueReportPaths) {
                  try {
                    const reportResponse = await api.get(
                      `/daily-check/daily-checks/download_multiple_reports/`,
                      { 
                        responseType: 'blob',
                        params: {
                          report_path: reportPath
                        }
                      }
                    );
                    
                    const blob = new Blob([reportResponse.data], { 
                      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
                    });
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', `daily_check_${new Date().toISOString()}.xlsx`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                  } catch (error) {
                    console.error('Error downloading report:', error);
                    toast.error(`Failed to download report from ${reportPath}`);
                  }
                }
              }
            } else if (taskStatus.status === 'failed') {
              clearInterval(pollInterval);
              setError(`Daily checks failed: ${taskStatus.message}`);
            }
          } catch (error) {
            console.error('Error checking task status:', error);
            clearInterval(pollInterval);
            setError('Failed to check task status');
          }
        }, 2000); // Poll every 2 seconds
        
        // Clean up interval when component unmounts
        return () => clearInterval(pollInterval);
      } else {
        setError('Failed to start daily checks');
      }
    } catch (error) {
      console.error('Error during daily check:', error);
      setError('Failed to start daily checks');
    } finally {
      setIsLoading(false);
    }
  };

  const downloadReport = async (dailyCheckId: string) => {
    try {
      const response = await api.get(
        `/daily-check/daily-checks/${dailyCheckId}/download_report/`,
        {
          responseType: 'blob'
        }
      );
      
      // Create a blob from the response data
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary link element
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from Content-Disposition header or use a default name
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'daily_check_report.xlsx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      
      // Append link to body, click it, and remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the URL
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading report:', error);
      toast.error('Failed to download report');
    }
  };

      if (isLoading) {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Header avec glassmorphism */}
      <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
          Firewall Daily Check
        </h1>
        <p className="text-slate-600 text-lg">Exécutez des vérifications quotidiennes sur vos pare-feux</p>
      </div>

      {/* Sélection des pare-feux avec glassmorphism */}
      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
          Sélection des Pare-feux
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Data Center Selection */}
          <div className="bg-gradient-to-r from-slate-50 to-purple-50 p-6 rounded-xl border border-white/50">
            <div className="flex items-center mb-4">
              <Building className="h-8 w-8 text-purple-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-slate-700">Data Center</p>
              </div>
            </div>
            <select
              value={selectedDataCenter}
              onChange={handleDataCenterChange}
              className="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
            >
              <option value="">All data centers</option>
              {hierarchy.map((dc) => (
                <option key={dc.id} value={dc.id}>
                  {dc.name}
                </option>
              ))}
            </select>
          </div>

          {/* Firewall Type Selection */}
          <div className="bg-gradient-to-r from-slate-50 to-blue-50 p-6 rounded-xl border border-white/50">
            <div className="flex items-center mb-4">
              <Shield className="h-8 w-8 text-blue-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-slate-700">Firewall Type</p>
              </div>
            </div>
            <select
              value={selectedFirewallType}
              onChange={handleFirewallTypeChange}
              disabled={!selectedDataCenter}
              className={`w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white/50 backdrop-blur-sm ${
                !selectedDataCenter ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <option value="">Select a firewall type</option>
              {getAvailableFirewallTypes().map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>

          {/* Firewall Selection */}
          <div className="bg-gradient-to-r from-slate-50 to-indigo-50 p-6 rounded-xl border border-white/50">
            <div className="flex items-center mb-4">
              <Server className="h-8 w-8 text-indigo-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-slate-700">Firewalls</p>
              </div>
            </div>
            <div className="space-y-3">
              <button
                onClick={handleSelectAllFirewalls}
                disabled={!selectedFirewallType}
                className={`w-full px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                  selectedFirewalls.length === getAvailableFirewalls().length
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg'
                    : 'bg-gradient-to-r from-purple-100 to-indigo-100 text-purple-700 hover:from-purple-200 hover:to-indigo-200'
                } ${!selectedFirewallType ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {selectedFirewalls.length === getAvailableFirewalls().length
                  ? 'Deselect All'
                  : 'Select All'}
              </button>
              <div className="max-h-48 overflow-y-auto space-y-2">
                {getAvailableFirewalls().map((fw) => (
                  <div
                    key={fw.id}
                    className={`flex items-center p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                      selectedFirewalls.includes(fw.id)
                        ? 'bg-gradient-to-r from-purple-100 to-indigo-100 border border-purple-200'
                        : 'hover:bg-gradient-to-r hover:from-slate-100 hover:to-purple-50 border border-transparent'
                    }`}
                    onClick={() => handleFirewallSelection(fw.id)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedFirewalls.includes(fw.id)}
                      onChange={() => handleFirewallSelection(fw.id)}
                      className="mr-3 w-4 h-4 text-purple-600 focus:ring-purple-500 border-slate-300 rounded"
                    />
                    <span className="text-sm font-medium text-slate-700">
                      {fw.name} - {fw.ip_address}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Commands Input */}
        <div className="mt-8">
          <div className="bg-gradient-to-r from-slate-50 to-emerald-50 p-6 rounded-xl border border-white/50">
            <div className="flex items-center mb-4">
              <FileText className="h-8 w-8 text-emerald-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-slate-700">Commands (one per line)</p>
              </div>
            </div>
            <textarea
              value={commands}
              onChange={(e) => setCommands(e.target.value)}
              className="w-full p-4 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-200 bg-white/50 backdrop-blur-sm text-sm font-mono"
              rows={6}
              placeholder="Enter commands (one per line)"
            />
          </div>
        </div>
      </div>

      {/* Bouton d'exécution avec glassmorphism */}
      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        {error && (
          <div className="p-4 bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-xl shadow-lg mb-6">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
              <span className="font-medium">{error}</span>
            </div>
          </div>
        )}

        {success && (
          <div className="p-4 bg-green-50/80 backdrop-blur-sm border border-green-200 text-green-700 rounded-xl shadow-lg mb-6">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="font-medium">{success}</span>
            </div>
          </div>
        )}

        <div className="pt-4">
          <button
            onClick={handleRunDailyCheck}
            disabled={isLoading || !selectedFirewalls.length}
            className="w-full flex items-center justify-center px-6 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 font-semibold text-lg"
          >
            <Play className="h-6 w-6 mr-3" />
            {isLoading ? 'Running...' : 'Run Daily Check'}
          </button>
        </div>
      </div>

      {/* Historique des vérifications avec glassmorphism */}
      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6 flex items-center gap-3">
          <Clock className="h-8 w-8 text-purple-600" />
          Historique des Vérifications
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-gradient-to-r from-slate-50 to-purple-50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700 uppercase tracking-wider">
                  Firewall
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white/50 backdrop-blur-sm divide-y divide-slate-200">
              {dailyChecks.map((check) => {
                // Get the last history entry to find the user
                const lastHistoryEntry = check.historique_dailycheck?.entries?.[check.historique_dailycheck.entries.length - 1];
                const user = lastHistoryEntry?.user || 'Unknown';
                
                return (
                  <tr key={check.id} className="hover:bg-slate-50/50 transition-colors duration-200">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Shield className="h-5 w-5 text-purple-600 mr-3" />
                        <div>
                          <div className="text-sm font-semibold text-slate-900">
                            {check.firewall.name}
                          </div>
                          <div className="text-sm text-slate-600">
                            {check.firewall.ip_address}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-900">
                        {user}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-900">
                        {new Date(check.check_date).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        check.status === 'SUCCESS' ? 'bg-gradient-to-r from-green-100 to-emerald-100 text-green-800 border border-green-200' :
                        check.status === 'FAILED' ? 'bg-gradient-to-r from-red-100 to-pink-100 text-red-800 border border-red-200' :
                        'bg-gradient-to-r from-yellow-100 to-orange-100 text-yellow-800 border border-yellow-200'
                      }`}>
                        {check.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {check.excel_report && (
                        <button
                          onClick={() => downloadReport(check.id)}
                          className="text-purple-600 hover:text-purple-900 flex items-center p-2 rounded-lg hover:bg-purple-50 transition-all duration-200"
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Download Report
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default DailyCheck; 

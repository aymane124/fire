import React, { useState, useEffect } from 'react';
import { Save, Play, Building, Shield, Server } from 'lucide-react';
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

function FirewallConfig() {
  const navigate = useNavigate();
  const [ipAddress, setIpAddress] = useState('');
  const [command, setCommand] = useState('show');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedFirewalls, setSelectedFirewalls] = useState<string[]>([]);
  const [isBulkOperation, setIsBulkOperation] = useState(false);

  // States for hierarchy data
  const [hierarchy, setHierarchy] = useState<HierarchyData[]>([]);
  const [selectedDataCenter, setSelectedDataCenter] = useState<string>('');
  const [selectedFirewallType, setSelectedFirewallType] = useState<string>('');
  const [selectedFirewall, setSelectedFirewall] = useState<Firewall | null>(null);

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
    setSelectedFirewallType(''); // Reset firewall type selection
    setSelectedFirewall(null); // Reset firewall selection
    setSelectedFirewalls([]); // Reset selected firewalls
  };

  const handleFirewallTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ftId = e.target.value;
    setSelectedFirewallType(ftId);
    setSelectedFirewall(null); // Reset firewall selection
    setSelectedFirewalls([]); // Reset selected firewalls
  };

  const handleFirewallChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const fwId = e.target.value;
    const firewalls = getAvailableFirewalls();
    const firewall = firewalls.find(fw => fw.id === fwId);
    if (firewall) {
      // Convert HierarchyFirewall to Firewall
      const selectedFirewall: Firewall = {
        id: firewall.id,
        name: firewall.name,
        ip_address: firewall.ip_address,
        data_center: {
          id: selectedDataCenter,
          name: hierarchy.find(dc => dc.id === selectedDataCenter)?.name || ''
        },
        firewall_type: {
          id: selectedFirewallType,
          name: getAvailableFirewallTypes().find(ft => ft.id === selectedFirewallType)?.name || ''
        },
        created_at: new Date().toISOString()
      };
      setSelectedFirewall(selectedFirewall);
      setIpAddress(firewall.ip_address);
    }
  };

  // Handle select all firewalls
  const handleSelectAllFirewalls = () => {
    const availableFirewalls = getAvailableFirewalls();
    if (selectedFirewalls.length === availableFirewalls.length) {
      // If all are selected, deselect all
      setSelectedFirewalls([]);
    } else {
      // Select all available firewalls
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

  const handleBulkSave = async () => {
    if (!selectedFirewalls.length && !selectedFirewallType) {
      setError('Please select firewalls or a firewall type');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const firewallsToProcess = selectedFirewalls.length > 0
        ? getAvailableFirewalls().filter(fw => selectedFirewalls.includes(fw.id))
        : getAvailableFirewalls();

      // Start bulk configuration save
      const response = await api.post('/command/commands/save_bulk_config/', {
        firewall_ids: firewallsToProcess.map(fw => fw.id),
        command: command
      });

      if (response.data.status === 'success') {
        setSuccess('Configuration save started. You can leave this page, the saves will continue in the background.');
        
        // Start polling for task status
        const taskId = response.data.task_id;
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await api.get(`/command/commands/check_task_status/?task_id=${taskId}`);
            const taskStatus = statusResponse.data;
            
            // Update progress message
            setSuccess(`${taskStatus.message} (${taskStatus.progress}%)`);
            
            if (taskStatus.status === 'completed') {
              clearInterval(pollInterval);
              setSuccess('All configurations saved successfully');
              
              // Download all configurations
              if (taskStatus.results && taskStatus.results.length > 0) {
                const successfulResults = taskStatus.results.filter((result: any) => result.status === 'success' && result.filepath);
                const failedResults = taskStatus.results.filter((result: any) => result.status === 'failed');
                
                // Download successful configurations
                for (const result of successfulResults) {
                  try {
                    const downloadResponse = await api.get(
                      '/command/commands/download_config_file/',
                      {
                        responseType: 'blob',
                        params: {
                          filepath: result.filepath
                        }
                      }
                    );
                    
                    const blob = new Blob([downloadResponse.data], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', `${result.firewall_name}_config.txt`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                  } catch (error) {
                    console.error(`Error downloading config for ${result.firewall_name}:`, error);
                    toast.error(`Failed to download configuration for ${result.firewall_name}`);
                  }
                }
                
                if (successfulResults.length > 0) {
                  setSuccess(`${successfulResults.length} configurations saved and downloaded successfully`);
                }
                if (failedResults.length > 0) {
                  setError(`Failed to save ${failedResults.length} configurations: ${failedResults.map((f: any) => f.firewall_name).join(', ')}`);
                }
              }
            } else if (taskStatus.status === 'failed') {
              clearInterval(pollInterval);
              setError(`Configuration save failed: ${taskStatus.message}`);
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
        setError('Failed to start configuration save');
      }
    } catch (error) {
      console.error('Error during bulk save:', error);
      setError('Failed to save configurations');
    } finally {
      setIsLoading(false);
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

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
        <div className="bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 px-6 py-4 rounded-2xl shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            <strong className="font-bold">Error!</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Header avec glassmorphism */}
      <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
          Firewall Configuration Backup
        </h1>
        <p className="text-slate-600 text-lg">Manage firewall configurations backup</p>
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
      </div>

      {/* Configuration avec glassmorphism */}
      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
          Configuration
        </h2>
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-3">
              IP Address
            </label>
            <input
              type="text"
              value={ipAddress}
              onChange={(e) => setIpAddress(e.target.value)}
              placeholder="e.g., 192.168.1.1"
              className="w-full p-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm text-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-3">
              Command
            </label>
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              className="w-full p-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm text-lg"
            />
          </div>

          {error && (
            <div className="p-4 bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-xl shadow-lg">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}

          {success && (
            <div className="p-4 bg-green-50/80 backdrop-blur-sm border border-green-200 text-green-700 rounded-xl shadow-lg">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="font-medium">{success}</span>
              </div>
            </div>
          )}

          <div className="pt-4">
            <button
              onClick={handleBulkSave}
              disabled={isLoading || (!selectedFirewalls.length && !selectedFirewallType)}
              className="w-full flex items-center justify-center px-6 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 font-semibold text-lg"
            >
              <Play className="h-6 w-6 mr-3" />
              {isLoading ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FirewallConfig;
import React, { useState, useEffect } from 'react';
import { Upload, Play, Server, Shield, Building, Search, Loader2, Terminal } from 'lucide-react';
import * as XLSX from 'xlsx';
import axios from 'axios';
import { API_URL } from '../config.ts';
import { executeCommand, getCommandHistory, executeTemplate, CommandResponse } from '../services/commandService';
import { templateService, Template as CommandTemplate } from '../services/templateService';
import { navigateTo } from '../utils/navigation';

interface FlowConfig {
  hostname: string;
  ipAddress: string;
  vdom: string;
  setName: string;
  srcaddr: string;
  srcaddrDesc: string;
  srcintf: string;
  dstaddr: string;
  dstaddrDesc: string;
  dstintf: string;
  service: string;
  [key: string]: string;
}

interface FirewallType {
  id: string;
  name: string;
  data_center: string;
  attributes_schema?: {
    type: string;
    required: string[];
    properties: {
      [key: string]: {
        type: string;
        title: string;
        required: boolean;
      };
    };
  };
}

interface DataCenter {
  id: string;
  name: string;
  owner: string;
}

interface Firewall {
  id: string;
  name: string;
  ip_address: string;
  data_center: {
    id: string;
    name: string;
  } | null;
  firewall_type: {
    id: string;
    name: string;
  } | null;
  config: {
    id: string;
    config_data: any;
  };
  created_at: string;
}

interface CommandHistory {
  id: number;
  firewall: number;
  command: string;
  output: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  error_message?: string;
  executed_at: string;
}

interface FlowMatrixResponse {
  ip: string;
  matches: Array<{
    name: string;
    comment: string | null;
    groups: string[];
  }>;
  config_path: string;
  file_list: string[];
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

const debounce = (func: Function, wait: number) => {
  let timeout: ReturnType<typeof setTimeout>;
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

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
      navigateTo('/login');
    }
    return Promise.reject(error);
  }
);

const FlowMatrix: React.FC = () => {
  const [configs, setConfigs] = useState<FlowConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<FlowConfig | null>(null);
  const [formData, setFormData] = useState<FlowConfig>({
    hostname: '',
    ipAddress: '',
    vdom: '',
    setName: '',
    srcaddr: '',
    srcaddrDesc: '',
    srcintf: '',
    dstaddr: '',
    dstaddrDesc: '',
    dstintf: '',
    service: ''
  });
  const [currentFirewallType, setCurrentFirewallType] = useState('');
  const [dataCenter, setDataCenter] = useState('');

  // New states for dropdowns
  const [firewallTypes, setFirewallTypes] = useState<FirewallType[]>([]);
  const [dataCenters, setDataCenters] = useState<DataCenter[]>([]);
  const [firewalls, setFirewalls] = useState<Firewall[]>([]);
  const [selectedFirewall, setSelectedFirewall] = useState<Firewall | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDataCenter, setSelectedDataCenter] = useState<string>('');
  const [selectedFirewallType, setSelectedFirewallType] = useState<string>('');
  const [availableFirewallTypes, setAvailableFirewallTypes] = useState<FirewallType[]>([]);
  const [availableFirewalls, setAvailableFirewalls] = useState<Firewall[]>([]);

  // Add new state for dynamic form fields
  const [formFields, setFormFields] = useState<Array<{
    name: string;
    label: string;
    required: boolean;
    type: string;
  }>>([]);

  // Add new state for form values
  const [formValues, setFormValues] = useState<Record<string, string>>({});

  // Add new state for command line interface
  const [command, setCommand] = useState('');
  const [commandOutput, setCommandOutput] = useState('');
  const [commandHistory, setCommandHistory] = useState<CommandResponse[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Add state for selected template
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');

  // Replace static templates with API-loaded templates
  const [templates, setTemplates] = useState<CommandTemplate[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  // Add useEffect to load templates
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setIsLoadingTemplates(true);
        setTemplateError(null);
        const loadedTemplates = await templateService.getTemplates();
        setTemplates(loadedTemplates);
      } catch (error) {
        console.error('Error loading templates:', error);
        setTemplateError('Failed to load templates');
      } finally {
        setIsLoadingTemplates(false);
      }
    };

    loadTemplates();
  }, []);

  const [flowMatrixResult, setFlowMatrixResult] = useState<FlowMatrixResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Add new states for destination search
  const [destinationSearchResult, setDestinationSearchResult] = useState<FlowMatrixResponse | null>(null);
  const [isDestinationSearching, setIsDestinationSearching] = useState(false);
  const [destinationSearchError, setDestinationSearchError] = useState<string | null>(null);

  // Add hierarchy state
  const [hierarchy, setHierarchy] = useState<HierarchyData[]>([]);

  // Add useEffect to fetch hierarchy data
  useEffect(() => {
    const fetchHierarchy = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/datacenters/hierarchy/');
        setHierarchy(response.data);
      } catch (error) {
        console.error('Error fetching hierarchy:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHierarchy();
  }, []);

  // Add helper functions
  const getAvailableFirewallTypes = () => {
    if (!selectedDataCenter) return [];
    const dc = hierarchy.find(dc => dc.id === selectedDataCenter);
    return dc ? dc.firewall_types : [];
  };

  const getAvailableFirewalls = () => {
    if (!selectedFirewallType) return [];
    const dc = hierarchy.find(dc => dc.id === selectedDataCenter);
    if (!dc) return [];
    const ft = dc.firewall_types.find(ft => ft.id === selectedFirewallType);
    return ft ? ft.firewalls : [];
  };

  // Update event handlers
  const handleDataCenterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const dcId = e.target.value;
    setSelectedDataCenter(dcId);
    setSelectedFirewallType(''); // Reset firewall type selection
    setSelectedFirewall(null); // Reset firewall selection
  };

  const handleFirewallTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ftId = e.target.value;
    setSelectedFirewallType(ftId);
    setSelectedFirewall(null); // Reset firewall selection
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
        config: { id: '', config_data: {} },
        created_at: new Date().toISOString()
      };
      setSelectedFirewall(selectedFirewall);
    }
  };

  // Add useEffect to fetch data on mount
  useEffect(() => {
    fetchData();
  }, []);

  // Fetch data from backend
  const fetchData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch all pages of firewalls
      let allFirewalls: any[] = [];
      let nextPage = '/firewalls/firewalls/';
      
      while (nextPage) {
        const response = await api.get(nextPage);
        const data = response.data;
        allFirewalls = [...allFirewalls, ...(data.results || [])];
        nextPage = data.next;
      }

      // Fetch other data
      const [firewallTypesRes, dataCentersRes] = await Promise.all([
        api.get('/firewalls/firewall-types/'),
        api.get('/datacenters/')
      ]);

      console.log('API Responses:', {
        firewallTypes: firewallTypesRes.data,
        dataCenters: dataCentersRes.data,
        firewalls: allFirewalls
      });

      // Format firewall types
      const firewallTypesData = firewallTypesRes.data.results || [];
      const formattedTypes = firewallTypesData.map((type: any) => ({
        id: type.id,
        name: type.name,
        data_center: type.data_center,
        attributes_schema: type.attributes_schema || {}
      }));
      setFirewallTypes(formattedTypes);

      // Format data centers
      const dataCentersData = dataCentersRes.data.results || [];
      const formattedDataCenters = dataCentersData.map((dc: any) => ({
        id: dc.id,
        name: dc.name
      }));
      setDataCenters(formattedDataCenters);

      // Format firewalls
      const formattedFirewalls = allFirewalls.map((fw: any) => ({
        id: fw.id,
        name: fw.name,
        ip_address: fw.ip_address,
        data_center: fw.data_center && fw.data_center.id && fw.data_center.name ? {
          id: fw.data_center.id,
          name: fw.data_center.name
        } : null,
        firewall_type: fw.firewall_type && fw.firewall_type.id && fw.firewall_type.name ? {
          id: fw.firewall_type.id,
          name: fw.firewall_type.name
        } : null,
        config: fw.config || { id: '', config_data: {} },
        created_at: fw.created_at
      })) as Firewall[];
      setFirewalls(formattedFirewalls);
      
      // Set initial selections from localStorage
      const savedDataCenter = localStorage.getItem('dataCenter');
      const savedFirewallType = localStorage.getItem('firewallType');
      const savedFirewallId = localStorage.getItem('selectedFirewallId');
      
      if (savedDataCenter) {
        setSelectedDataCenter(savedDataCenter);
      }
      
      if (savedFirewallType) {
        setSelectedFirewallType(savedFirewallType);
      }
      
      if (savedFirewallId) {
        const firewall = formattedFirewalls.find((f: Firewall) => f.id === savedFirewallId);
        if (firewall) {
          setSelectedFirewall(firewall);
          setFormData(prev => ({ ...prev, ipAddress: firewall.ip_address }));
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Update available firewall types when data center changes
  useEffect(() => {
    if (selectedDataCenter) {
      // Filtrer les types de pare-feu par datacenter
      const filteredTypes = firewallTypes.filter(type => {
        // Vérifier si le type a un datacenter valide
        if (!type.data_center) {
          console.log('No data_center for type:', type);
          return false;
        }
        // Comparer les IDs des datacenters
        const matches = type.data_center === selectedDataCenter;
        console.log('Type matches:', {
          typeId: type.id,
          typeDataCenter: type.data_center,
          selectedDataCenter,
          matches
        });
        return matches;
      });
      
      console.log('Filtered Firewall Types:', {
        selectedDataCenter,
        allTypes: firewallTypes,
        filteredTypes
      });
      
      setAvailableFirewallTypes(filteredTypes);
      
      // Si le type de pare-feu actuel n'est plus disponible, le réinitialiser
      if (selectedFirewallType && !filteredTypes.some(type => type.id === selectedFirewallType)) {
        setSelectedFirewallType('');
        localStorage.removeItem('firewallType');
      }
    } else {
      setAvailableFirewallTypes([]);
      setSelectedFirewallType('');
    }
  }, [selectedDataCenter, firewallTypes]);

  // Update form fields when firewall type changes
  useEffect(() => {
    if (selectedFirewallType) {
      const selectedType = availableFirewallTypes.find(type => type.id === selectedFirewallType);
      console.log('Selected Type:', selectedType);
      
      if (selectedType?.attributes_schema?.properties) {
        const fields = Object.entries(selectedType.attributes_schema.properties).map(([key, value]) => {
          return {
            name: key,
            label: value.title || key,
            required: value.required || false,
            type: value.type || 'string'
          };
        });
        console.log('Generated Form Fields:', fields);
        setFormFields(fields);
      } else {
        console.log('No attributes schema found for type:', selectedType);
        setFormFields([]);
      }
    } else {
      setFormFields([]);
    }
  }, [selectedFirewallType, availableFirewallTypes]);

  // Update available firewalls when firewall type changes
  useEffect(() => {
    if (selectedFirewallType && selectedDataCenter) {
      // Filtrer les pare-feu par type et datacenter
      const filteredFirewalls = firewalls.filter(fw => {
        if (!fw.firewall_type || !fw.data_center) {
          return false;
        }
        
        const matchesType = fw.firewall_type.id === selectedFirewallType;
        const matchesDataCenter = fw.data_center.id === selectedDataCenter;
        
        console.log('Firewall Filter Check:', {
          firewallId: fw.id,
          firewallType: fw.firewall_type.id,
          dataCenter: fw.data_center.id,
          selectedType: selectedFirewallType,
          selectedDC: selectedDataCenter,
          matchesType,
          matchesDataCenter
        });
        
        return matchesType && matchesDataCenter;
      });
      
      console.log('Filtered Firewalls:', {
        selectedFirewallType,
        selectedDataCenter,
        allFirewalls: firewalls,
        filteredFirewalls
      });
      
      setAvailableFirewalls(filteredFirewalls);
      
      // Si le pare-feu actuel n'est plus disponible, le réinitialiser
      if (selectedFirewall && !filteredFirewalls.some(fw => fw.id === selectedFirewall.id)) {
        setSelectedFirewall(null);
        localStorage.removeItem('selectedFirewallId');
      }
    } else {
      setAvailableFirewalls([]);
      setSelectedFirewall(null);
    }
  }, [selectedFirewallType, selectedDataCenter, firewalls]);

  // Load saved selections on component mount
  useEffect(() => {
    const savedDataCenter = localStorage.getItem('dataCenter');
    const savedFirewallType = localStorage.getItem('firewallType');
    const savedFirewallId = localStorage.getItem('selectedFirewallId');
    
    console.log('Loading saved selections:', {
      savedDataCenter,
      savedFirewallType,
      savedFirewallId
    });
    
    if (savedDataCenter) {
      setSelectedDataCenter(savedDataCenter);
    }
    
    if (savedFirewallType) {
      setSelectedFirewallType(savedFirewallType);
    }
    
    if (savedFirewallId) {
      const firewall = firewalls.find(f => f.id === savedFirewallId);
      if (firewall) {
        setSelectedFirewall(firewall);
        setFormData(prev => ({ ...prev, ipAddress: firewall.ip_address }));
      }
    }
  }, [firewalls]);

  const processExcelFile = (data: ArrayBuffer) => {
    try {
      const workbook = XLSX.read(data, { type: 'array' });

      if (!workbook.SheetNames.length) {
        throw new Error('No sheets found in the Excel file');
      }

      const firstSheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[firstSheetName];
      const selectedType = availableFirewallTypes.find(type => type.id === selectedFirewallType);
      
      if (!selectedType) {
        throw new Error('No firewall type selected');
      }

      if (!selectedType.attributes_schema?.properties) {
        throw new Error('No attributes defined for the selected firewall type');
      }

      // Get required fields from attributes
      const requiredFields = Object.entries(selectedType.attributes_schema.properties)
        .filter(([_, value]) => value.required)
        .map(([key]) => key);

      // Convert Excel to JSON with header row
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
        raw: false,
        header: 1
      });
      
      if (!Array.isArray(jsonData) || jsonData.length === 0) {
        throw new Error('No data found in the Excel file');
      }

      // Get headers from first row
      const headers = jsonData[0];

      if (!Array.isArray(headers) || headers.length === 0) {
        throw new Error('No headers found in the Excel file');
      }

      // Remove header row and process data
      const dataRows = jsonData.slice(1);
      
      // Validate and map the data
      const mappedConfigs = dataRows.map((row: any, index: number) => {
        // Map headers to values
        const mappedRow: any = {};
        if (Array.isArray(row)) {
          headers.forEach((header: string, colIndex: number) => {
            const value = row[colIndex];
            mappedRow[header] = value;
          });
        }

        // Check for required fields
        const missingFields = requiredFields.filter(field => !mappedRow[field]);
        if (missingFields.length > 0) {
          throw new Error(`Missing required fields in row ${index + 2}: ${missingFields.join(', ')}`);
        }

        // Map the data according to attributes
        const config: any = {};
        if (selectedType?.attributes_schema?.properties) {
          Object.entries(selectedType.attributes_schema.properties).forEach(([key, value]) => {
            // Try to find the matching header (case insensitive and with common variations)
            const matchingHeader = Object.keys(mappedRow).find(header => {
              const normalizedHeader = header.toLowerCase().replace(/\s+/g, '');
              const normalizedKey = key.toLowerCase().replace(/\s+/g, '');
              
              // Common variations of the same field
              const variations = {
                'ipaddress': ['ip', 'ipaddress', 'ipaddr', 'ip_address', 'ipaddress', 'IP Adresse'],
                'sourceaddress': ['source', 'src', 'sourceaddr', 'source_address', 'sourceaddress', 'source'],
                'destinationinterface': ['dstintf', 'destinationintf', 'destination_interface', 'dstinterface', 'destinationinterface', 'destination'],
                'name': ['name', 'nom', 'hostname', 'device'],
                'vdom': ['vdom', 'virtualdomain'],
                'service': ['service', 'services', 'protocol'],
                'hostname': ['hostname', 'name', 'device'],
                'sourcedescription': ['sourcedescription', 'srcdesc', 'source_desc'],
                'sourceinterface': ['sourceinterface', 'srcintf', 'source_intf'],
                'destinationaddress': ['destinationaddress', 'dstaddr', 'destination_addr'],
                'destinationdescription': ['destinationdescription', 'dstdesc', 'destination_desc']
              };
              
              // Check exact match
              if (normalizedHeader === normalizedKey) return true;
              
              // Check variations
              if (variations[normalizedKey as keyof typeof variations]) {
                return variations[normalizedKey as keyof typeof variations].includes(normalizedHeader);
              }
              
              return false;
            });
            
            if (matchingHeader) {
              config[key] = mappedRow[matchingHeader] || '';
            } else {
              config[key] = '';
            }
          });
        }

        return config;
      });

      // Mettre à jour les configurations et sélectionner la première
      setConfigs(mappedConfigs);
      if (mappedConfigs.length > 0) {
        setSelectedConfig(mappedConfigs[0]);
        setFormValues(mappedConfigs[0]);
      }

      alert(`${mappedConfigs.length} configurations loaded successfully`);
    } catch (error: any) {
      alert(`Error processing Excel file: ${error.message}`);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check if a firewall type is selected
      if (!selectedFirewallType) {
        alert('Please select a firewall type before uploading the file');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const data = e.target?.result as ArrayBuffer;
        processExcelFile(data);
      };
      reader.readAsArrayBuffer(file);
    }
  };

  // Add debounced search functions
  const debouncedSourceSearch = React.useCallback(
    debounce(async (value: string) => {
      if (!selectedFirewall || !value) return;
      
      setIsSearching(true);
      setSearchError(null);
      setFlowMatrixResult(null);

      try {
        const response = await api.post('/analysis/flow-matrix/analyze-ip/', {
          source_ip: value,
          firewall_id: selectedFirewall.id,
          data_center_name: selectedFirewall.data_center?.name || '',
          firewall_type_name: selectedFirewall.firewall_type?.name || ''
        });
        setFlowMatrixResult(response.data);
      } catch (error: any) {
        setSearchError(error.response?.data?.error || 'Failed to search address');
      } finally {
        setIsSearching(false);
      }
    }, 500),
    [selectedFirewall]
  );

  const debouncedDestinationSearch = React.useCallback(
    debounce(async (value: string) => {
      if (!selectedFirewall || !value) return;
      
      setIsDestinationSearching(true);
      setDestinationSearchError(null);
      setDestinationSearchResult(null);

      try {
        const response = await api.post('/analysis/flow-matrix/analyze-ip/', {
          source_ip: value,
          firewall_id: selectedFirewall.id,
          data_center_name: selectedFirewall.data_center?.name || '',
          firewall_type_name: selectedFirewall.firewall_type?.name || ''
        });
        setDestinationSearchResult(response.data);
      } catch (error: any) {
        setDestinationSearchError(error.response?.data?.error || 'Failed to search address');
      } finally {
        setIsDestinationSearching(false);
      }
    }, 500),
    [selectedFirewall]
  );

  // Modify handleInputChange
  const handleInputChange = (fieldName: string, value: string) => {
    setFormValues(prev => ({
      ...prev,
      [fieldName]: value
    }));

    // Trigger automatic search
    if (fieldName === 'SourceAddress') {
      debouncedSourceSearch(value);
    } else if (fieldName === 'DestinationAddress') {
      debouncedDestinationSearch(value);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      const response = await api.post('/flow-configurations/', {
        source_firewall: selectedSourceFirewall,
        destination_firewall: selectedDestinationFirewall,
        command: selectedCommand
      });
      setConfigurations([...configurations, response.data]);
      setError(null);
    } catch (err) {
      console.error('Error submitting configuration:', err);
      setError('Failed to submit configuration. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSearch = async (searchTerm: string, isSource: boolean) => {
    try {
      if (isSource) {
        setIsSourceSearching(true);
        setSourceSearchError(null);
      } else {
        setIsDestinationSearching(true);
        setDestinationSearchError(null);
      }

      const response = await api.get(`/firewalls/search/?q=${searchTerm}`);
      const results = response.data;

      if (isSource) {
        setSourceSearchResults(results);
      } else {
        setDestinationSearchResults(results);
      }
    } catch (err) {
      console.error('Error searching firewalls:', err);
      if (isSource) {
        setSourceSearchError('Failed to search source firewalls');
      } else {
        setDestinationSearchError('Failed to search destination firewalls');
      }
    } finally {
      if (isSource) {
        setIsSourceSearching(false);
      } else {
        setIsDestinationSearching(false);
      }
    }
  };

  const currentConfig = selectedConfig && {
    fields: [
      { name: 'hostname', label: 'Hostname', required: true },
      { name: 'ipAddress', label: 'IP Address', required: true },
      { name: 'vdom', label: 'VDOM', required: true },
      { name: 'setName', label: 'Set Name', required: true },
      { name: 'srcaddr', label: 'Source Address', required: true },
      { name: 'srcaddrDesc', label: 'Source Description', required: false },
      { name: 'srcintf', label: 'Source Interface', required: true },
      { name: 'dstaddr', label: 'Destination Address', required: true },
      { name: 'dstaddrDesc', label: 'Destination Description', required: false },
      { name: 'dstintf', label: 'Destination Interface', required: true },
      { name: 'service', label: 'Service', required: true }
    ]
  };

  const visibleFields = currentConfig?.fields || [];

  const handleExecuteCommand = async (command: string) => {
    if (!selectedFirewall) {
      setError('Please select a firewall first');
      return;
    }

    // Découper les commandes par ligne (ignorer les lignes vides)
    const commands = command
      .split('\n')
      .map(cmd => cmd.trim())
      .filter(cmd => cmd.length > 0);

    try {
      if (commands.length > 1) {
        // Exécuter tout le template en UNE seule session interactive
        const res = await executeTemplate(selectedFirewall.id, commands);
        if (Array.isArray(res.results)) {
          const newHistory = res.results.map((r, idx) => ({
            id: idx,
            firewall: selectedFirewall.id as unknown as number,
            command: r.command,
            output: r.output || '',
            status: (r.status as any) || 'completed',
            executed_at: new Date().toISOString()
          })) as unknown as CommandResponse[];
          setCommandHistory(prev => Array.isArray(prev) ? [...prev, ...newHistory] : newHistory);
        }
        setError(null);
      } else if (commands.length === 1) {
        // Une seule commande: endpoint classique
        const result = await executeCommand(selectedFirewall.id, commands[0]);
        setCommandHistory(prev => Array.isArray(prev) ? [...prev, result] : [result]);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute command');
    } finally {
      setCommand('');
    }
  };

  useEffect(() => {
    const loadCommandHistory = async () => {
      if (selectedFirewall) {
        try {
          const history = await getCommandHistory(selectedFirewall.id);
          setCommandHistory(Array.isArray(history) ? history : []);
        } catch (err) {
          console.error('Error loading command history:', err);
          setCommandHistory([]);
        }
      }
    };

    loadCommandHistory();
  }, [selectedFirewall]);

  const applyTemplate = () => {
    if (!selectedTemplate) return;
    
    const template = templates.find(t => t.name === selectedTemplate);
    if (!template) return;

    // Extraire toutes les variables du template (format {{ VariableName }})
    const variableRegex = /{{([^}]+)}}/g;
    const templateVariables = new Set<string>();
    let match;
    
    while ((match = variableRegex.exec(template.content)) !== null) {
      const variableName = match[1].trim();
      templateVariables.add(variableName);
    }

    // Créer le mapping automatique des variables
    const variableMapping: Record<string, string> = {};
    templateVariables.forEach(variableName => {
      // Chercher la valeur correspondante dans formValues
      const value = formValues[variableName] || '';
      variableMapping[`{{ ${variableName} }}`] = value;
    });

    // Remplacer toutes les variables dans le template
    let templateContent = template.content;
    Object.entries(variableMapping).forEach(([variable, value]) => {
      templateContent = templateContent.replace(new RegExp(variable, 'g'), value);
    });

    setCommand(templateContent);
  };

  const searchSourceAddress = async () => {
    if (!selectedFirewall || !formValues.SourceAddress) {
      setSearchError('Please select a firewall and enter a source address');
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setFlowMatrixResult(null);

    try {
      const response = await api.post('/analysis/flow-matrix/analyze-ip/', {
        source_ip: formValues.SourceAddress,
        firewall_id: selectedFirewall.id,
        data_center_name: selectedFirewall.data_center?.name || '',
        firewall_type_name: selectedFirewall.firewall_type?.name || ''
      });

      setFlowMatrixResult(response.data);
    } catch (error: any) {
      setSearchError(error.response?.data?.error || 'Failed to search source address');
    } finally {
      setIsSearching(false);
    }
  };

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configurations, setConfigurations] = useState<any[]>([]);
  
  const [isSourceSearching, setIsSourceSearching] = useState(false);
  const [sourceSearchError, setSourceSearchError] = useState<string | null>(null);
  const [sourceSearchResults, setSourceSearchResults] = useState<any[]>([]);
  const [destinationSearchResults, setDestinationSearchResults] = useState<any[]>([]);

  // Form state
  const [selectedSourceFirewall, setSelectedSourceFirewall] = useState<string>('');
  const [selectedDestinationFirewall, setSelectedDestinationFirewall] = useState<string>('');
  const [selectedCommand, setSelectedCommand] = useState<string>('');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Page Header (match Settings style) */}
      <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-2">
            Configurations dynamique des firewalls avec des fichiers Excel
          </h1>
          <p className="text-slate-600 text-lg">Gérez et configurez vos pare-feu de manière dynamique en utilisant des fichiers Excel</p>
        </div>
      </div>
      <div className="bg-white/80 backdrop-blur rounded-2xl shadow p-6 mb-6 border border-slate-100">
        <div className="grid grid-cols-3 gap-4">
          {/* Data Center Selection */}
          <div className="flex items-center space-x-3 p-3 bg-purple-50/70 rounded-xl">
            <Building className="h-6 w-6 text-purple-600" />
            <div className="flex-1">
              <p className="text-sm text-gray-500">Data Center</p>
              <select
                value={selectedDataCenter}
                onChange={handleDataCenterChange}
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-200 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm rounded-md bg-white"
              >
                <option value="">All data centers</option>
                {hierarchy.map((dc) => (
                  <option key={dc.id} value={dc.id}>
                    {dc.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Firewall Type Selection */}
          <div className="flex items-center space-x-3 p-3 bg-purple-50/70 rounded-xl">
            <Shield className="h-6 w-6 text-purple-600" />
            <div className="flex-1">
              <p className="text-sm text-gray-500">Firewall Type</p>
              <select
                value={selectedFirewallType}
                onChange={handleFirewallTypeChange}
                disabled={!selectedDataCenter}
                className={`mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-200 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm rounded-md ${
                  !selectedDataCenter ? 'bg-gray-100' : 'bg-white'
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
          </div>

          {/* Firewall Selection */}
          <div className="flex items-center space-x-3 p-3 bg-purple-50/70 rounded-xl">
            <Server className="h-6 w-6 text-purple-600" />
            <div className="flex-1">
              <p className="text-sm text-gray-500">Firewalls</p>
              <select
                value={selectedFirewall?.id || ''}
                onChange={handleFirewallChange}
                disabled={!selectedFirewallType}
                className={`mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-200 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm rounded-md ${
                  !selectedFirewallType ? 'bg-gray-100' : 'bg-white'
                }`}
              >
                <option value="">Select a firewall</option>
                {getAvailableFirewalls().map((fw) => (
                  <option key={fw.id} value={fw.id}>
                    {fw.name} - {fw.ip_address}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-100 shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Configuration</h2>
            <div className="space-y-4">
              {formFields.length > 0 ? (
                formFields.map((field) => (
                  <div key={field.name} className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    <div className="relative">
                      <input
                        type={field.type === 'string' ? 'text' : field.type}
                        value={formValues[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        required={field.required}
                        className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 bg-white"
                        placeholder={`Enter ${field.label.toLowerCase()}`}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-gray-500">
                  {selectedFirewallType ? 'No fields defined for this firewall type' : 'Select a firewall type to see available fields'}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-100 shadow p-6">
            <h2 className="text-xl font-semibold text-purple-900 mb-4">Sélectionner une configuration</h2>
            {configs.length > 0 ? (
              <>
                <select
                  className="w-full p-2 border border-gray-300 rounded-lg mb-4"
                  value={selectedConfig ? JSON.stringify(selectedConfig) : ''}
                  onChange={(e) => {
                    const config = JSON.parse(e.target.value) as FlowConfig;
                    setSelectedConfig(config);
                    const formValues: Record<string, string> = {};
                    Object.entries(config).forEach(([key, value]) => {
                      formValues[key] = String(value);
                    });
                    setFormValues(formValues);
                  }}
                >
                  <option value="">Choisir une configuration</option>
                  {configs.map((config, index) => (
                    <option key={index} value={JSON.stringify(config)}>
                      {config.hostname} - {config.ipAddress}
                    </option>
                  ))}
                </select>
                {selectedConfig && (
                  <button
                    onClick={() => {
                      const formValues: Record<string, string> = {};
                      Object.entries(selectedConfig).forEach(([key, value]) => {
                        formValues[key] = String(value);
                      });
                      setFormValues(formValues);
                    }}
                    className="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 flex items-center justify-center transition-colors"
                  >
                    <Play className="w-5 h-5 mr-2" />
                    Appliquer la configuration
                  </button>
                )}
              </>
            ) : (
              <div className="text-center py-4 text-gray-500">
                Aucune configuration disponible. Veuillez importer un fichier Excel ou créer une configuration manuelle.
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-slate-100 shadow p-6">
            <h2 className="text-xl font-semibold text-purple-900 mb-4">Importer une configuration</h2>
            <div className="space-y-4">
              {selectedFirewallType ? (
                <>
                  <div className="mb-4">
                    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
                      <h3 className="text-lg font-semibold text-gray-800 mb-3">Format Excel requis:</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              {Object.entries(availableFirewallTypes
                                .find(type => type.id === selectedFirewallType)
                                ?.attributes_schema?.properties || {})
                                .map(([key, value]) => (
                                  <th key={key} className="px-4 py-3 text-left text-sm font-medium text-gray-700 uppercase tracking-wider border-b border-gray-200">
                                    {value.title} {value.required && <span className="text-red-500 ml-1">*</span>}
                                  </th>
                                ))}
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            <tr>
                              {Object.entries(availableFirewallTypes
                                .find(type => type.id === selectedFirewallType)
                                ?.attributes_schema?.properties || {})
                                .map(([key, value]) => (
                                  <td key={key} className="px-4 py-3 text-sm text-gray-500 border-b border-gray-200">
                                    {value.type === 'string' ? 'Texte' : value.type}
                                  </td>
                                ))}
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <p className="mt-3 text-sm text-gray-500">
                        <span className="text-red-500">*</span> Champs obligatoires
                      </p>
                    </div>
                  </div>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer flex flex-col items-center justify-center"
                    >
                      <Upload className="h-12 w-12 text-gray-400 mb-4" />
                      <span className="text-gray-600">Choisir un fichier Excel</span>
                      <span className="text-sm text-gray-500 mt-2">Format: .xlsx, .xls</span>
                    </label>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500">Veuillez sélectionner un type de pare-feu pour voir les champs requis</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add the search section after the form fields */}
      <div className="mt-6 bg-white rounded-2xl border border-slate-100 shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Source Address Search</h3>
        <div className="flex items-center space-x-4">
          <input
            type="text"
            value={formValues.SourceAddress || ''}
            onChange={(e) => handleInputChange('SourceAddress', e.target.value)}
            placeholder="Enter source address"
            className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <button
            onClick={searchSourceAddress}
            disabled={isSearching || !selectedFirewall || !formValues.SourceAddress}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors duration-200 flex items-center gap-2"
          >
            {isSearching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Search Address
              </>
            )}
          </button>
        </div>

        {searchError && (
          <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-md">
            {searchError}
          </div>
        )}

        {flowMatrixResult && (
          <div className="mt-4 space-y-4">
            <div className="p-4 bg-green-50 rounded-md">
              <h4 className="font-medium text-green-800 mb-4">Search Results</h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Source Address */}
                <div className="bg-white p-3 rounded-md shadow-sm">
                  <p className="text-sm text-gray-500">Source Address</p>
                  <p className="font-medium text-gray-900">{flowMatrixResult.ip}</p>
                </div>

                {/* Config Path */}
                <div className="bg-white p-3 rounded-md shadow-sm">
                  <p className="text-sm text-gray-500">Config Path</p>
                  <p className="font-medium text-gray-900">{flowMatrixResult.config_path}</p>
                </div>
              </div>

              {/* Matches: name + comment + groups */}
              <div className="mt-6">
                <p className="text-sm text-gray-500 mb-2">Matched Address Objects</p>
                {flowMatrixResult.matches && flowMatrixResult.matches.length > 0 ? (
                  <div className="space-y-4">
                    {flowMatrixResult.matches.map((item, index) => (
                      <div key={index} className="border-l-4 border-green-500 pl-3">
                        <div className="flex items-center">
                          <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                          <span className="font-medium text-gray-900">{item.name}</span>
                        </div>
                        {item.comment && (
                          <div className="ml-4 mt-1">
                            <p className="text-xs text-gray-500 italic">{item.comment}</p>
                          </div>
                        )}
                        {item.groups && item.groups.length > 0 && (
                          <div className="ml-4 mt-2 text-sm text-blue-600">
                            Groups: {item.groups.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 italic mt-2">No matches found</p>
                )}
              </div>

              {/* Debug */}
              {flowMatrixResult.matches && flowMatrixResult.matches.length > 0 && (
                <details className="mt-4">
                  <summary className="text-sm text-gray-500 cursor-pointer">Debug Information</summary>
                  <div className="mt-2 space-y-2">
                    {flowMatrixResult.matches.map((match, index) => (
                      <div key={index} className="p-2 bg-gray-50 rounded">
                        <p><span className="text-gray-500">Name:</span> {match.name}</p>
                        {match.comment && <p><span className="text-gray-500">Comment:</span> {match.comment}</p>}
                        {match.groups && match.groups.length > 0 && (
                          <p><span className="text-gray-500">Groups:</span> {match.groups.join(', ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        )}
      </div>


      {/* Command Line Interface */}
      <div className="mt-8 bg-gray-900 rounded-2xl shadow-lg p-6 border border-gray-800">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <h2 className="text-xl font-semibold text-gray-200 ml-2 flex items-center gap-2"><Terminal className="h-5 w-5" /> Terminal</h2>
        </div>
        
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-green-400">$</span>
            <span className="text-gray-400">Selected Firewall:</span>
            <span className="text-purple-400">
              {selectedFirewall ? `${selectedFirewall.name} (${selectedFirewall.ip_address})` : 'None'}
            </span>
          </div>

          {/* Template Selection */}
          <div className="mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <span className="text-green-400">$</span>
              <span className="text-gray-400">Template:</span>
            </div>
            <div className="flex space-x-2">
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="flex-1 p-2 bg-gray-800 text-gray-200 border border-gray-700 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                disabled={isLoadingTemplates}
              >
                <option value="">Select a template...</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.name}>
                    {template.name}
                  </option>
                ))}
              </select>
              <button
                onClick={applyTemplate}
                disabled={!selectedTemplate || isLoadingTemplates}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors duration-200"
              >
                {isLoadingTemplates ? 'Loading...' : 'Apply Template'}
              </button>
            </div>
            {templateError && (
              <div className="mt-2 text-sm text-red-400">
                {templateError}
              </div>
            )}
          </div>

          {/* Command Input */}
          <div className="flex space-x-2">
            <div className="flex-1 relative">
              <span className="absolute left-3 top-2 text-green-400">$</span>
              <textarea
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="Enter command..."
                className="w-full h-32 pl-8 p-2 bg-gray-800 text-gray-200 border border-gray-700 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm resize-none"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleExecuteCommand(command);
                  }
                }}
              />
            </div>
            <div className="flex flex-col space-y-2">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  handleExecuteCommand(command);
                }}
                disabled={isExecuting || !selectedFirewall || !command.trim()}
                className={`px-4 py-2 rounded-md transition-colors duration-200 ${
                  isExecuting
                    ? 'bg-yellow-600 text-white'
                    : !selectedFirewall || !command.trim()
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-purple-600 text-white hover:bg-purple-700'
                }`}
              >
                {isExecuting ? (
                  <div className="flex items-center">
                    <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    Executing...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Play className="h-4 w-4" />
                    Execute
                  </div>
                )}
              </button>
              <button
                onClick={() => setCommand('')}
                className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors duration-200"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        {/* Command Output */}
        {commandOutput && (
          <div className="mb-4 p-4 bg-gray-800 rounded-md border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-lg">Output:</span>
              <button
                onClick={() => setCommandOutput('')}
                className="text-gray-500 hover:text-gray-400"
              >
                Clear
              </button>
            </div>
            <pre className="text-sm overflow-auto max-h-96 font-mono text-gray-300 p-4 bg-gray-900 rounded-md">
              {commandOutput}
            </pre>
          </div>
        )}

        {/* Error Display */}
        {executionError && (
          <div className="mb-4 p-4 bg-red-900/50 text-red-400 rounded-md border border-red-700">
            <div className="flex items-center justify-between">
              <span className="text-red-500 font-semibold">Error:</span>
              <button
                onClick={() => setExecutionError(null)}
                className="text-red-500 hover:text-red-400"
              >
                Clear
              </button>
            </div>
            <p className="mt-2">{executionError}</p>
          </div>
        )}

        {/* Command History */}
        {commandHistory.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-green-400">$</span>
                <span className="text-gray-400">History:</span>
              </div>
              <button
                onClick={() => setCommandHistory([])}
                className="text-gray-500 hover:text-gray-400 text-sm"
              >
                Clear History
              </button>
            </div>
            <div className="space-y-2">
              {commandHistory.map((item, index) => (
                <div 
                  key={`${item.id}-${item.executed_at}-${index}`} 
                  className="bg-gray-800 rounded-md p-3 border border-gray-700"
                >
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-green-400">$</span>
                      <span className="font-mono text-sm text-gray-300">{item.command}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        item.status === 'completed' ? 'bg-green-900 text-green-300' :
                        item.status === 'failed' ? 'bg-red-900 text-red-300' :
                        item.status === 'executing' ? 'bg-yellow-900 text-yellow-300' :
                        'bg-gray-900 text-gray-300'
                      }`}>
                        {item.status}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(item.executed_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  {item.output && (
                    <pre className={`text-sm overflow-auto max-h-40 font-mono ${
                      item.status === 'completed' ? 'text-gray-300' : 'text-red-400'
                    }`}>
                      {item.output}
                    </pre>
                  )}
                  {item.error_message && (
                    <div className="mt-2 text-sm text-red-400">
                      Error: {item.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default FlowMatrix;

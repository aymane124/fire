import React, { useState, useEffect, useCallback } from 'react';
import { Plus, ChevronDown, ChevronRight, Trash2, Upload } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config';
import { variableService, Variable } from '../services/templateService';
import { navigateTo } from '../utils/navigation';

interface DataCenter {
  id: string;
  name: string;
  description: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  owner: string;
  owner_username: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  firewall_count: number;
  firewall_type_count: number;
  firewalls: Firewall[];
  firewall_types: FirewallType[];
}

interface Firewall {
  id: string;
  name: string;
  ip_address: string;
  firewall_type: string;
}

interface FirewallType {
  id: string;
  name: string;
  description: string;
  attributes_schema: Record<string, any>;
  data_center: string;
  firewalls: Firewall[];
}

interface FirewallConfigElement {
  name: string;
  label: string;
  required: boolean;
}

const ATTRIBUTE_ORDER = [
  'Hostname',
  'IP Adresse', 
  'VDOM',
  'Name',
  'SourceAddress',
  'SourceDescription',
  'SourceInterface',
  'DestinationAddress',
  'DestinationDescription',
  'DestinationInterface',
  'service'
];

function Settings() {
  const [dataCenters, setDataCenters] = useState<DataCenter[]>([]);
  const [expandedDCs, setExpandedDCs] = useState<string[]>([]);
  const [expandedTypes, setExpandedTypes] = useState<string[]>([]);
  const [newDataCenter, setNewDataCenter] = useState({
    name: '',
    description: '',
    location: '',
    latitude: '',
    longitude: ''
  });
  const [newFirewallType, setNewFirewallType] = useState<{
    name: string;
    description: string;
  }>({
    name: '',
    description: ''
  });
  const [firewallConfigElements, setFirewallConfigElements] = useState<FirewallConfigElement[]>([]);
  const [selectedConfigElements, setSelectedConfigElements] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFirewall, setSelectedFirewall] = useState<Firewall | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [currentFirewallType, setCurrentFirewallType] = useState('');
  const [dataCenter, setDataCenter] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [selectedFirewallTypeId, setSelectedFirewallTypeId] = useState<number>(1);
  const [editingDataCenter, setEditingDataCenter] = useState<DataCenter | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingFirewallType, setEditingFirewallType] = useState<FirewallType | null>(null);
  const [isEditFirewallTypeModalOpen, setIsEditFirewallTypeModalOpen] = useState(false);
  const [newFirewall, setNewFirewall] = useState({
    name: '',
    ip_address: '',
    firewall_type: ''
  });
  const [isAddingFirewall, setIsAddingFirewall] = useState(false);
  const [selectedFirewallTypeForNew, setSelectedFirewallTypeForNew] = useState<string>('');
  const [newVariableName, setNewVariableName] = useState('');
  const [newVariableDescription, setNewVariableDescription] = useState('');
  const [isAddingVariable, setIsAddingVariable] = useState(false);

  // Get token from localStorage
  const getAuthToken = () => {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No authentication token found');
    }
    return token;
  };

  // Create axios instance with auth header
  const api = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Add request interceptor to update auth header
  api.interceptors.request.use(
    (config) => {
      try {
        const token = getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        // Remove any double 'api' prefix in the URL
        if (config.url?.startsWith('/api/')) {
          config.url = config.url.replace('/api/', '/');
        }
        return config;
      } catch (error) {
        console.error('Authentication error:', error);
        // Redirect to login page if token is missing
        navigateTo('/login');
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Add response interceptor to handle 401 errors
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response && error.response.status === 401) {
        // Clear token and redirect to login page
        localStorage.removeItem('token');
        navigateTo('/login');
      }
      return Promise.reject(error);
    }
  );

  // Fetch all data
  const fetchAllData = async () => {
    try {
      setIsLoading(true);
      const [firewallTypesRes, dataCentersRes, firewallsRes] = await Promise.all([
        api.get('/firewalls/firewall-types/'),
        api.get('/datacenters/'),
        api.get('/firewalls/')
      ]);

      // Ensure we have arrays to work with
      const firewallTypesData = Array.isArray(firewallTypesRes.data?.results) ? firewallTypesRes.data.results : [];
      const dataCentersData = Array.isArray(dataCentersRes.data?.results) ? dataCentersRes.data.results : [];
      const firewallsData = Array.isArray(firewallsRes.data?.results) ? firewallsRes.data.results : [];

      // Format and combine the data
      const formattedDataCenters = dataCentersData.map((dc: any) => ({
        id: dc.id,
        name: dc.name,
        description: dc.description || '',
        location: dc.location || '',
        latitude: dc.latitude ? parseFloat(dc.latitude) : null,
        longitude: dc.longitude ? parseFloat(dc.longitude) : null,
        owner: dc.owner || '',
        owner_username: dc.owner_username || '',
        created_at: dc.created_at,
        updated_at: dc.updated_at,
        is_active: dc.is_active,
        firewall_count: dc.firewall_count || 0,
        firewall_type_count: dc.firewall_type_count || 0,
        firewalls: firewallsData.filter((fw: any) => fw.data_center?.id === dc.id),
        firewall_types: firewallTypesData.filter((type: any) => type.data_center === dc.id)
      }));

      setDataCenters(formattedDataCenters);
      
      // Set initial selections from localStorage
      const savedFirewallId = localStorage.getItem('selectedFirewallId');
      const savedFirewallType = localStorage.getItem('firewallType');
      const savedDataCenter = localStorage.getItem('dataCenter');
      
      if (savedFirewallId) {
        const firewall = firewallsData.find((f: Firewall) => f.id === savedFirewallId);
        if (firewall) {
          setSelectedFirewall(firewall);
          setFormData(prev => ({ ...prev, ipAddress: firewall.ip_address }));
        }
      }
      
      if (savedFirewallType) {
        setCurrentFirewallType(savedFirewallType);
      }
      
      if (savedDataCenter) {
        setDataCenter(savedDataCenter);
      }
    } catch (error) {
      alert('Erreur lors du chargement des données. Veuillez rafraîchir la page.');
    } finally {
      setIsLoading(false);
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchAllData();
  }, []);

  // Refresh data after modifications
  const refreshData = async () => {
    await fetchAllData();
  };

  const toggleDC = (dcId: string) => {
    setExpandedDCs(prev => 
      prev.includes(dcId) ? prev.filter(id => id !== dcId) : [...prev, dcId]
    );
  };

  const toggleType = (typeId: string) => {
    setExpandedTypes(prev =>
      prev.includes(typeId) ? prev.filter(id => id !== typeId) : [...prev, typeId]
    );
  };

  const handleAddDataCenter = async () => {
    if (newDataCenter.name) {
      try {
        // Validation des coordonnées
        let latitude = null;
        let longitude = null;

        if (newDataCenter.latitude) {
          const lat = parseFloat(newDataCenter.latitude);
          if (!isNaN(lat) && lat >= -90 && lat <= 90) {
            latitude = Number(lat.toFixed(6)); // Limiter à 6 décimales
          } else {
            alert('La latitude doit être comprise entre -90 et 90 degrés');
            return;
          }
        }

        if (newDataCenter.longitude) {
          const lng = parseFloat(newDataCenter.longitude);
          if (!isNaN(lng) && lng >= -180 && lng <= 180) {
            longitude = Number(lng.toFixed(6)); // Limiter à 6 décimales
          } else {
            alert('La longitude doit être comprise entre -180 et 180 degrés');
            return;
          }
        }

        const data = {
          name: newDataCenter.name.trim(),
          description: newDataCenter.description.trim() || null,
          location: newDataCenter.location.trim() || null,
          latitude: latitude,
          longitude: longitude,
          is_active: true
        };

        // Vérification finale des données
        if (data.latitude !== null && data.longitude === null) {
          alert('Si la latitude est fournie, la longitude doit également être fournie');
          return;
        }
        if (data.latitude === null && data.longitude !== null) {
          alert('Si la longitude est fournie, la latitude doit également être fournie');
          return;
        }

        console.log('Sending data to API:', data);

        const response = await api.post('/datacenters/', data);
        console.log('API Response:', response.data);

        setNewDataCenter({
          name: '',
          description: '',
          location: '',
          latitude: '',
          longitude: ''
        });
        await refreshData();
      } catch (error: any) {
        console.error('Error creating data center:', error);
        console.error('Error response:', error.response?.data);
        
        // Gestion spécifique des erreurs de validation
        if (error.response?.data?.longitude) {
          alert(`Erreur de longitude: ${error.response.data.longitude[0]}`);
        } else if (error.response?.data?.latitude) {
          alert(`Erreur de latitude: ${error.response.data.latitude[0]}`);
        } else {
          const errorMessage = error.response?.data?.detail || 
                             error.response?.data?.non_field_errors?.[0] || 
                             'Erreur lors de la création du datacenter. Veuillez réessayer.';
          alert(errorMessage);
        }
      }
    } else {
      alert('Le nom du datacenter est requis');
    }
  };
  

  const handleAddFirewallType = async (dcId: string) => {
    const { name, description } = newFirewallType;
    if (name) {
      try {
        const selectedElements = Object.entries(selectedConfigElements)
          .filter(([_, selected]) => selected)
          .map(([name]) => name);

        const requestData = {
          name,
          description: description || '',
          data_center: dcId,
          attributes_schema: {
            type: "object",
            properties: selectedElements.reduce((acc, elem) => {
              const configElement = firewallConfigElements.find(ce => ce.name === elem);
              if (configElement) {
                acc[elem] = {
                  type: "string",
                  title: configElement.label,
                  required: configElement.required
                };
              }
              return acc;
            }, {} as Record<string, any>),
            required: selectedElements.filter(elem => {
              const configElement = firewallConfigElements.find(ce => ce.name === elem);
              return configElement?.required;
            })
          }
        };

        console.log('Creating firewall type with data:', requestData);

        const response = await api.post('/firewalls/firewall-types/', requestData, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });

        console.log('Firewall type created successfully:', response.data);

        setNewFirewallType({
          name: '',
          description: ''
        });
        setSelectedConfigElements(
          firewallConfigElements.reduce((acc, elem) => ({ ...acc, [elem.name]: false }), {})
        );
        await refreshData();
      } catch (error: any) {
        console.error('Error creating firewall type:', error);
        console.error('Error response:', error.response?.data);
        const errorMessage = error.response?.data?.detail || error.response?.data?.owner?.[0] || 'Erreur lors de la création du type de pare-feu.';
        alert(errorMessage);
      }
    }
  };

  const handleDeleteDataCenter = async (dcId: string) => {
    try {
      await api.delete(`/datacenters/${dcId}/`);
      await refreshData(); // Refresh all data after deletion
    } catch (error: any) {
      console.error('Error deleting data center:', error);
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression du datacenter.';
      alert(errorMessage);
    }
  };

  const handleDeleteFirewallType = async (typeId: string) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce type de pare-feu ?')) {
      try {
        await api.delete(`/firewalls/firewall-types/${typeId}/`);
        await refreshData();
      } catch (error: any) {
        console.error('Error deleting firewall type:', error);
        const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression du type de pare-feu.';
        alert(errorMessage);
      }
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent, firewallTypeId: string) => {
    e.preventDefault();
    setIsDragging(false);
    setUploadError(null);
    setUploadProgress(0);

    const files = Array.from(e.dataTransfer.files);
    const csvFiles = files.filter(file => file.type === 'text/csv' || file.name.endsWith('.csv'));

    if (csvFiles.length === 0) {
        setUploadError('Veuillez déposer uniquement des fichiers CSV');
        return;
    }

    for (const file of csvFiles) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('firewall_type', firewallTypeId);

            const response = await api.post('/api/firewalls/upload-csv/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                onUploadProgress: (progressEvent) => {
                    const progress = progressEvent.total
                        ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        : 0;
                    setUploadProgress(progress);
                },
            });

            if (response.data.success) {
                setUploadMessage(`Fichier téléchargé avec succès. ${response.data.created_count} pare-feu(s) créé(s).`);
                setUploadError(null);
                await refreshData();
            } else {
                const errorMessage = response.data.error || 'Erreur lors du téléchargement';
                const details = response.data.errors || [];
                setUploadError(`${errorMessage}\n${details.join('\n')}`);
            }
        } catch (error: any) {
            console.error('Error uploading CSV:', error);
            const errorMessage = error.response?.data?.error || 'Erreur lors du téléchargement du fichier';
            setUploadError(errorMessage);
        }
    }
  }, [refreshData]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/api/firewalls/upload-csv/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        console.log('Upload response:', response.data);
        fetchAllData(); // Rafraîchir les données après l'upload
    } catch (error) {
        console.error('Error uploading file:', error);
    }
  };

  const handleEditDataCenter = (dc: DataCenter) => {
    setEditingDataCenter(dc);
    setIsEditModalOpen(true);
  };

  const handleUpdateDataCenter = async () => {
    if (!editingDataCenter) return;

    try {
      // Validation des coordonnées
      let latitude = editingDataCenter.latitude;
      let longitude = editingDataCenter.longitude;

      if (latitude !== null && (latitude < -90 || latitude > 90)) {
        alert('La latitude doit être comprise entre -90 et 90 degrés');
        return;
      }

      if (longitude !== null && (longitude < -180 || longitude > 180)) {
        alert('La longitude doit être comprise entre -180 et 180 degrés');
        return;
      }

      // Vérification finale des données
      if (latitude !== null && longitude === null) {
        alert('Si la latitude est fournie, la longitude doit également être fournie');
        return;
      }
      if (latitude === null && longitude !== null) {
        alert('Si la longitude est fournie, la latitude doit également être fournie');
        return;
      }

      const data = {
        name: editingDataCenter.name.trim(),
        description: editingDataCenter.description?.trim() || null,
        location: editingDataCenter.location?.trim() || null,
        latitude: latitude,
        longitude: longitude,
        is_active: editingDataCenter.is_active
      };

      await api.put(`/datacenters/${editingDataCenter.id}/`, data);
      setIsEditModalOpen(false);
      setEditingDataCenter(null);
      await refreshData();
    } catch (error: any) {
      console.error('Error updating data center:', error);
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.non_field_errors?.[0] || 
                          'Erreur lors de la mise à jour du datacenter.';
      alert(errorMessage);
    }
  };

  const handleEditFirewallType = (type: FirewallType) => {
    setEditingFirewallType(type);
    setIsEditFirewallTypeModalOpen(true);
  };

  const handleUpdateFirewallType = async () => {
    if (!editingFirewallType) return;

    try {
      const selectedElements = Object.entries(selectedConfigElements)
        .filter(([_, selected]) => selected)
        .map(([name]) => name);

      const requestData = {
        name: editingFirewallType.name.trim(),
        description: editingFirewallType.description?.trim() || '',
        data_center: editingFirewallType.data_center,
        attributes_schema: {
          type: "object",
          properties: selectedElements.reduce((acc, elem) => {
            const configElement = firewallConfigElements.find(ce => ce.name === elem);
            if (configElement) {
              acc[elem] = {
                type: "string",
                title: configElement.label,
                required: configElement.required
              };
            }
            return acc;
          }, {} as Record<string, any>),
          required: selectedElements.filter(elem => {
            const configElement = firewallConfigElements.find(ce => ce.name === elem);
            return configElement?.required;
          })
        }
      };

      await api.put(`/firewalls/firewall-types/${editingFirewallType.id}/`, requestData);
      setIsEditFirewallTypeModalOpen(false);
      setEditingFirewallType(null);
      await refreshData();
    } catch (error: any) {
      console.error('Error updating firewall type:', error);
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.non_field_errors?.[0] || 
                          'Erreur lors de la mise à jour du type de pare-feu.';
      alert(errorMessage);
    }
  };

  const handleAddFirewall = async (firewallTypeId: string) => {
    if (!newFirewall.name || !newFirewall.ip_address) {
      alert('Le nom et l\'adresse IP sont requis');
      return;
    }

    try {
      // Trouver le type de firewall pour obtenir le data center
      const firewallType = dataCenters
        .flatMap(dc => dc.firewall_types)
        .find(type => type.id === firewallTypeId);

      if (!firewallType) {
        throw new Error('Type de firewall non trouvé');
      }

      // Obtenir l'ID de l'utilisateur depuis le localStorage ou l'API
      let userId;
      const userData = localStorage.getItem('userData');
      if (userData) {
        const user = JSON.parse(userData);
        userId = user.id;
      } else {
        // Si les données ne sont pas dans le localStorage, les récupérer depuis l'API
        const response = await api.get('/auth/users/me/');
        userId = response.data.id;
      }

      if (!userId) {
        throw new Error('Impossible de récupérer l\'ID de l\'utilisateur');
      }

      const data = {
        name: newFirewall.name.trim(),
        ip_address: newFirewall.ip_address.trim(),
        firewall_type: firewallTypeId,
        data_center: firewallType.data_center,
        owner: userId
      };

      console.log('Sending data to API:', data);

      const response = await api.post('/firewalls/firewalls/', data);
      console.log('API Response:', response.data);

      setNewFirewall({
        name: '',
        ip_address: '',
        firewall_type: ''
      });
      setIsAddingFirewall(false);
      await refreshData();
    } catch (error: any) {
      console.error('Error creating firewall:', error);
      console.error('Error response:', error.response?.data);
      
      let errorMessage = 'Erreur lors de la création du pare-feu.';
      
      if (error.response?.data) {
        if (typeof error.response.data === 'object') {
          // Si c'est un objet d'erreurs de validation
          const errorDetails = Object.entries(error.response.data)
            .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
            .join('\n');
          errorMessage = `Erreurs de validation:\n${errorDetails}`;
        } else if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else if (error.response.data.detail) {
          errorMessage = error.response.data.detail;
        }
      }
      
      alert(errorMessage);
    }
  };

  const handleDeleteFirewall = async (firewallId: string) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce pare-feu ?')) {
      try {
        await api.delete(`/firewalls/${firewallId}/`);
        await refreshData();
      } catch (error: any) {
        console.error('Error deleting firewall:', error);
        const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression du pare-feu.';
        alert(errorMessage);
      }
    }
  };

  const handleAddVariable = async () => {
    if (!newVariableName.trim() || !newVariableDescription.trim()) {
      alert("Le nom et la description sont requis");
      return;
    }
    try {
      setIsAddingVariable(true);
      await variableService.createVariable({
        name: newVariableName.trim(),
        description: newVariableDescription.trim()
      });
      setNewVariableName('');
      setNewVariableDescription('');
      // Recharge les variables
      const variables = await variableService.getVariables();
      const configElements = variables.map(variable => ({
        name: variable.name,
        label: variable.name,
        required: false
      }));
      setFirewallConfigElements(configElements);
      setSelectedConfigElements(
        configElements.reduce((acc, elem) => ({ ...acc, [elem.name]: false }), {})
      );
    } catch (error) {
      alert("Erreur lors de la création de la variable");
    } finally {
      setIsAddingVariable(false);
    }
  };

  const renderDataCenterList = () => {
    return (
      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
          Liste des Datacenters et Types de Firewall
        </h2>
        <div className="space-y-6">
                      {dataCenters.map(dc => (
              <div key={dc.id} className="bg-white/60 backdrop-blur-sm rounded-xl border border-white/30 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
                {/* Datacenter Header */}
                <div className="bg-gradient-to-r from-slate-100 to-purple-50 p-6 flex justify-between items-center">
                  <div>
                    <h3 className="text-xl font-bold text-slate-900 mb-1">{dc.name}</h3>
                    <p className="text-slate-600 flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {dc.location}
                    </p>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleEditDataCenter(dc)}
                      className="px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 flex items-center gap-2 shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Modifier
                    </button>
                    <button
                      onClick={() => handleDeleteDataCenter(dc.id)}
                      className="px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 flex items-center gap-2 shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
                    >
                      <Trash2 className="h-4 w-4" />
                      Supprimer
                    </button>
                  </div>
                </div>

              {/* Firewall Types List */}
              <div className="p-6">
                <h4 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Types de Firewall
                </h4>
                <div className="space-y-4">
                  {dc.firewall_types?.map(type => (
                    <div key={type.id} className="bg-gradient-to-r from-slate-50 to-purple-50 p-4 rounded-xl border border-white/50 shadow-sm hover:shadow-md transition-all duration-200">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-bold text-slate-900 text-lg mb-1">{type.name}</p>
                          <p className="text-slate-600 mb-3">{type.description}</p>
                          <div className="mt-3">
                            <p className="text-sm font-medium text-slate-700 mb-2">Attributs configurés:</p>
                            <div className="flex flex-wrap gap-2">
                              {type.attributes_schema?.properties && 
                                Object.entries(type.attributes_schema.properties)
                                .sort(([a], [b]) => {
                                  const indexA = ATTRIBUTE_ORDER.indexOf(a);
                                  const indexB = ATTRIBUTE_ORDER.indexOf(b);
                                  if (indexA === -1) return 1;
                                  if (indexB === -1) return -1;
                                  return indexA - indexB;
                                })
                                .map(([key, value]) => (
                                  <span key={key} className="px-3 py-1 bg-gradient-to-r from-purple-100 to-indigo-100 text-purple-800 text-sm rounded-full border border-purple-200 font-medium">
                                    {key}
                                  </span>
                                ))
                              }
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 ml-4">
                          <button
                            onClick={() => {
                              setSelectedFirewallTypeForNew(type.id);
                              setIsAddingFirewall(true);
                            }}
                            className="px-3 py-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg hover:from-green-600 hover:to-emerald-700 flex items-center gap-2 shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
                          >
                            <Plus className="h-4 w-4" />
                            Ajouter Firewall
                          </button>
                          <button
                            onClick={() => handleEditFirewallType(type)}
                            className="px-3 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 flex items-center gap-2 shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Modifier
                          </button>
                          <button
                            onClick={() => handleDeleteFirewallType(type.id)}
                            className="px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 flex items-center gap-2 shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
                          >
                            <Trash2 className="h-4 w-4" />
                            Supprimer
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderFirewallType = (dc: DataCenter, type: FirewallType) => {
    return (
      <div key={type.id} className="ml-6 mb-4">
        <div className="flex items-center justify-between bg-gray-50 p-3 rounded-md">
          <div className="flex items-center">
            <button
              onClick={() => toggleType(type.id)}
              className="mr-2 text-gray-500 hover:text-gray-700"
            >
              {expandedTypes.includes(type.id) ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
            </button>
            <span className="font-medium">{type.name}</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                setSelectedFirewallTypeForNew(type.id);
                setIsAddingFirewall(true);
              }}
              className="px-2 py-1 bg-green-500 text-white rounded-md hover:bg-green-600 flex items-center gap-1"
            >
              <Plus className="h-3 w-3" />
              Ajouter Firewall
            </button>
            <button
              onClick={() => handleEditFirewallType(type)}
              className="px-2 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center gap-1"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Modifier
            </button>
            <button
              onClick={() => handleDeleteFirewallType(type.id)}
              className="px-2 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 flex items-center gap-1"
            >
              <Trash2 className="h-3 w-3" />
              Supprimer
            </button>
          </div>
        </div>
        
        {expandedTypes.includes(type.id) && (
          <div className="mt-2 p-4 bg-white rounded-md shadow">
            {/* Liste des firewalls existants */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Pare-feu existants</h4>
              <div className="space-y-2">
                {type.firewalls?.map(fw => (
                  <div key={fw.id} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                    <div>
                      <p className="font-medium text-gray-900">{fw.name}</p>
                      <p className="text-sm text-gray-500">{fw.ip_address}</p>
                    </div>
                    <button
                      onClick={() => handleDeleteFirewall(fw.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Zone de dépôt CSV */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
                isDragging 
                  ? 'border-purple-500 bg-gradient-to-br from-purple-50 to-indigo-50 shadow-lg scale-105' 
                  : 'border-slate-300 hover:border-purple-400 hover:bg-gradient-to-br hover:from-slate-50 hover:to-purple-50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, type.id)}
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.csv';
                input.multiple = true;
                input.onchange = async (e) => {
                  const files = Array.from((e.target as HTMLInputElement).files || []);
                  if (files.length > 0) {
                    setUploadError(null);
                    setUploadProgress(0);
                    
                    for (const file of files) {
                      try {
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('firewall_type', type.id);

                        const response = await api.post('/api/firewalls/upload-csv/', formData, {
                          headers: {
                            'Content-Type': 'multipart/form-data',
                          },
                          onUploadProgress: (progressEvent) => {
                            const progress = progressEvent.total
                              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
                              : 0;
                            setUploadProgress(progress);
                          },
                        });

                        if (response.data.success) {
                          setUploadMessage(`Fichier téléchargé avec succès. ${response.data.created_count} pare-feu(s) créé(s).`);
                          setUploadError(null);
                          await refreshData();
                        } else {
                          const errorMessage = response.data.error || 'Erreur lors du téléchargement';
                          const details = response.data.errors || [];
                          setUploadError(`${errorMessage}\n${details.join('\n')}`);
                        }
                      } catch (error: any) {
                        console.error('Error uploading CSV:', error);
                        const errorMessage = error.response?.data?.error || 'Erreur lors du téléchargement du fichier';
                        setUploadError(errorMessage);
                      }
                    }
                  }
                };
                input.click();
              }}
            >
              <div className="relative">
                <Upload className={`mx-auto h-16 w-16 transition-all duration-300 ${
                  isDragging ? 'text-purple-600 scale-110' : 'text-slate-400'
                }`} />
                {isDragging && (
                  <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 bg-purple-400 opacity-20"></div>
                )}
              </div>
              <div className="mt-6">
                <p className="text-lg font-semibold text-slate-700 mb-2">
                  Glissez et déposez vos fichiers CSV ici
                </p>
                <p className="text-slate-500">
                  ou cliquez pour sélectionner des fichiers
                </p>
              </div>
              {uploadProgress !== null && (
                <div className="mt-6">
                  <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-indigo-600 h-3 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-slate-600 mt-2 font-medium">
                    Progression: {uploadProgress}%
                  </p>
                </div>
              )}
              {uploadError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 text-sm font-medium">{uploadError}</p>
                </div>
              )}
              {uploadMessage && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-600 text-sm font-medium">{uploadMessage}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Add useEffect to load variables from database
  useEffect(() => {
    const loadVariables = async () => {
      try {
        const variables = await variableService.getVariables();
        const configElements = variables.map(variable => ({
          name: variable.name,
          label: variable.name,
          required: false
        }));
        setFirewallConfigElements(configElements);
        // Initialize selectedConfigElements with the new variables
        setSelectedConfigElements(
          configElements.reduce((acc, elem) => ({ ...acc, [elem.name]: false }), {})
        );
      } catch (error) {
        console.error('Error loading variables:', error);
      }
    };

    loadVariables();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Header avec glassmorphism */}
      <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-3">
              Paramètres CMS
            </h1>
            <p className="text-slate-600 text-lg">Gérez la structure des data centers et leurs types de firewalls</p>
          </div>
          <button
            onClick={refreshData}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 flex items-center gap-3 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Rafraîchir
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 border-2 border-purple-400 opacity-20"></div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8">
          {/* Liste des datacenters et types de firewall */}
          {renderDataCenterList()}
          
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-purple-900 mb-4">Structure</h2>
              
              {/* Add new Data Center */}
              <div className="mb-6 p-4 border border-dashed border-gray-300 rounded-lg">
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Nom du Data Center *"
                      value={newDataCenter.name}
                      onChange={(e) => setNewDataCenter(prev => ({ ...prev, name: e.target.value }))}
                      className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                      required
                    />
                    <button
                      onClick={handleAddDataCenter}
                      className="px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <textarea
                    placeholder="Description"
                    value={newDataCenter.description}
                    onChange={(e) => setNewDataCenter(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full p-2 border border-gray-300 rounded-md text-sm"
                    rows={2}
                  />
                  <input
                    type="text"
                    placeholder="Adresse physique"
                    value={newDataCenter.location}
                    onChange={(e) => setNewDataCenter(prev => ({ ...prev, location: e.target.value }))}
                    className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Latitude (-90 à 90)"
                        value={newDataCenter.latitude}
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === '' || (parseFloat(value) >= -90 && parseFloat(value) <= 90)) {
                            setNewDataCenter(prev => ({ ...prev, latitude: value }));
                          }
                        }}
                        className="w-full p-2 border border-gray-300 rounded-md text-sm"
                        min="-90"
                        max="90"
                      />
                      <p className="text-xs text-gray-500 mt-1">Ex: 33.552084</p>
                    </div>
                    <div>
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Longitude (-180 à 180)"
                        value={newDataCenter.longitude}
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === '' || (parseFloat(value) >= -180 && parseFloat(value) <= 180)) {
                            setNewDataCenter(prev => ({ ...prev, longitude: value }));
                          }
                        }}
                        className="w-full p-2 border border-gray-300 rounded-md text-sm"
                        min="-180"
                        max="180"
                      />
                      <p className="text-xs text-gray-500 mt-1">Ex: -7.657616</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tree Structure */}
              <div className="space-y-2">
                {Array.isArray(dataCenters) && dataCenters.map(dc => (
                  <div key={dc.id} className="border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-t-lg">
                      <div className="flex items-center">
                        <button
                          onClick={() => toggleDC(dc.id)}
                          className="mr-2 text-gray-500 hover:text-gray-700"
                        >
                          {expandedDCs.includes(dc.id) ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                        <span className="font-medium">{dc.name}</span>
                      </div>
                      <button
                        onClick={() => handleDeleteDataCenter(dc.id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {expandedDCs.includes(dc.id) && (
                      <div className="p-4 space-y-4">
                        {/* Add new Firewall Type */}
                        <div className="p-4 border border-dashed border-gray-300 rounded-lg">
                          <div className="space-y-4">
                            <div className="flex gap-2">
                              <input
                                type="text"
                                placeholder="Nom du type de pare-feu"
                                value={newFirewallType.name}
                                onChange={(e) => setNewFirewallType(prev => ({ ...prev, name: e.target.value }))}
                                className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                              />
                              <button
                                onClick={() => handleAddFirewallType(dc.id)}
                                className="px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                              >
                                <Plus className="w-4 h-4" />
                              </button>
                            </div>
                            <textarea
                              placeholder="Description"
                              value={newFirewallType.description}
                              onChange={(e) => setNewFirewallType(prev => ({ ...prev, description: e.target.value }))}
                              className="w-full p-2 border border-gray-300 rounded-md text-sm"
                              rows={2}
                            />
                            <div className="mb-3">
                              <h4 className="text-sm font-semibold text-purple-800 mb-2 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                                Choisir ou ajouter les éléments statiques pour une configuration dynamique des pare-feu
                              </h4>
                              <p className="text-xs text-gray-600 mb-3">
                                Sélectionnez les éléments de configuration qui seront utilisés pour configurer dynamiquement les pare-feu de ce type
                              </p>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                              {firewallConfigElements.map(elem => (
                                <label key={elem.name} className="flex items-center space-x-2">
                                  <input
                                    type="checkbox"
                                    checked={selectedConfigElements[elem.name]}
                                    onChange={(e) => setSelectedConfigElements(prev => ({
                                      ...prev,
                                      [elem.name]: e.target.checked
                                    }))}
                                    className="rounded text-purple-600 focus:ring-purple-500"
                                  />
                                  <span className="text-sm text-gray-700">{elem.label}</span>
                                </label>
                              ))}
                              {/* Champ d'ajout de variable */}
                              <div className="flex items-center space-x-2 col-span-2 mt-2">
                                <input
                                  type="text"
                                  value={newVariableName}
                                  onChange={e => setNewVariableName(e.target.value)}
                                  placeholder="Nom de la variable"
                                  className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                                  disabled={isAddingVariable}
                                />
                                <input
                                  type="text"
                                  value={newVariableDescription}
                                  onChange={e => setNewVariableDescription(e.target.value)}
                                  placeholder="Description"
                                  className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                                  disabled={isAddingVariable}
                                />
                                <button
                                  onClick={handleAddVariable}
                                  className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                                  disabled={isAddingVariable}
                                >
                                  Ajouter
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Firewall Types List */}
                        <div className="space-y-2">
                          {dc.firewall_types?.map(type => renderFirewallType(dc, type))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          </div>
        </div>
      )}

      {/* Edit DataCenter Modal */}
      {isEditModalOpen && editingDataCenter && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white/95 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl w-full max-w-2xl transform transition-all duration-300">
            <div className="p-8">
              <h2 className="text-3xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
                Modifier le Data Center
              </h2>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Nom *</label>
                  <input
                    type="text"
                    value={editingDataCenter.name}
                    onChange={(e) => setEditingDataCenter(prev => prev ? {...prev, name: e.target.value} : null)}
                    className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                    required
                  />
                </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={editingDataCenter.description || ''}
                  onChange={(e) => setEditingDataCenter(prev => prev ? {...prev, description: e.target.value} : null)}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Adresse physique</label>
                <input
                  type="text"
                  value={editingDataCenter.location || ''}
                  onChange={(e) => setEditingDataCenter(prev => prev ? {...prev, location: e.target.value} : null)}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Latitude (-90 à 90)</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={editingDataCenter.latitude || ''}
                    onChange={(e) => {
                      const value = e.target.value === '' ? null : parseFloat(e.target.value);
                      if (value === null || (value >= -90 && value <= 90)) {
                        setEditingDataCenter(prev => prev ? {...prev, latitude: value} : null);
                      }
                    }}
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                    min="-90"
                    max="90"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Longitude (-180 à 180)</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={editingDataCenter.longitude || ''}
                    onChange={(e) => {
                      const value = e.target.value === '' ? null : parseFloat(e.target.value);
                      if (value === null || (value >= -180 && value <= 180)) {
                        setEditingDataCenter(prev => prev ? {...prev, longitude: value} : null);
                      }
                    }}
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                    min="-180"
                    max="180"
                  />
                </div>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={editingDataCenter.is_active}
                  onChange={(e) => setEditingDataCenter(prev => prev ? {...prev, is_active: e.target.checked} : null)}
                  className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                />
                <label className="ml-2 block text-sm text-gray-900">Actif</label>
              </div>
            </div>
          </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingDataCenter(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={handleUpdateDataCenter}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit FirewallType Modal */}
      {isEditFirewallTypeModalOpen && editingFirewallType && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Modifier le Type de Pare-feu</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom *</label>
                <input
                  type="text"
                  value={editingFirewallType.name}
                  onChange={(e) => setEditingFirewallType(prev => prev ? {...prev, name: e.target.value} : null)}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={editingFirewallType.description || ''}
                  onChange={(e) => setEditingFirewallType(prev => prev ? {...prev, description: e.target.value} : null)}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={3}
                />
              </div>
              <div>
                <div className="mb-3">
                  <h4 className="text-sm font-semibold text-purple-800 mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Choisir ou ajouter les éléments statiques pour une configuration dynamique des pare-feu
                  </h4>
                  <p className="text-xs text-gray-600 mb-3">
                    Sélectionnez les éléments de configuration qui seront utilisés pour configurer dynamiquement les pare-feu de ce type
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {firewallConfigElements.map(elem => (
                    <label key={elem.name} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={selectedConfigElements[elem.name]}
                        onChange={(e) => setSelectedConfigElements(prev => ({
                          ...prev,
                          [elem.name]: e.target.checked
                        }))}
                        className="rounded text-purple-600 focus:ring-purple-500"
                      />
                      <span className="text-sm text-gray-700">{elem.label}</span>
                    </label>
                  ))}
                  {/* Champ d'ajout de variable */}
                  <div className="flex items-center space-x-2 col-span-2 mt-2">
                    <input
                      type="text"
                      value={newVariableName}
                      onChange={e => setNewVariableName(e.target.value)}
                      placeholder="Nom de la variable"
                      className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                      disabled={isAddingVariable}
                    />
                    <input
                      type="text"
                      value={newVariableDescription}
                      onChange={e => setNewVariableDescription(e.target.value)}
                      placeholder="Description"
                      className="flex-1 p-2 border border-gray-300 rounded-md text-sm"
                      disabled={isAddingVariable}
                    />
                    <button
                      onClick={handleAddVariable}
                      className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                      disabled={isAddingVariable}
                    >
                      Ajouter
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setIsEditFirewallTypeModalOpen(false);
                  setEditingFirewallType(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={handleUpdateFirewallType}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Firewall Modal */}
      {isAddingFirewall && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Ajouter un Pare-feu</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom *</label>
                <input
                  type="text"
                  value={newFirewall.name}
                  onChange={(e) => setNewFirewall(prev => ({ ...prev, name: e.target.value }))}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Adresse IP *</label>
                <input
                  type="text"
                  value={newFirewall.ip_address}
                  onChange={(e) => setNewFirewall(prev => ({ ...prev, ip_address: e.target.value }))}
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md text-sm"
                  required
                  placeholder="Ex: 192.168.1.1"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setIsAddingFirewall(false);
                  setNewFirewall({
                    name: '',
                    ip_address: '',
                    firewall_type: ''
                  });
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={() => handleAddFirewall(selectedFirewallTypeForNew)}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              >
                Ajouter
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { FeatureCollection } from 'geojson';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API_URL, API_ENDPOINTS } from '../config';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Wifi, WifiOff, Plus } from 'lucide-react';
import { Camera, CameraPingStatus } from '../types/camera';
import { AddCameraForm } from './AddCameraForm';
import { marocData } from '../data/marocData.ts';

// Create axios instance with auth header
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Add request interceptor to update auth header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        // Token expiré ou invalide
        localStorage.removeItem('token');
        window.location.href = '/login';
      } else if (error.response.status === 404) {
        console.error('Endpoint not found:', error.response.config.url);
        return Promise.reject(new Error('Endpoint non trouvé. Veuillez vérifier la configuration du serveur.'));
      }
    }
    return Promise.reject(error);
  }
);

// Fix for default marker icon
const defaultIcon = L.icon({
  iconUrl: '/images/marker-icon.png',
  iconRetinaUrl: '/images/marker-icon-2x.png',
  shadowUrl: '/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Custom camera icon for online cameras
const onlineCameraIcon = L.divIcon({
  className: 'custom-camera-icon',
  html: `
    <svg viewBox="0 0 60.051 60.051" width="32" height="32">
      <g fill="#22c55e">
        <path d="M56.963,32.026H55.14c-1.703,0-3.088,1.385-3.088,3.088v3.912h-10v-6.219c3.646-1.177,5.957-6.052,5.957-12.781
          c0-7.235-2.669-12.333-6.8-12.988c-0.052-0.008-0.104-0.012-0.157-0.012h-40c-0.481,0-0.893,0.343-0.982,0.816l-0.001,0
          c-0.02,0.107-0.472,2.648,1.243,4.714c1.138,1.371,2.92,2.169,5.292,2.395c-0.357,1.59-0.552,3.31-0.552,5.075
          c0,7.29,3.075,13,7,13h21v12.967c0,1.672,1.36,3.033,3.033,3.033h1.935c1.308,0,2.415-0.837,2.84-2h10.193v2.912
          c0,1.703,1.385,3.088,3.088,3.088h1.823c1.703,0,3.088-1.385,3.088-3.088V35.114C60.051,33.411,58.666,32.026,56.963,32.026z"/>
        <circle cx="32.051" cy="27.026" r="1"/>
        <circle cx="28.051" cy="27.026" r="1"/>
        <circle cx="24.051" cy="27.026" r="1"/>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

// Custom camera icon for offline cameras
const offlineCameraIcon = L.divIcon({
  className: 'custom-camera-icon',
  html: `
    <svg viewBox="0 0 60.051 60.051" width="32" height="32">
      <g fill="#ef4444">
        <path d="M56.963,32.026H55.14c-1.703,0-3.088,1.385-3.088,3.088v3.912h-10v-6.219c3.646-1.177,5.957-6.052,5.957-12.781
          c0-7.235-2.669-12.333-6.8-12.988c-0.052-0.008-0.104-0.012-0.157-0.012h-40c-0.481,0-0.893,0.343-0.982,0.816l-0.001,0
          c-0.02,0.107-0.472,2.648,1.243,4.714c1.138,1.371,2.92,2.169,5.292,2.395c-0.357,1.59-0.552,3.31-0.552,5.075
          c0,7.29,3.075,13,7,13h21v12.967c0,1.672,1.36,3.033,3.033,3.033h1.935c1.308,0,2.415-0.837,2.84-2h10.193v2.912
          c0,1.703,1.385,3.088,3.088,3.088h1.823c1.703,0,3.088-1.385,3.088-3.088V35.114C60.051,33.411,58.666,32.026,56.963,32.026z"/>
        <circle cx="32.051" cy="27.026" r="1"/>
        <circle cx="28.051" cy="27.026" r="1"/>
        <circle cx="24.051" cy="27.026" r="1"/>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

// Custom camera icon for untested cameras
const defaultCameraIcon = L.divIcon({
  className: 'custom-camera-icon',
  html: `
    <svg viewBox="0 0 60.051 60.051" width="32" height="32">
      <g fill="#2563eb">
        <path d="M56.963,32.026H55.14c-1.703,0-3.088,1.385-3.088,3.088v3.912h-10v-6.219c3.646-1.177,5.957-6.052,5.957-12.781
          c0-7.235-2.669-12.333-6.8-12.988c-0.052-0.008-0.104-0.012-0.157-0.012h-40c-0.481,0-0.893,0.343-0.982,0.816l-0.001,0
          c-0.02,0.107-0.472,2.648,1.243,4.714c1.138,1.371,2.92,2.169,5.292,2.395c-0.357,1.59-0.552,3.31-0.552,5.075
          c0,7.29,3.075,13,7,13h21v12.967c0,1.672,1.36,3.033,3.033,3.033h1.935c1.308,0,2.415-0.837,2.84-2h10.193v2.912
          c0,1.703,1.385,3.088,3.088,3.088h1.823c1.703,0,3.088-1.385,3.088-3.088V35.114C60.051,33.411,58.666,32.026,56.963,32.026z"/>
        <circle cx="32.051" cy="27.026" r="1"/>
        <circle cx="28.051" cy="27.026" r="1"/>
        <circle cx="24.051" cy="27.026" r="1"/>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

// Add styles for the camera icons
const cameraIconStyles = `
  .custom-camera-icon {
    background: none;
    border: none;
  }
  .custom-camera-icon svg {
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    transition: transform 0.2s ease;
  }
  .custom-camera-icon:hover svg {
    transform: scale(1.1);
  }
  .custom-datacenter-icon {
    background: none;
    border: none;
  }
  .custom-datacenter-icon svg {
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    transition: transform 0.2s ease;
  }
  .custom-datacenter-icon:hover svg {
    transform: scale(1.1);
  }
  .leaflet-popup-content-wrapper {
    padding: 0;
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  .leaflet-popup-content {
    margin: 0;
    min-width: 300px;
    max-width: 500px;
  }
  .datacenter-popup-content {
    padding: 1rem;
    min-width: 300px;
    max-width: 500px;
    max-height: 500px;
    overflow-y: auto;
    background: white;
    border-radius: 8px;
  }
`;

// Add the styles to the document
const styleSheet = document.createElement("style");
styleSheet.innerText = cameraIconStyles;
document.head.appendChild(styleSheet);

interface FirewallType {
  id: string;
  name: string;
  description: string;
  attributes_schema: any;
  firewalls?: Firewall[];
}

interface Firewall {
  id: string;
  name: string;
  ip_address: string;
  firewall_type: string;
}

interface FirewallPingStatus {
  status: 'idle' | 'loading' | 'online' | 'offline' | 'error';
  responseTime: number | null;
  lastUpdate?: number;
}

interface DataCenter {
  id: string;
  name: string;
  description: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
}

const MapClickHandler: React.FC<{ onMapClick: (lat: number, lng: number) => void }> = ({ onMapClick }) => {
  useMapEvents({
    click: (e) => {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

// Add type for cluster
interface Cluster {
  getChildCount(): number;
}

interface PingAllResult {
  total: number;
  online: number;
  offline: number;
  errors: number;
}

const WorldMap: React.FC = () => {
  const [marocData, setMarocData] = useState<FeatureCollection | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [clickPosition, setClickPosition] = useState<[number, number]>([0, 0]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [cameraPingStatuses, setCameraPingStatuses] = useState<Record<string, CameraPingStatus>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);
  const { isAuthenticated, token } = useAuth();
  const mapRef = useRef<L.Map | null>(null);
  const [searchType, setSearchType] = useState<'all' | 'cameras'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'online' | 'offline'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isInitialized, setIsInitialized] = useState(false);
  const refreshTimeoutRef = useRef<number | null>(null);
  const [isPingingAll, setIsPingingAll] = useState(false);
  const [cameraToDelete, setCameraToDelete] = useState<Camera | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedCameras, setSelectedCameras] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [showSelectionList, setShowSelectionList] = useState(false);

  // Fonction pour gérer les erreurs d'authentification
  const handleAuthError = (message: string) => {
    setError(message);
    // Nettoyer le timeout existant s'il y en a un
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
    // Définir un nouveau timeout pour rafraîchir la page
    refreshTimeoutRef.current = window.setTimeout(() => {
      window.location.reload();
    }, 3000); // Rafraîchir après 3 secondes
  };

  // Vérification initiale de l'authentification
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      handleAuthError('Veuillez vous connecter pour accéder à cette page');
      return;
    }

    // Vérifier si le token est valide en essayant de charger les caméras
    api.get(API_ENDPOINTS.CAMERAS.LIST, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    }).then(() => {
      setIsInitialized(true);
    }).catch((error) => {
      if (error.response?.status === 401) {
        handleAuthError('Session expirée. Veuillez vous reconnecter.');
        localStorage.removeItem('token');
        window.location.href = '/login';
      } else {
        setError('Erreur de connexion au serveur');
      }
    });

    // Cleanup function
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isInitialized) return;

    // Set default icon
    L.Marker.prototype.options.icon = defaultIcon;
    
    // Use local GeoJSON data
    setMarocData(marocData);
  }, [isInitialized]);

  useEffect(() => {
    if (!isInitialized) return;

    // Load cameras
    const fetchAllCameras = async () => {
      try {
        setIsLoading(true);
        setMapError(null);
        
        const token = localStorage.getItem('token');
        if (!token) {
          setError('Token non trouvé. Veuillez vous reconnecter.');
          return;
        }

        let allCameras: Camera[] = [];
        let nextUrl = API_ENDPOINTS.CAMERAS.LIST;
        
        while (nextUrl) {
          const response = await api.get(nextUrl, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            }
          });
          
          if (response.data.results) {
            allCameras = [...allCameras, ...response.data.results];
          }
          
          nextUrl = response.data.next;
        }
        
        setCameras(allCameras);
        setError(null);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching cameras:', error);
        if (axios.isAxiosError(error)) {
          if (error.response?.status === 401) {
            setError('Session expirée. Veuillez vous reconnecter.');
            localStorage.removeItem('token');
            window.location.href = '/login';
          } else {
            setError('Erreur lors du chargement des caméras');
            setMapError('Erreur lors du chargement des données de la carte');
          }
        } else {
          setError('Erreur lors du chargement des caméras');
          setMapError('Erreur lors du chargement des données de la carte');
        }
        setCameras([]);
        setIsLoading(false);
      }
    };

    fetchAllCameras();

    // Cleanup
    return () => {
      L.Marker.prototype.options.icon = undefined;
    };
  }, [isInitialized]);

  const handleMapClick = (lat: number, lng: number) => {
    if (!isAuthenticated || !token) {
      handleAuthError('Veuillez vous connecter pour ajouter une caméra');
      return;
    }

    setClickPosition([lat, lng]);
    setShowAddForm(true);
  };

  // Fonction pour pinger une caméra
  const handleCameraPing = async (cameraId: string) => {
    try {
      setCameraPingStatuses(prev => ({
        ...prev,
        [cameraId]: { status: 'loading', responseTime: null }
      }));

      const response = await fetch(`${API_URL}/cameras/cameras/${cameraId}/ping/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Erreur lors du ping');
      }
      
      const data = await response.json();
      setCameraPingStatuses(prev => ({
        ...prev,
        [cameraId]: {
          status: data.status,
          responseTime: data.response_time,
          lastUpdate: Date.now()
        }
      }));
    } catch (error) {
      console.error('Error pinging camera:', error);
      setCameraPingStatuses(prev => ({
        ...prev,
        [cameraId]: { 
          status: 'error', 
          responseTime: null,
          lastUpdate: Date.now()
        }
      }));
    }
  };

  const handleDeleteCamera = async (camera: Camera) => {
    if (!isAuthenticated || !token) {
      setError('Veuillez vous connecter pour supprimer une caméra');
      return;
    }

    setIsDeleting(true);
    try {
      const response = await api.delete(`/cameras/cameras/${camera.id}/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      if (response.status === 204) {
        setSuccess(`Caméra "${fixEncoding(camera.name)}" supprimée avec succès`);
        // Mettre à jour la liste des caméras
        setCameras(prevCameras => prevCameras.filter(c => c.id !== camera.id));
        // Fermer la modal de confirmation
        setCameraToDelete(null);
      }
    } catch (error) {
      console.error('Error deleting camera:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          setError('Session expirée. Veuillez vous reconnecter.');
          localStorage.removeItem('token');
          window.location.href = '/login';
        } else {
          setError(error.response?.data?.error || 'Erreur lors de la suppression de la caméra');
        }
      } else {
        setError('Erreur lors de la suppression de la caméra');
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const fixEncoding = (str: string): string => {
    return str.replace(/Ã©/g, 'é')
             .replace(/Ã¨/g, 'è')
             .replace(/Ã§/g, 'ç')
             .replace(/Ã /g, 'à')
             .replace(/Ã´/g, 'ô')
             .replace(/Ã»/g, 'û')
             .replace(/Ã¯/g, 'ï')
             .replace(/Ã«/g, 'ë')
             .replace(/Ã¹/g, 'ù');
  };

  const isStatusExpired = (lastUpdate: number | undefined) => {
    if (!lastUpdate) return true;
    return Date.now() - lastUpdate > 300000; // 5 minutes
  };

  const getCameraIcon = (cameraId: string) => {
    const status = cameraPingStatuses[cameraId];
    if (!status || status.status === 'idle' || isStatusExpired(status.lastUpdate)) {
        return defaultCameraIcon;
    }
    return status.status === 'online' ? onlineCameraIcon : offlineCameraIcon;
  };

    const filteredCameras = cameras.filter(camera => {
    const matchesSearch = camera.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         camera.ip_address.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = searchType === 'all' || searchType === 'cameras';
    const matchesStatus = filterStatus === 'all' ||
                         (filterStatus === 'online' && cameraPingStatuses[camera.id]?.status === 'online') ||
                         (filterStatus === 'offline' && (cameraPingStatuses[camera.id]?.status === 'offline' || cameraPingStatuses[camera.id]?.status === 'error'));
    return matchesSearch && matchesType && matchesStatus;
  });

  const handlePingAll = async () => {
    if (!isAuthenticated) {
      setError('Veuillez vous connecter pour effectuer un ping');
      return;
    }

    setIsPingingAll(true);
    try {
      // Démarrer le processus de ping asynchrone
      const response = await api.post('/cameras/cameras/ping_all/');
      const taskId = response.data.task_id;

      // Fonction pour vérifier le statut
      const checkStatus = async () => {
        try {
          const statusResponse = await api.get(`/cameras/cameras/check_ping_status/?task_id=${taskId}`);
          const status = statusResponse.data;

          if (status.status === 'completed') {
            // Mettre à jour les statuts des caméras
            const updatedCameraPingStatuses: Record<string, CameraPingStatus> = {};
            status.results.forEach((result: any) => {
              updatedCameraPingStatuses[result.id] = {
                status: result.status,
                responseTime: result.response_time,
                lastUpdate: Date.now()
              };
            });
            setCameraPingStatuses(prev => ({ ...prev, ...updatedCameraPingStatuses }));

            // Mettre à jour la liste des caméras avec les nouveaux statuts
            setCameras(prevCameras => 
              prevCameras.map(camera => {
                const newStatus = updatedCameraPingStatuses[camera.id];
                if (newStatus) {
                  return {
                    ...camera,
                    is_online: newStatus.status === 'online'
                  };
                }
                return camera;
              })
            );

            // Calculer les statistiques
            const totalOnline = Object.values(updatedCameraPingStatuses).filter(s => s.status === 'online').length;
            const totalOffline = Object.values(updatedCameraPingStatuses).filter(s => s.status === 'offline' || s.status === 'error').length;
            setSuccess(`Ping terminé: ${totalOnline} en ligne, ${totalOffline} hors ligne`);
            setIsPingingAll(false);
          } else if (status.status === 'failed') {
            setError(`Erreur lors du ping: ${status.message}`);
            setIsPingingAll(false);
          } else {
            // Continuer à vérifier le statut
            setTimeout(checkStatus, 2000);
          }
        } catch (error) {
          console.error('Error checking ping status:', error);
          setError('Erreur lors de la vérification du statut');
          setIsPingingAll(false);
        }
      };

      // Démarrer la vérification du statut
      checkStatus();

    } catch (error) {
      console.error('Error starting ping process:', error);
      setError('Erreur lors du démarrage du ping');
      setIsPingingAll(false);
    }
  };

  // Fonction pour récupérer l'historique des pings
  const fetchPingHistory = async (cameraId: string) => {
    try {
      const response = await api.get(`/cameras/cameras/get_ping_history/?camera_id=${cameraId}`);
      const history = response.data.results;
      
      if (history && history.length > 0) {
        const lastPing = history[0]; // Le plus récent est le premier
        setCameraPingStatuses(prev => ({
          ...prev,
          [cameraId]: {
            status: lastPing.status,
            responseTime: lastPing.response_time,
            lastUpdate: new Date(lastPing.timestamp).getTime()
          }
        }));
      }
    } catch (error) {
      console.error('Error fetching ping history:', error);
    }
  };

  // Ajouter un useEffect pour charger l'historique des pings au chargement des caméras
  // useEffect(() => {
  //   if (cameras.length > 0) {
  //     cameras.forEach(camera => {
  //       fetchPingHistory(camera.id);
  //     });
  //   }
  // }, [cameras]);

  const handleCameraSelect = (cameraId: string) => {
    if (!isSelectionMode) return;
    
    setSelectedCameras(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(cameraId)) {
        newSelection.delete(cameraId);
      } else {
        newSelection.add(cameraId);
      }
      return newSelection;
    });
    setShowSelectionList(true);
  };

  const handleRemoveFromSelection = (cameraId: string) => {
    setSelectedCameras(prev => {
      const newSelection = new Set(prev);
      newSelection.delete(cameraId);
      return newSelection;
    });
  };

  const handleDeleteSelected = async () => {
    if (!isAuthenticated || !token || selectedCameras.size === 0) return;

    setIsDeleting(true);
    try {
      const deletePromises = Array.from(selectedCameras).map(cameraId => 
        api.delete(`/cameras/cameras/${cameraId}/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
        })
      );

      await Promise.all(deletePromises);
      setSuccess(`${selectedCameras.size} caméra(s) supprimée(s) avec succès`);
      setCameras(prevCameras => prevCameras.filter(c => !selectedCameras.has(c.id)));
      setSelectedCameras(new Set());
      setIsSelectionMode(false);
    } catch (error) {
      console.error('Error deleting cameras:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          setError('Session expirée. Veuillez vous reconnecter.');
          localStorage.removeItem('token');
          window.location.href = '/login';
        } else {
          setError(error.response?.data?.error || 'Erreur lors de la suppression des caméras');
        }
      } else {
        setError('Erreur lors de la suppression des caméras');
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const handlePingSelected = async () => {
    if (!isAuthenticated || !token || selectedCameras.size === 0) return;

    setIsPingingAll(true);
    try {
      const pingPromises = Array.from(selectedCameras).map(cameraId => 
        api.post(`/cameras/cameras/${cameraId}/ping/`)
      );

      const responses = await Promise.all(pingPromises);
      const updatedStatuses: Record<string, CameraPingStatus> = {};
      
      responses.forEach((response, index) => {
        const cameraId = Array.from(selectedCameras)[index];
        updatedStatuses[cameraId] = {
          status: response.data.status,
          responseTime: response.data.response_time,
          lastUpdate: Date.now()
        };
      });

      setCameraPingStatuses(prev => ({ ...prev, ...updatedStatuses }));
      setSuccess(`Ping de ${selectedCameras.size} caméra(s) terminé`);
    } catch (error) {
      console.error('Error pinging cameras:', error);
      setError('Erreur lors du ping des caméras sélectionnées');
    } finally {
      setIsPingingAll(false);
    }
  };

  if (isLoading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg">Chargement de la carte...</p>
        </div>
      </div>
    );
  }

  if (mapError) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="bg-red-100 p-4 rounded-lg mb-4">
            <p className="text-red-600 font-medium">Erreur de chargement de la carte</p>
            <p className="text-red-500 text-sm mt-2">{mapError}</p>
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            Recharger la page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen rounded-lg overflow-hidden shadow-lg relative bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Control Panel */}
      <div className="absolute top-4 right-4 z-[1000] bg-white rounded-lg shadow-lg p-4 space-y-4 w-80">
        {/* Selection Mode Toggle */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Mode sélection</span>
          <button
            onClick={() => {
              setIsSelectionMode(!isSelectionMode);
              if (!isSelectionMode) {
                setSelectedCameras(new Set());
                setShowSelectionList(false);
              }
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full ${
              isSelectionMode ? 'bg-blue-600' : 'bg-gray-200'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              isSelectionMode ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>

        {/* Selected Cameras List */}
        {isSelectionMode && selectedCameras.size > 0 && showSelectionList && (
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
            <div className="p-3 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-sm font-medium text-gray-700">
                Caméras sélectionnées ({selectedCameras.size})
              </h3>
              <button
                onClick={() => setShowSelectionList(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            <div className="max-h-60 overflow-y-auto">
              {Array.from(selectedCameras).map(cameraId => {
                const camera = cameras.find(c => c.id === cameraId);
                if (!camera) return null;
                return (
                  <div key={cameraId} className="p-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-gray-900">{fixEncoding(camera.name)}</h4>
                        <p className="text-xs text-gray-500">IP: {camera.ip_address}</p>
                        {camera.latitude && camera.longitude && (
                          <p className="text-xs text-gray-500">
                            Position: {camera.latitude}, {camera.longitude}
                          </p>
                        )}
                        <div className="mt-2 flex items-center gap-2">
                          <button
                            onClick={() => handleCameraPing(camera.id)}
                            disabled={cameraPingStatuses[camera.id]?.status === 'loading'}
                            className={`px-2 py-1 rounded text-xs text-white ${
                              cameraPingStatuses[camera.id]?.status === 'loading'
                                ? 'bg-gray-400'
                                : cameraPingStatuses[camera.id]?.status === 'online'
                                ? 'bg-green-500'
                                : cameraPingStatuses[camera.id]?.status === 'offline'
                                ? 'bg-red-500'
                                : 'bg-blue-500'
                            }`}
                          >
                            {cameraPingStatuses[camera.id]?.status === 'loading' ? (
                              <div className="animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent"></div>
                            ) : cameraPingStatuses[camera.id]?.status === 'online' ? (
                              <Wifi className="w-3 h-3" />
                            ) : cameraPingStatuses[camera.id]?.status === 'offline' ? (
                              <WifiOff className="w-3 h-3" />
                            ) : (
                              'Ping'
                            )}
                          </button>
                          <button
                            onClick={() => handleRemoveFromSelection(camera.id)}
                            className="px-2 py-1 rounded text-xs text-white bg-red-500 hover:bg-red-600"
                          >
                            Retirer
                          </button>
                        </div>
                      </div>
                      <div className="ml-2">
                        <button
                          onClick={() => {
                            if (mapRef.current) {
                              const lat = parseFloat(camera.latitude || '0');
                              const lng = parseFloat(camera.longitude || '0');
                              if (!isNaN(lat) && !isNaN(lng)) {
                                mapRef.current.setView([lat, lng], 13);
                              }
                            }
                          }}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="p-3 bg-gray-50 border-t border-gray-200">
              <div className="flex space-x-2">
                <button
                  onClick={handlePingSelected}
                  disabled={isPingingAll}
                  className={`flex-1 px-3 py-1.5 rounded-md text-sm text-white ${
                    isPingingAll ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'
                  }`}
                >
                  {isPingingAll ? 'Ping en cours...' : 'Ping sélection'}
                </button>
                <button
                  onClick={handleDeleteSelected}
                  disabled={isDeleting}
                  className={`flex-1 px-3 py-1.5 rounded-md text-sm text-white ${
                    isDeleting ? 'bg-red-400' : 'bg-red-500 hover:bg-red-600'
                  }`}
                >
                  {isDeleting ? 'Suppression...' : 'Supprimer'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Selected Cameras Summary */}
        {isSelectionMode && selectedCameras.size > 0 && !showSelectionList && (
          <div className="bg-blue-50 p-3 rounded-md space-y-2">
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium text-blue-700">
                {selectedCameras.size} caméra(s) sélectionnée(s)
              </div>
              <button
                onClick={() => setShowSelectionList(true)}
                className="text-blue-600 hover:text-blue-800 text-sm"
              >
                Voir la liste
              </button>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handlePingSelected}
                disabled={isPingingAll}
                className={`flex-1 px-3 py-1.5 rounded-md text-sm text-white ${
                  isPingingAll ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {isPingingAll ? 'Ping en cours...' : 'Ping sélection'}
              </button>
              <button
                onClick={handleDeleteSelected}
                disabled={isDeleting}
                className={`flex-1 px-3 py-1.5 rounded-md text-sm text-white ${
                  isDeleting ? 'bg-red-400' : 'bg-red-500 hover:bg-red-600'
                }`}
              >
                {isDeleting ? 'Suppression...' : 'Supprimer'}
              </button>
            </div>
          </div>
        )}

        {/* Add Camera Button */}
        <button
          onClick={() => {
            if (!isAuthenticated) {
              handleAuthError('Veuillez vous connecter pour ajouter une caméra');
              return;
            }
            setShowAddForm(true);
          }}
          className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
        >
          <Plus className="h-5 w-5 mr-2" />
          Ajouter une Caméra
        </button>

        {/* Type de recherche */}
        <div className="flex space-x-2 mb-2">
          <button
            onClick={() => setSearchType('all')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm ${
              searchType === 'all'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Tout
          </button>
          <button
            onClick={() => setSearchType('cameras')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm ${
              searchType === 'cameras'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Caméras
          </button>
        </div>

        {/* Barre de recherche */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Rechercher une caméra..."
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>

        {/* Filtres de statut */}
        <div className="flex space-x-2">
          <button
            onClick={() => setFilterStatus('all')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm ${
              filterStatus === 'all'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Tous
          </button>
          <button
            onClick={() => setFilterStatus('online')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm ${
              filterStatus === 'online'
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            En ligne
          </button>
          <button
            onClick={() => setFilterStatus('offline')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm ${
              filterStatus === 'offline'
                ? 'bg-red-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Hors ligne
          </button>
        </div>

        {/* Statistiques */}
        <div className="bg-gray-50 rounded-md p-3">
          <div className="text-sm font-medium text-gray-700 mb-2">Statistiques</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex justify-between">
              <span>Caméras:</span>
              <span className="font-semibold">{filteredCameras.length}</span>
            </div>
            <div className="flex justify-between">
              <span>En ligne:</span>
              <span className="text-green-500 font-semibold">
                {Object.values(cameraPingStatuses).filter(s => s.status === 'online').length}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Hors ligne:</span>
              <span className="text-red-500 font-semibold">
                {Object.values(cameraPingStatuses).filter(s => s.status === 'offline' || s.status === 'error').length}
              </span>
          </div>
        </div>

          {/* Ping All Button */}
          <button
            onClick={handlePingAll}
            disabled={isPingingAll}
            className={`w-full px-4 py-2 rounded-md text-white text-sm flex items-center justify-center gap-2 ${
              isPingingAll ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'
            }`}
          >
            {isPingingAll ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Ping en cours...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 4c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                </svg>
                Tester toutes les caméras
              </>
            )}
          </button>
        </div>
      </div>

      <MapContainer
        center={[31.7917, -7.0926]}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        ref={mapRef}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        {marocData && (
          <GeoJSON 
            data={marocData} 
            style={{
              color: '#2563eb',
              weight: 2,
              fillOpacity: 0.1,
              fillColor: '#3b82f6'
            }}
            onEachFeature={(feature, layer) => {
              layer.bindPopup(`
                <div class="p-2">
                  <h3 class="font-semibold text-lg">${feature.properties.ADMIN}</h3>
                  <p class="text-sm">Population: ${feature.properties.POP_EST?.toLocaleString() || 'N/A'}</p>
                </div>
              `);
            }}
          />
        )}
        <MarkerClusterGroup
          chunkedLoading
          maxClusterRadius={50}
          spiderfyOnMaxZoom={true}
          showCoverageOnHover={false}
          zoomToBoundsOnClick={true}
          iconCreateFunction={(cluster: Cluster) => {
            return L.divIcon({
              html: `<div class="bg-blue-500 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">${cluster.getChildCount()}</div>`,
              className: 'custom-cluster-icon',
              iconSize: L.point(32, 32)
            });
          }}
        >
          {filteredCameras.map((camera) => {
            if (camera.latitude && camera.longitude) {
              const lat = parseFloat(camera.latitude);
              const lng = parseFloat(camera.longitude);
              if (!isNaN(lat) && !isNaN(lng)) {
                const isSelected = selectedCameras.has(camera.id);
                return (
                  <Marker
                    key={camera.id}
                    position={[lat, lng]}
                    icon={getCameraIcon(camera.id)}
                    riseOnHover={true}
                    eventHandlers={{
                      click: () => handleCameraSelect(camera.id)
                    }}
                  >
                    <Popup>
                      <div className={`p-2 min-w-[200px] ${isSelected ? 'bg-blue-50' : ''}`}>
                        <h3 className="font-semibold text-lg">{fixEncoding(camera.name)}</h3>
                        <p className="text-sm">IP: {camera.ip_address}</p>
                        <p className="text-sm">Latitude: {lat}</p>
                        <p className="text-sm">Longitude: {lng}</p>
                        <div className="mt-2 flex items-center justify-between">
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              handleCameraPing(camera.id);
                            }}
                            className={`px-3 py-1 rounded-md text-white text-sm flex items-center gap-2 ${
                              cameraPingStatuses[camera.id]?.status === 'loading'
                                ? 'bg-gray-400'
                                : cameraPingStatuses[camera.id]?.status === 'online'
                                ? 'bg-green-500'
                                : cameraPingStatuses[camera.id]?.status === 'offline'
                                ? 'bg-red-500'
                                : 'bg-blue-500'
                            }`}
                            disabled={cameraPingStatuses[camera.id]?.status === 'loading'}
                          >
                            {cameraPingStatuses[camera.id]?.status === 'loading' ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                            ) : cameraPingStatuses[camera.id]?.status === 'online' ? (
                              <Wifi className="w-4 h-4" />
                            ) : cameraPingStatuses[camera.id]?.status === 'offline' ? (
                              <WifiOff className="w-4 h-4" />
                            ) : (
                              'Ping'
                            )}
                            {cameraPingStatuses[camera.id]?.status === 'online' && cameraPingStatuses[camera.id].responseTime && 
                              <span>{Math.round(cameraPingStatuses[camera.id].responseTime || 0)}ms</span>
                            }
                          </button>
                          {!isSelectionMode && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                                setCameraToDelete(camera);
                            }}
                            className="px-3 py-1 rounded-md text-white text-sm bg-red-500 hover:bg-red-600 flex items-center gap-2"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            Supprimer
                          </button>
                          )}
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              }
            }
            return null;
          })}
        </MarkerClusterGroup>
      </MapContainer>

      {showAddForm && (
        <>
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-[1000]"
            onClick={() => setShowAddForm(false)}
          />
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[1001]">
            <AddCameraForm
              onClose={() => setShowAddForm(false)}
              position={clickPosition}
              onSuccess={(message: string) => {
                setSuccess(message);
                setShowAddForm(false);
              }}
              onError={(message: string) => {
                setError(message);
                setShowAddForm(false);
              }}
              onCamerasUpdate={(updatedCameras: Camera[]) => {
                setCameras(updatedCameras);
              }}
            />
          </div>
        </>
      )}

      {/* Delete Confirmation Modal */}
      {cameraToDelete && (
        <>
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-[1000]"
            onClick={() => !isDeleting && setCameraToDelete(null)}
          />
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[1001] bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Confirmer la suppression
            </h3>
            <div className="mb-4">
              <p className="text-gray-600 mb-2">
                Êtes-vous sûr de vouloir supprimer la caméra suivante ?
              </p>
              <div className="bg-gray-50 p-3 rounded-md">
                <p className="font-medium">{fixEncoding(cameraToDelete.name)}</p>
                <p className="text-sm text-gray-500">IP: {cameraToDelete.ip_address}</p>
                {cameraToDelete.latitude && cameraToDelete.longitude && (
                  <p className="text-sm text-gray-500">
                    Position: {cameraToDelete.latitude}, {cameraToDelete.longitude}
                  </p>
                )}
              </div>
            </div>
            <div className="flex justify-end space-x-3">
            <button
                onClick={() => setCameraToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            >
                Annuler
            </button>
              <button
                onClick={() => handleDeleteCamera(cameraToDelete)}
                disabled={isDeleting}
                className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 ${
                  isDeleting ? 'bg-red-400' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {isDeleting ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    Suppression...
                  </div>
                ) : (
                  'Supprimer'
                )}
              </button>
        </div>
          </div>
        </>
      )}

      {error && (
        <div className="absolute bottom-4 left-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Erreur! </strong>
          <span className="block sm:inline">{error}</span>
          {error.includes('Trop de requêtes') && (
            <button
              className="ml-4 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => window.location.reload()}
            >
              Réessayer
            </button>
          )}
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setError(null)}
          >
            <svg className="fill-current h-6 w-6 text-red-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
              <title>Close</title>
              <path d="M14.348 14.849a1 1 0 0 1-1.697 0L10 11.819l-2.651 3.029a1 1 0 1 0 1.697 1.414L10 13.515l2.651-3.029a1 1 0 0 1 1.697-1.697L10 11.819l2.651-3.031a1 1 0 1 0 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/>
            </svg>
          </button>
        </div>
      )}

      {success && (
        <div className="absolute bottom-4 left-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Succès! </strong>
          <span className="block sm:inline">{success}</span>
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setSuccess(null)}
          >
            <svg className="fill-current h-6 w-6 text-green-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
              <title>Close</title>
              <path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1 1 0 1 0 1.697 1.697L10 13.515l2.651-3.029a1 1 0 0 0-1.697-1.697L10 11.819l2.651-3.031a1 1 0 1 0 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};

export default WorldMap;

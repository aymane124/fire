import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { marocData } from '../data/maroc_with_sahara';
import axios from 'axios';
import { API_URL } from '../config.ts';
import { useAuth } from '../contexts/AuthContext';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Wifi, WifiOff, Network } from 'lucide-react';
import debounce from 'lodash/debounce';

// Fix for default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface DataCenter {
  id: string;
  name: string;
  description: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  region: string;
  status: string;
  last_ping?: number | null;
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
  attributes_schema: any;
  firewalls?: Firewall[];
}

interface FirewallPingStatus {
  status: 'idle' | 'loading' | 'online' | 'offline' | 'error';
  responseTime: number | null;
  lastUpdate?: number;
  error?: string;
}

// New interface for ping API response
interface PingApiResponse {
  status: 'success' | 'error' | 'online' | 'offline';
  response_time: number | null;
  message?: string;
}

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

// Custom icons for datacenters
const dataCenterIcon = L.divIcon({
  className: 'custom-datacenter-icon',
  html: `
    <svg fill="#000000" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	   viewBox="0 0 60 60" xml:space="preserve">
      <g>
        <g>
          <path d="M2,34H0v25c0,0.6,0.4,1,1,1h26v-2H2V34z"/>
          <path d="M58,58H33v2h26c0.6,0,1-0.4,1-1V34h-2V58z"/>
          <path d="M59,0H33v2h25v6H36v2h22v18h2V1C60,0.4,59.6,0,59,0z"/>
          <path d="M2,10h22V8H2V2h25V0H1C0.4,0,0,0.4,0,1v27h2V10z"/>
          <rect x="4" y="4" width="2" height="2"/>
          <rect x="8" y="4" width="2" height="2"/>
          <rect x="12" y="4" width="2" height="2"/>
          <rect x="52" y="4" width="4" height="2"/>
          <path d="M16,16v10v10v10c0,0.6,0.4,1,1,1h26c0.6,0,1-0.4,1-1V36V26V16c0-0.6-0.4-1-1-1H17C16.4,15,16,15.4,16,16z M42,35H18v-8h24
            V35z M42,45H18v-8h24V45z M18,17h24v8H18V17z"/>
          <rect x="20" y="19" width="2" height="4"/>
          <rect x="24" y="19" width="2" height="4"/>
          <rect x="28" y="19" width="2" height="4"/>
          <rect x="20" y="29" width="2" height="4"/>
          <rect x="24" y="29" width="2" height="4"/>
          <rect x="28" y="29" width="2" height="4"/>
          <rect x="34" y="20" width="2" height="2"/>
          <rect x="38" y="20" width="2" height="2"/>
          <rect x="34" y="30" width="2" height="2"/>
          <rect x="38" y="30" width="2" height="2"/>
          <rect x="29" y="40" width="6" height="2"/>
          <rect x="37" y="40" width="2" height="2"/>
          <rect x="25" y="40" width="2" height="2"/>
          <rect x="21" y="40" width="2" height="2"/>
        </g>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

const dataCenterRedIcon = L.divIcon({
  className: 'custom-datacenter-icon',
  html: `
    <svg fill="#ef4444" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	   viewBox="0 0 60 60" xml:space="preserve">
      <g>
        <g>
          <path d="M2,34H0v25c0,0.6,0.4,1,1,1h26v-2H2V34z"/>
          <path d="M58,58H33v2h26c0.6,0,1-0.4,1-1V34h-2V58z"/>
          <path d="M59,0H33v2h25v6H36v2h22v18h2V1C60,0.4,59.6,0,59,0z"/>
          <path d="M2,10h22V8H2V2h25V0H1C0.4,0,0,0.4,0,1v27h2V10z"/>
          <rect x="4" y="4" width="2" height="2"/>
          <rect x="8" y="4" width="2" height="2"/>
          <rect x="12" y="4" width="2" height="2"/>
          <rect x="52" y="4" width="4" height="2"/>
          <path d="M16,16v10v10v10c0,0.6,0.4,1,1,1h26c0.6,0,1-0.4,1-1V36V26V16c0-0.6-0.4-1-1-1H17C16.4,15,16,15.4,16,16z M42,35H18v-8h24
            V35z M42,45H18v-8h24V45z M18,17h24v8H18V17z"/>
          <rect x="20" y="19" width="2" height="4"/>
          <rect x="24" y="19" width="2" height="4"/>
          <rect x="28" y="19" width="2" height="4"/>
          <rect x="20" y="29" width="2" height="4"/>
          <rect x="24" y="29" width="2" height="4"/>
          <rect x="28" y="29" width="2" height="4"/>
          <rect x="34" y="20" width="2" height="2"/>
          <rect x="38" y="20" width="2" height="2"/>
          <rect x="34" y="30" width="2" height="2"/>
          <rect x="38" y="30" width="2" height="2"/>
          <rect x="29" y="40" width="6" height="2"/>
          <rect x="37" y="40" width="2" height="2"/>
          <rect x="25" y="40" width="2" height="2"/>
          <rect x="21" y="40" width="2" height="2"/>
        </g>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

const dataCenterOrangeIcon = L.divIcon({
  className: 'custom-datacenter-icon',
  html: `
    <svg fill="#f97316" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	   viewBox="0 0 60 60" xml:space="preserve">
      <g>
        <g>
          <path d="M2,34H0v25c0,0.6,0.4,1,1,1h26v-2H2V34z"/>
          <path d="M58,58H33v2h26c0.6,0,1-0.4,1-1V34h-2V58z"/>
          <path d="M59,0H33v2h25v6H36v2h22v18h2V1C60,0.4,59.6,0,59,0z"/>
          <path d="M2,10h22V8H2V2h25V0H1C0.4,0,0,0.4,0,1v27h2V10z"/>
          <rect x="4" y="4" width="2" height="2"/>
          <rect x="8" y="4" width="2" height="2"/>
          <rect x="12" y="4" width="2" height="2"/>
          <rect x="52" y="4" width="4" height="2"/>
          <path d="M16,16v10v10v10c0,0.6,0.4,1,1,1h26c0.6,0,1-0.4,1-1V36V26V16c0-0.6-0.4-1-1-1H17C16.4,15,16,15.4,16,16z M42,35H18v-8h24
            V35z M42,45H18v-8h24V45z M18,17h24v8H18V17z"/>
          <rect x="20" y="19" width="2" height="4"/>
          <rect x="24" y="19" width="2" height="4"/>
          <rect x="28" y="19" width="2" height="4"/>
          <rect x="20" y="29" width="2" height="4"/>
          <rect x="24" y="29" width="2" height="4"/>
          <rect x="28" y="29" width="2" height="4"/>
          <rect x="34" y="20" width="2" height="2"/>
          <rect x="38" y="20" width="2" height="2"/>
          <rect x="34" y="30" width="2" height="2"/>
          <rect x="38" y="30" width="2" height="2"/>
          <rect x="29" y="40" width="6" height="2"/>
          <rect x="37" y="40" width="2" height="2"/>
          <rect x="25" y="40" width="2" height="2"/>
          <rect x="21" y="40" width="2" height="2"/>
        </g>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

// Icône pour les datacenters (vert - tous les firewalls sont en ligne) - Added from WorldMap.tsx
const dataCenterGreenIcon = L.divIcon({
  className: 'custom-datacenter-icon',
  html: `
    <svg fill="#22c55e" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	   viewBox="0 0 60 60" xml:space="preserve">
      <g>
        <g>
          <path d="M2,34H0v25c0,0.6,0.4,1,1,1h26v-2H2V34z"/>
          <path d="M58,58H33v2h26c0.6,0,1-0.4,1-1V34h-2V58z"/>
          <path d="M59,0H33v2h25v6H36v2h22v18h2V1C60,0.4,59.6,0,59,0z"/>
          <path d="M2,10h22V8H2V2h25V0H1C0.4,0,0,0.4,0,1v27h2V10z"/>
          <rect x="4" y="4" width="2" height="2"/>
          <rect x="8" y="4" width="2" height="2"/>
          <rect x="12" y="4" width="2" height="2"/>
          <rect x="52" y="4" width="4" height="2"/>
          <path d="M16,16v10v10v10c0,0.6,0.4,1,1,1h26c0.6,0,1-0.4,1-1V36V26V16c0-0.6-0.4-1-1-1H17C16.4,15,16,15.4,16,16z M42,35H18v-8h24
            V35z M42,45H18v-8h24V45z M18,17h24v8H18V17z"/>
          <rect x="20" y="19" width="2" height="4"/>
          <rect x="24" y="19" width="2" height="4"/>
          <rect x="28" y="19" width="2" height="4"/>
          <rect x="20" y="29" width="2" height="4"/>
          <rect x="24" y="29" width="2" height="4"/>
          <rect x="28" y="29" width="2" height="4"/>
          <rect x="34" y="20" width="2" height="2"/>
          <rect x="38" y="20" width="2" height="2"/>
          <rect x="34" y="30" width="2" height="2"/>
          <rect x="38" y="30" width="2" height="2"/>
          <rect x="29" y="40" width="6" height="2"/>
          <rect x="37" y="40" width="2" height="2"/>
          <rect x="25" y="40" width="2" height="2"/>
          <rect x="21" y="40" width="2" height="2"/>
        </g>
      </g>
    </svg>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

// Add styles for the datacenter and popup (from WorldMap.tsx)
const customMapStyles = `
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

const NetworkMap: React.FC = () => {
  const [dataCenters, setDataCenters] = useState<DataCenter[]>([]);
  const [firewallTypes, setFirewallTypes] = useState<Record<string, FirewallType[]>>({});
  const [firewallStatuses, setFirewallStatuses] = useState<Record<string, FirewallPingStatus>>({});
  const [loadingFirewalls, setLoadingFirewalls] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const refreshTimeoutRef = useRef<number | null>(null);
  const { token } = useAuth();

  // Add states for search and filter (from WorldMap.tsx logic)
  const [filterStatus, setFilterStatus] = useState<'all' | 'online' | 'offline'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  // Add state for pinging all firewalls
  const [isPingingAll, setIsPingingAll] = useState(false);

  // Add openSections state for accordion functionality (from WorldMap.tsx)
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  // Add toggleSection function for accordion functionality (from WorldMap.tsx)
  const toggleSection = (typeId: string) => {
    setOpenSections(prev => ({
      ...prev,
      [typeId]: !prev[typeId]
    }));
  };

  // Inject the styles into the document head (moved inside component)
  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.innerText = customMapStyles;
    document.head.appendChild(styleSheet);

    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  // Handle authentication errors
  const handleAuthError = (message: string) => {
    setError(message);
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
    refreshTimeoutRef.current = window.setTimeout(() => {
      window.location.reload();
    }, 3000);
  };

  // Initial authentication check
  useEffect(() => {
    console.log('Starting authentication check...');
    const token = localStorage.getItem('token');
    if (!token) {
      console.log('No token found');
      handleAuthError('Please login to access this page');
      return;
    }
    console.log('Token found, verifying...');

    // Verify token validity
    api.get('/datacenters/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    }).then(() => {
      console.log('Token verified successfully');
      setIsInitialized(true);
    }).catch((error) => {
      console.error('Token verification failed:', error);
      if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
          handleAuthError('Session expired. Please login again.');
        localStorage.removeItem('token');
        window.location.href = '/login';
      } else {
          setError('Server connection error');
        }
      }
    });

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

  // Initialize map settings
  useEffect(() => {
    console.log('Map initialization effect running, isInitialized:', isInitialized);
    if (!isInitialized) return;
    console.log('Setting default marker icon');
    L.Marker.prototype.options.icon = dataCenterIcon;
  }, [isInitialized]);

  // Fetch datacenters
  useEffect(() => {
    console.log('Fetch datacenters effect running, isInitialized:', isInitialized);
    if (!isInitialized) return;

    const fetchDataCenters = async () => {
      try {
        console.log('Starting to fetch datacenters...');
        const token = localStorage.getItem('token');
        if (!token) {
          console.log('No token found during fetch');
          setError('Token not found. Please login again.');
          return;
        }

        const response = await api.get('/datacenters/', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            }
          });
          
        console.log('Raw API response:', response.data);
          if (response.data.results) {
          console.log('Setting datacenters:', response.data.results);
          setDataCenters(response.data.results);
          
          // After setting datacenters, fetch firewall types for each datacenter
          response.data.results.forEach((datacenter: DataCenter) => {
            fetchFirewallTypes(datacenter.id);
          });

        } else {
          console.log('No results in API response');
          setDataCenters([]);
        }
      } catch (error) {
        console.error('Error fetching datacenters:', error);
        if (axios.isAxiosError(error)) {
          if (error.response?.status === 401) {
            setError('Session expired. Please login again.');
            localStorage.removeItem('token');
            window.location.href = '/login';
          } else {
            setError('Error loading datacenters');
          }
        }
        setDataCenters([]);
      }
    };

    fetchDataCenters();
  }, [isInitialized]);

  // Debug log for datacenters state changes
  useEffect(() => {
    console.log('Datacenters state updated:', dataCenters);
  }, [dataCenters]);

  const fetchFirewallTypes = async (datacenterId: string) => {
    try {
      setLoadingFirewalls(prev => ({ ...prev, [datacenterId]: true }));
      const token = localStorage.getItem('token'); // Ensure token is available
      if (!token) {
        setError('Token not found. Please login again.');
      return;
    }

      // Fetch the full hierarchy to get nested firewalls, similar to WorldMap.tsx
      const response = await api.get(`/datacenters/hierarchy/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      // console.log(`Raw API response for firewall types (datacenterId: ${datacenterId}):`, response.data);

      if (response.data) {
        // Find the specific datacenter in the hierarchy
        const datacenter = response.data.find((dc: any) => dc.id === datacenterId);
        if (datacenter && datacenter.firewall_types) {
          console.log(`Datacenter found in hierarchy (ID: ${datacenterId}):`, datacenter);
          setFirewallTypes(prev => ({
        ...prev,
            [datacenterId]: datacenter.firewall_types
          }));
        } else {
          console.warn(`Datacenter with ID ${datacenterId} not found or has no firewall types in hierarchy.`, response.data);
          setFirewallTypes(prev => ({ ...prev, [datacenterId]: [] }));
        }
      }
    } catch (error) {
      console.error('Error fetching firewall types:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          setError('Session expired. Please login again.');
          localStorage.removeItem('token');
          window.location.href = '/login';
        } else {
          setError('Error fetching firewall types');
        }
      } else {
        setError('Error fetching firewall types');
      }
    } finally {
      setLoadingFirewalls(prev => ({ ...prev, [datacenterId]: false }));
    }
  };

  // Memoize filtered datacenters
  const filteredDataCenters = useMemo(() => {
    return dataCenters.filter(datacenter => {
      if (filterStatus === 'all') return true;
      if (filterStatus === 'online') return datacenter.is_active;
      if (filterStatus === 'offline') return !datacenter.is_active;
      return false;
    });
  }, [dataCenters, filterStatus]);

  // Add this function to calculate datacenter status
  const calculateDatacenterStatus = (datacenterId: string, firewallTypes: Record<string, FirewallType[]>, firewallStatuses: Record<string, FirewallPingStatus>) => {
    const datacenterFirewallTypes = firewallTypes[datacenterId] || [];
    let totalFirewalls = 0;
    let onlineFirewalls = 0;
    let hasExpiredStatus = false;

    datacenterFirewallTypes.forEach(type => {
      type.firewalls?.forEach(firewall => {
        const status = firewallStatuses[firewall.id];
        if (status && !isStatusExpired(status.lastUpdate)) {
          totalFirewalls++;
          if (status.status === 'online') {
            onlineFirewalls++;
          }
        } else {
          hasExpiredStatus = true;
        }
      });
    });

    // If no firewalls or all statuses are expired, return 'unknown'
    if (totalFirewalls === 0 || hasExpiredStatus) {
      return 'unknown';
    }

    // If all firewalls are online, return 'online'
    if (onlineFirewalls === totalFirewalls) {
      return 'online';
    }

    // If no firewalls are online, return 'offline'
    if (onlineFirewalls === 0) {
      return 'offline';
    }

    // If some firewalls are online and some are offline, return 'partial'
    return 'partial';
  };

  // Update the getDataCenterIcon function to use the dynamic status
  const getDataCenterIcon = useCallback((datacenterId: string) => {
    const status = calculateDatacenterStatus(datacenterId, firewallTypes, firewallStatuses);
    
    switch (status) {
      case 'online':
        return dataCenterGreenIcon;
      case 'offline':
        return dataCenterRedIcon;
      case 'partial':
        return dataCenterOrangeIcon;
      default:
        return dataCenterIcon;
    }
  }, [firewallTypes, firewallStatuses]);

  // Memoize the handleMarkerClick function
  const handleMarkerClick = useCallback((datacenter: DataCenter) => {
    fetchFirewallTypes(datacenter.id);
  }, [fetchFirewallTypes]);

  // Memoize the handleFirewallPing function
  const handleFirewallPing = useCallback(async (firewallId: string) => {
    if (firewallStatuses[firewallId]?.status === 'loading') {
      return;
    }

    try {
      setFirewallStatuses(prev => ({
        ...prev,
        [firewallId]: { status: 'loading', responseTime: null }
      }));

      const response = await api.post<PingApiResponse>(`/firewalls/${firewallId}/ping/`);
      console.log(`Ping response for firewall ${firewallId}:`, response.data);
      
      if (!response.data) {
        throw new Error('Invalid response from server');
      }

      // Debug log for response data
      console.log('Response data details:', {
        status: response.data.status,
        response_time: response.data.response_time,
        message: response.data.message
      });

      // Handle error status from the API
      if (response.data.status === 'error') {
        console.log('Error status detected, setting firewall to offline');
        setFirewallStatuses(prev => ({
          ...prev,
          [firewallId]: {
            status: 'offline',
            responseTime: null,
            lastUpdate: Date.now(),
            error: response.data.message || 'Connection failed'
          }
        }));
        return;
      }

      // Determine status based on the API response
      const status: 'online' | 'offline' = response.data.status === 'online' ? 'online' : 'offline';
      console.log('Status determination:', {
        firewallId,
        status,
        responseTime: response.data.response_time
      });
      
      setFirewallStatuses(prev => ({
        ...prev,
        [firewallId]: {
          status,
          responseTime: response.data.response_time,
          lastUpdate: Date.now(),
          error: response.data.message || undefined
        }
      }));
    } catch (error) {
      console.error(`Error pinging firewall ${firewallId}:`, error);
      setFirewallStatuses(prev => ({
        ...prev,
        [firewallId]: { 
          status: 'offline', 
          responseTime: null,
          lastUpdate: Date.now(),
          error: error instanceof Error ? error.message : 'Connection failed'
        }
      }));
    }
  }, [firewallStatuses]);

  // Memoize the handlePingAllFirewalls function
  const handlePingAllFirewalls = useCallback(async () => {
    if (!token) {
      setError('Please login to perform this action.');
      return;
    }
    setIsPingingAll(true);
    try {
      const response = await api.post('/firewalls/ping_all/');
      console.log('Ping all response:', response.data);

      if (response.data && response.data.results) {
        const newStatuses: Record<string, FirewallPingStatus> = {};
        response.data.results.forEach((result: { 
          id: string; 
          status: string; 
          response_time: number | null;
          message?: string;
        }) => {
          newStatuses[result.id] = {
            status: result.status === 'online' ? 'online' : 'offline',
            responseTime: result.response_time,
            lastUpdate: Date.now(),
            error: result.message
          };
        });
        setFirewallStatuses(prev => ({ ...prev, ...newStatuses }));
        
        // Log statistics
        console.log('Ping statistics:', {
          total: response.data.total,
          online: response.data.online,
          offline: response.data.offline,
          errors: response.data.errors
        });
      }
    } catch (error) {
      console.error('Error pinging all firewalls:', error);
      setError('Error pinging all firewalls');
    } finally {
      setIsPingingAll(false);
    }
  }, [token]);

  const isStatusExpired = (lastUpdate: number | undefined) => {
    if (!lastUpdate) return true;
    const now = Date.now();
    return now - lastUpdate > 5 * 60 * 1000; // 5 minutes
  };

  // Type for cluster (from WorldMap.tsx)
  interface Cluster {
    getChildCount(): number;
  }

  // Update the markers rendering to use the dynamic status
  const markers = useMemo(() => {
    return filteredDataCenters.map((datacenter) => {
      if (!datacenter.latitude || !datacenter.longitude) {
        return null;
      }

      const lat = parseFloat(datacenter.latitude.toString());
      const lng = parseFloat(datacenter.longitude.toString());
      
      if (isNaN(lat) || isNaN(lng)) {
        return null;
      }

      // Calculate dynamic status
      const status = calculateDatacenterStatus(datacenter.id, firewallTypes, firewallStatuses);
      
      return (
        <Marker
          key={datacenter.id}
          position={[lat, lng]}
          icon={getDataCenterIcon(datacenter.id)}
          eventHandlers={{
            click: () => handleMarkerClick(datacenter)
          }}
        >
          <Popup>
            <div className="datacenter-popup-content">
              {/* En-tête du datacenter */}
              <div className="border-b border-gray-200 pb-3 mb-4">
                <h3 className="font-semibold text-lg text-purple-700 flex items-center gap-2">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.5L20 8v8l-8 4-8-4V8l8-3.5z" fill="currentColor"/>
                  </svg>
                  {datacenter.name}
                </h3>
                {datacenter.location && (
                  <p className="text-sm text-gray-600 mt-1">
                    <span className="font-medium">Adresse:</span> {datacenter.location}
                  </p>
                )}
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    status === 'online' 
                      ? 'bg-green-100 text-green-800'
                      : status === 'offline'
                      ? 'bg-red-100 text-red-800'
                      : status === 'partial'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {status === 'online' ? 'Actif' : 
                     status === 'offline' ? 'Inactif' :
                     status === 'partial' ? 'Partiellement Actif' :
                     'Statut Inconnu'}
                  </span>
                </div>
              </div>
              
              {/* Section des types de firewall */}
              <div className="mt-4">
                <h4 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.67-3.13 8.96-7 10.69-3.87-1.73-7-6.02-7-10.69v-4.7l7-3.12z" fill="currentColor"/>
                  </svg>
                  Types de Firewall
                </h4>
                {loadingFirewalls[datacenter.id] ? (
                  <div className="flex items-center justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-purple-500 border-t-transparent"></div>
                    <span className="ml-2 text-sm text-gray-500">Chargement des firewalls...</span>
                  </div>
                ) : firewallTypes[datacenter.id] ? (
                  <div className="space-y-3">
                    {firewallTypes[datacenter.id].map((type) => (
                      <div key={type.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                        {/* En-tête du type de firewall avec accordéon */}
                        <div 
                          className="bg-purple-50 p-3 border-b border-purple-100 cursor-pointer hover:bg-purple-100 transition-colors"
                          onClick={() => toggleSection(type.id)}
                        >
                          <div className="font-medium text-sm text-purple-700 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.67-3.13 8.96-7 10.69-3.87-1.73-7-6.02-7-10.69v-4.7l7-3.12z" fill="currentColor"/>
                              </svg>
                              {type.name}
                            </div>
                            <svg 
                              className={`w-4 h-4 transform transition-transform ${openSections[type.id] ? 'rotate-180' : ''}`}
                              viewBox="0 0 24 24" 
                              fill="none" 
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          </div>
                        </div>
                        
                        {/* Liste des firewalls */}
                        {openSections[type.id] && (
                          <div className="p-3">
                            {type.firewalls && type.firewalls.length > 0 ? (
                              <div className="space-y-2">
                                {type.firewalls.map((firewall) => (
                                  <div key={firewall.id} className="bg-gray-50 rounded-md p-3 hover:bg-gray-100 transition-colors">
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3">
                                        <div className="bg-white p-2 rounded-md shadow-sm">
                                          <svg className="w-4 h-4 text-purple-600" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.67-3.13 8.96-7 10.69-3.87-1.73-7-6.02-7-10.69v-4.7l7-3.12z" fill="currentColor"/>
                                          </svg>
                                        </div>
                                        <div>
                                          <div className="font-medium text-sm">{firewall.name}</div>
                                          <div className="text-xs text-gray-500 mt-1">{firewall.ip_address}</div>
                                        </div>
                                      </div>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleFirewallPing(firewall.id);
                                        }}
                                        className={`px-3 py-1.5 rounded-md text-white text-sm flex items-center gap-2 transition-colors ${
                                          firewallStatuses[firewall.id]?.status === 'loading'
                                            ? 'bg-gray-400'
                                            : firewallStatuses[firewall.id]?.status === 'online'
                                            ? 'bg-green-500 hover:bg-green-600'
                                            : firewallStatuses[firewall.id]?.status === 'offline'
                                            ? 'bg-red-500 hover:bg-red-600'
                                            : 'bg-blue-500 hover:bg-blue-600'
                                        }`}
                                        disabled={firewallStatuses[firewall.id]?.status === 'loading'}
                                        title={firewallStatuses[firewall.id]?.error || ''}
                                      >
                                        {firewallStatuses[firewall.id]?.status === 'loading' ? (
                                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                                        ) : firewallStatuses[firewall.id]?.status === 'online' ? (
                                          <Wifi className="w-4 h-4" />
                                        ) : firewallStatuses[firewall.id]?.status === 'offline' ? (
                                          <WifiOff className="w-4 h-4" />
                                        ) : (
                                          'Ping'
                                        )}
                                        {firewallStatuses[firewall.id]?.status === 'online' && firewallStatuses[firewall.id].responseTime && 
                                          <span>{Math.round(firewallStatuses[firewall.id].responseTime || 0)}ms</span>
                                        }
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-center text-sm text-gray-500">
                                Aucun firewall trouvé
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-sm text-gray-500">
                    Aucun type de firewall trouvé
                  </div>
                )}
              </div>
            </div>
          </Popup>
        </Marker>
      );
    });
  }, [filteredDataCenters, getDataCenterIcon, handleFirewallPing, handleMarkerClick, toggleSection, loadingFirewalls, firewallTypes, openSections, firewallStatuses]);

  return (
    <div className="h-screen w-full">
      {error && (
        <div className="absolute top-0 left-0 right-0 bg-red-500 text-white p-2 text-center z-50">
          {error}
          {error.includes('Trop de requêtes') && (
            <button
              className="ml-4 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => window.location.reload()}
            >
              Réessayer
            </button>
          )}
          <button
            className="ml-4 px-3 py-1 bg-gray-700 text-white rounded hover:bg-gray-800"
            onClick={() => setError(null)}
          >
            Fermer
          </button>
        </div>
      )}

      {/* Control Panel (Adapted from WorldMap.tsx) */}
      <div className="fixed top-4 right-4 z-[3000] bg-white rounded-lg shadow-lg p-4 space-y-4 w-80">
        {/* Barre de recherche */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Rechercher un datacenter..."
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
              <span>Datacenters:</span>
              <span className="font-semibold">{filteredDataCenters.length}</span>
            </div>
            <div className="flex justify-between">
              <span>En ligne:</span>
              <span className="text-green-500 font-semibold">
                {filteredDataCenters.filter(dc => {
                  const datacenterFirewallTypes = firewallTypes[dc.id] || [];
                  let totalFirewalls = 0;
                  let onlineFirewalls = 0;
                  datacenterFirewallTypes.forEach(type => {
                    type.firewalls?.forEach(firewall => {
                      const status = firewallStatuses[firewall.id];
                      if (status && !isStatusExpired(status.lastUpdate)) {
                        totalFirewalls++;
                        if (status.status === 'online') {
                          onlineFirewalls++;
                        }
                      }
                    });
                  });
                  // A datacenter is considered 'online' if all its firewalls are online (or no firewalls)
                  return dc.is_active && (totalFirewalls === 0 || onlineFirewalls === totalFirewalls);
                }).length}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Hors ligne:</span>
              <span className="text-red-500 font-semibold">
                {filteredDataCenters.filter(dc => {
                  const datacenterFirewallTypes = firewallTypes[dc.id] || [];
                  let totalFirewalls = 0;
                  let onlineFirewalls = 0;
                  datacenterFirewallTypes.forEach(type => {
                    type.firewalls?.forEach(firewall => {
                      const status = firewallStatuses[firewall.id];
                      if (status && !isStatusExpired(status.lastUpdate)) {
                        totalFirewalls++;
                        if (status.status === 'online') {
                          onlineFirewalls++;
                        }
                      }
                    });
                  });
                  // A datacenter is considered 'offline' if it's inactive or if some/all firewalls are offline/expired
                  return !dc.is_active || (totalFirewalls > 0 && onlineFirewalls < totalFirewalls);
                }).length}
              </span>
            </div>
          </div>
        </div>

        {/* Bouton de test (Adapted for firewalls only) */}
        <button
          onClick={handlePingAllFirewalls}
          disabled={isPingingAll}
          className={`w-full px-4 py-2 rounded-md text-white text-sm flex items-center justify-center gap-2 ${
            isPingingAll ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'
          }`}
        >
          {isPingingAll ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Test en cours...
            </>
          ) : (
            <>
              <Network className="w-4 h-4" />
              Tester tous les firewalls
            </>
          )}
        </button>
      </div>

      <MapContainer
        center={[31.7917, -7.0926]}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        minZoom={4}
        maxZoom={18}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        
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
          {markers}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
};

export default React.memo(NetworkMap);
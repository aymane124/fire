export interface Camera {
  id: string;
  name: string;
  ip_address: string;
  location: string;
  latitude: string;
  longitude: string;
  created_at: string;
  updated_at: string;
}

export interface CameraPingStatus {
  status: 'online' | 'offline' | 'error' | 'loading' | 'idle';
  responseTime: number | null;
  lastUpdate?: number;
} 
// API Configuration
export const API_URL = 'http://127.0.0.1:8000/api';

export const config = {
    isDevelopment: false,
    showDevTools: false
};

// Endpoints
export const API_ENDPOINTS = {
  CAMERAS: {
    LIST: '/cameras/cameras/',
    UPLOAD: '/cameras/cameras/upload_csv/',
    DETAIL: (id: string) => `/cameras/cameras/${id}/`,
    PING_ALL: '/cameras/cameras/ping_all/',
  },
  COMMANDS: {
    SAVE_CONFIG: '/command/commands/save_config/',
    EXECUTE: '/command/execute/',
  },
  AUTH: {
    LOGIN: '/auth/token/',
    REFRESH: '/auth/token/refresh/',
  },
  DATACENTERS: '/datacenters/',
  FIREWALL_TYPES: '/firewalls/firewall-type/',
  FIREWALLS: '/firewalls/firewall/'
};
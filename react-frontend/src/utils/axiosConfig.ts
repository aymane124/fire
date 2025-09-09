import axios from 'axios';
import { API_URL } from '../config';
import { getCookie } from './cookieUtils';
import { navigateTo } from './navigation';

// Namespaced storage keys to avoid collisions across projects
const ACCESS_KEY = 'firewallapp_token';
const REFRESH_KEY = 'firewallapp_refreshToken';

// Normalize tokens from legacy keys to namespaced keys (one-time migrate)
function migrateLegacyKeys(): void {
  try {
    const legacyAccess = localStorage.getItem('token');
    const legacyRefresh = localStorage.getItem('refreshToken');
    const nsAccess = localStorage.getItem(ACCESS_KEY);
    const nsRefresh = localStorage.getItem(REFRESH_KEY);
    if (!nsAccess && legacyAccess) {
      localStorage.setItem(ACCESS_KEY, legacyAccess);
      localStorage.removeItem('token');
    }
    if (!nsRefresh && legacyRefresh) {
      localStorage.setItem(REFRESH_KEY, legacyRefresh);
      localStorage.removeItem('refreshToken');
    }
  } catch {}
}

migrateLegacyKeys();

function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY) || null;
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY) || null;
}

function setAccessToken(token: string) {
  localStorage.setItem(ACCESS_KEY, token);
}

function setRefreshToken(token: string) {
  localStorage.setItem(REFRESH_KEY, token);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  // Clean any legacy remnants
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
}

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for CSRF
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Add a request interceptor to include Authorization and CSRF token
api.interceptors.request.use((config) => {
  // Always attach latest access token
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`;
  }

  // For POST, PUT, PATCH, DELETE requests, include CSRF token
  if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase() || '')) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
  }
  return config;
});

// Add a response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = getRefreshToken();
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          }, {
            withCredentials: true,
            headers: {
              'X-CSRFToken': getCookie('csrftoken')
            }
          });

          const { access } = response.data;
          setAccessToken(access);
          api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
          originalRequest.headers['Authorization'] = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // If refresh token fails, logout the user
        clearTokens();
        navigateTo('/login');
      }
    }
    return Promise.reject(error);
  }
);

export default api; 
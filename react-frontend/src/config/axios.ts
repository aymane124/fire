import axios from 'axios';
import { API_URL } from './index';

// Configure axios defaults
axios.defaults.withCredentials = true;

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Function to get cookie value
const getCookie = (name: string): string | null => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
};

// Function to get CSRF token from cookie
export const getCSRFToken = () => {
  return getCookie('csrftoken');
};

// Function to fetch CSRF token
export const fetchCSRFToken = async () => {
  try {
    const response = await axios.get(`${API_URL}/api/auth/csrf/`, {
      withCredentials: true,
      headers: {
        'Accept': 'application/json',
      }
    });
    const token = response.data.token;
    if (token) {
      document.cookie = `csrftoken=${token}; path=/`;
    }
    return token;
  } catch (error) {
    console.error('Error fetching CSRF token:', error);
    throw error;
  }
};

// Request interceptor
axiosInstance.interceptors.request.use(
  async (config) => {
    // Skip CSRF for GET requests
    if (config.method?.toLowerCase() === 'get') {
      return config;
    }

    // Get CSRF token
    let csrfToken = getCSRFToken();
    
    // If no CSRF token, try to fetch it
    if (!csrfToken) {
      try {
        csrfToken = await fetchCSRFToken();
        if (!csrfToken) {
          throw new Error('Failed to get CSRF token');
        }
      } catch (error) {
        console.error('Failed to fetch CSRF token:', error);
        throw error;
      }
    }
    
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
      config.headers['X-Requested-With'] = 'XMLHttpRequest';
    }

    // Get auth token
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Ensure credentials are included
    config.withCredentials = true;
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the token
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
            refresh: refreshToken
          }, {
            withCredentials: true,
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken(),
            }
          });

          if (response.data.access) {
            // Store new token
            localStorage.setItem('access_token', response.data.access);
            
            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
            return axiosInstance(originalRequest);
          }
        }
      } catch (refreshError) {
        // If refresh fails, clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance; 
import axios from 'axios';
import { API_URL } from '../config';

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login?: string;
}

const api = axios.create({
  baseURL: API_URL
});

// Add request interceptor to add auth token
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

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const userService = {
  getUsers: async (): Promise<User[]> => {
    try {
      const response = await api.get('/auth/users/');
      return response.data.results || response.data;
    } catch (error) {
      throw error;
    }
  },

  getUser: async (id: string): Promise<User> => {
    try {
      const response = await api.get(`/auth/users/${id}/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  getCurrentUser: async (): Promise<User> => {
    try {
      const response = await api.get('/auth/users/me/');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  searchUsers: async (query: string): Promise<User[]> => {
    try {
      const response = await api.get(`/auth/users/?search=${encodeURIComponent(query)}`);
      return response.data.results || response.data;
    } catch (error) {
      throw error;
    }
  },

  getActiveUsers: async (): Promise<User[]> => {
    try {
      const response = await api.get('/auth/users/?is_active=true');
      return response.data.results || response.data;
    } catch (error) {
      throw error;
    }
  },

  getStaffUsers: async (): Promise<User[]> => {
    try {
      const response = await api.get('/auth/users/?is_staff=true');
      return response.data.results || response.data;
    } catch (error) {
      throw error;
    }
  }
};

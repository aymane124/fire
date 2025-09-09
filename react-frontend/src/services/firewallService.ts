import axios from 'axios';
import { API_URL } from '../config';

export interface Firewall {
    id: string;
    name: string;
    ip_address: string;
    firewall_type: string | {
        id: string;
        name: string;
        description?: string;
    };
    data_center: string;
    data_center_info?: {
        id: string;
        name: string;
        description?: string;
    };
    firewall_type_info?: {
        id: string;
        name: string;
        description?: string;
    };
    firewall_type_details?: {
        id: string;
        name: string;
        description?: string;
    };
    attributes?: Record<string, any>;
    created_at: string;
    updated_at: string;
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

export const firewallService = {
    getFirewalls: async (page?: number): Promise<any> => {
        try {
            let url = '/firewalls/firewalls/';
            if (page) {
                url += `?page=${page}`;
            }
            const response = await api.get(url);
            // Return the full response data to maintain compatibility with pagination
            return response.data;
        } catch (error) {
            throw error;
        }
    },

    getFirewall: async (id: string): Promise<Firewall> => {
        try {
            const response = await api.get(`/firewalls/firewalls/${id}/`);
            return response.data;
        } catch (error) {
            throw error;
        }
    },

    createFirewall: async (firewall: Partial<Firewall>): Promise<Firewall> => {
        try {
            const response = await api.post('/firewalls/firewalls/', firewall);
            return response.data;
        } catch (error) {
            throw error;
        }
    },

    updateFirewall: async (id: string, firewall: Partial<Firewall>): Promise<Firewall> => {
        try {
            const response = await api.put(`/firewalls/firewalls/${id}/`, firewall);
            return response.data;
        } catch (error) {
            throw error;
        }
    },

    deleteFirewall: async (id: string): Promise<void> => {
        try {
            await api.delete(`/firewalls/firewalls/${id}/`);
        } catch (error) {
            throw error;
        }
    }
}; 
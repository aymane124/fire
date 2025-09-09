import axios, { AxiosResponse } from 'axios';
import { getAuthToken } from './authService';
import { API_URL } from '../config';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true  // This is important for CSRF
});

// Add request interceptor to add auth token and CSRF token
api.interceptors.request.use(
  async (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Get CSRF token from cookie
    const csrfToken = document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
      
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export interface Template {
  id: number;
  name: string;
  description: string;
  content: string;
  variables: Variable[];
  created_at?: string;
}

export interface Variable {
  id: number;
  name: string;
  description: string;
  value: string;
}

const REQUIRED_VARIABLES = [
  { name: 'Name', description: 'Template name' },
  { name: 'Source Address', description: 'Source IP address or network' },
  { name: 'Source Description', description: 'Description of the source' },
  { name: 'Source Interface', description: 'Source network interface' },
  { name: 'Destination Address', description: 'Destination IP address or network' },
  { name: 'Destination Description', description: 'Description of the destination' },
  { name: 'Destination Interface', description: 'Destination network interface' },
  { name: 'Service', description: 'Network service or port' }
];

class TemplateService {
  async getVariables(): Promise<Variable[]> {
    try {
      const response = await api.get('/templates/variables/');
      return response.data.results || [];
    } catch (error) {
      throw new Error('Failed to fetch variables');
    }
  }

  async getTemplate(id: number): Promise<Template> {
    try {
      const response = await api.get(`/templates/${id}/`);
      return response.data;
    } catch (error) {
      throw new Error('Failed to fetch template');
    }
  }

  async getTemplates(): Promise<Template[]> {
    try {
      const response = await api.get('/templates/');
      return response.data.results || [];
    } catch (error) {
      throw new Error('Failed to fetch templates');
    }
  }

  async createTemplate(template: Omit<Template, 'id'>): Promise<Template> {
    try {
      const response = await api.post('/templates/', template);
      return response.data;
    } catch (error) {
      throw new Error('Failed to create template');
    }
  }

  async updateTemplate(id: number, template: Partial<Template>): Promise<Template> {
    try {
      const response = await api.patch(`/templates/${id}/`, template);
      return response.data;
    } catch (error) {
      throw new Error('Failed to update template');
    }
  }

  async deleteTemplate(id: number): Promise<void> {
    try {
      await api.delete(`/templates/${id}/`);
    } catch (error) {
      throw new Error('Failed to delete template');
    }
  }
}

export const templateService = new TemplateService();

// Variable Service
export const variableService = {
  getVariables: async (): Promise<Variable[]> => {
    try {
      const token = getAuthToken();
      if (!token) {
        console.error('No authentication token found');
        return [];
      }

      let allVariables: Variable[] = [];
      let nextUrl: string | null = `${API_URL}/templates/variables/`;

      // Récupérer toutes les pages
      while (nextUrl) {
        const response: AxiosResponse = await axios.get(nextUrl, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (Array.isArray(response.data)) {
          allVariables = [...allVariables, ...response.data];
          nextUrl = null;
        } else if (response.data.results && Array.isArray(response.data.results)) {
          allVariables = [...allVariables, ...response.data.results];
          nextUrl = response.data.next;
        } else {
          console.error('Unexpected API response format:', response.data);
          break;
        }
      }

      return allVariables;
    } catch (error) {
      console.error('Error fetching variables:', error);
      if (axios.isAxiosError(error)) {
        console.error('Error details:', {
          status: error.response?.status,
          data: error.response?.data,
          headers: error.response?.headers
        });
      }
      return [];
    }
  },

  createVariable: async (variable: { name: string; description: string }): Promise<Variable> => {
    try {
      const response = await axios.post(`${API_URL}/templates/variables/`, variable, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error creating variable:', error);
      throw error;
    }
  },

  updateVariable: async (id: number, variable: { name: string; description: string }): Promise<Variable> => {
    try {
      const response = await axios.put(`${API_URL}/templates/variables/${id}/`, variable, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error updating variable:', error);
      throw error;
    }
  },

  deleteVariable: async (id: number): Promise<void> => {
    try {
      await axios.delete(`${API_URL}/templates/variables/${id}/`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Error deleting variable:', error);
      throw error;
    }
  },

  addVariableToTemplate: async (templateId: number, variableId: number): Promise<void> => {
    try {
      await axios.post(`${API_URL}/templates/${templateId}/add_variable/`, { variable_id: variableId }, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Error adding variable to template:', error);
      throw error;
    }
  },

  removeVariableFromTemplate: async (templateId: number, variableId: number): Promise<void> => {
    try {
      await axios.post(`${API_URL}/templates/${templateId}/remove_variable/`, { variable_id: variableId }, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Error removing variable from template:', error);
      throw error;
    }
  },

  async ensureRequiredVariables(): Promise<void> {
    const existingVariables = await this.getVariables();
    const existingNames = new Set(existingVariables.map(v => v.name));

    for (const requiredVar of REQUIRED_VARIABLES) {
      if (!existingNames.has(requiredVar.name)) {
        await this.createVariable(requiredVar);
      }
    }
  }
}; 
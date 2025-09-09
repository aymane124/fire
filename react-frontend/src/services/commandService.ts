import axios from 'axios';
import { getAuthToken } from './authService';
import { API_URL } from '../config';

export interface CommandResponse {
  id: number;
  firewall: string;
  command: string;
  output: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  error_message?: string;
  executed_at: string;
}

export const executeCommand = async (firewallId: string, command: string): Promise<CommandResponse> => {
  try {
    const response = await axios.post(
      `${API_URL}/command/execute/`,
      { firewall_id: firewallId, command },
      {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'Failed to execute command');
    }
    throw error;
  }
};

export const getCommandHistory = async (firewallId: string): Promise<CommandResponse[]> => {
  try {
    const response = await axios.get(
      `${API_URL}/command/commands/`,
      {
        params: { firewall_id: firewallId },
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'Failed to fetch command history');
    }
    throw error;
  }
}; 

export const executeTemplate = async (firewallId: string, commands: string[]): Promise<{ status: string; results: Array<{ command: string; status: string; output?: string; error?: string }> }> => {
  try {
    const response = await axios.post(
      `${API_URL}/command/commands/execute-template/`,
      { firewall_id: firewallId, commands },
      {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'Failed to execute template');
    }
    throw error;
  }
};
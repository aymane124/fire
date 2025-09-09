import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

const API_URL = import.meta.env.VITE_API_URL;

export interface UserProfileData {
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  password?: string;
}

interface DecodedToken {
  exp: number;
  user_id: string;
}

export const isTokenValid = (token: string): boolean => {
  try {
    const decoded = jwtDecode<DecodedToken>(token);
    const currentTime = Date.now() / 1000;
    return decoded.exp > currentTime;
  } catch {
    return false;
  }
};

export const getAuthToken = (): string | null => {
  const token = localStorage.getItem('token');
  if (!token) return null;
  
  if (!isTokenValid(token)) {
    removeAuthToken();
    return null;
  }
  
  return token;
};

export const setAuthToken = (token: string): void => {
  if (!isTokenValid(token)) {
    throw new Error('Invalid token');
  }
  localStorage.setItem('token', token);
};

export const removeAuthToken = (): void => {
  localStorage.removeItem('token');
};

export const updateUserProfile = async (data: UserProfileData, token: string) => {
  if (!isTokenValid(token)) {
    throw new Error('Token expired');
  }
  
  try {
    const response = await axios.put(
      `${API_URL}/api/auth/users/update_user_info/`,
      data,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      removeAuthToken();
    }
    throw error;
  }
}; 
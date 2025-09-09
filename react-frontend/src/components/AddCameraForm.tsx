import React, { useState, useRef } from 'react';
import axios from 'axios';
import { useAuth } from 'src/contexts/AuthContext';
import { API_URL } from 'src/config';
import { Camera } from 'src/types/camera';
import { decimalToDms } from 'src/utils/coordinateConverters.ts';

interface AddCameraFormProps {
  onClose: () => void;
  position: [number, number];
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onCamerasUpdate: (cameras: Camera[]) => void;
}

const AddCameraForm: React.FC<AddCameraFormProps> = ({ 
  onClose, 
  position, 
  onSuccess,
  onError,
  onCamerasUpdate 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    ip_address: '',
    location: `${decimalToDms(position[0], true)} ${decimalToDms(position[1], false)}`,
    latitude: position[0].toString(),
    longitude: position[1].toString()
  });
  const { isAuthenticated, token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isAuthenticated || !token) {
      onError('Veuillez vous connecter pour ajouter une caméra');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await axios.post(`${API_URL}/cameras/cameras/`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      if (response.status === 201) {
        onSuccess('Caméra ajoutée avec succès');
        const camerasResponse = await axios.get(`${API_URL}/cameras/cameras/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        onCamerasUpdate(camerasResponse.data.results || []);
        onClose();
      }
    } catch (error) {
      console.error('Error adding camera:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          onError('Session expirée. Veuillez vous reconnecter.');
          localStorage.removeItem('token');
          window.location.href = '/login';
        } else {
          onError(error.response?.data?.error || 'Erreur lors de l\'ajout de la caméra');
        }
      } else {
        onError('Erreur lors de l\'ajout de la caméra');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!isAuthenticated || !token) {
      onError('Veuillez vous connecter pour importer des caméras');
      return;
    }

    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      onError('Le fichier doit être au format CSV');
      return;
    }

    setIsSubmitting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/cameras/cameras/upload_csv/`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json',
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.status === 200) {
        onSuccess(`Import réussi: ${response.data.created} créées, ${response.data.updated} mises à jour`);
        const camerasResponse = await axios.get(`${API_URL}/cameras/cameras/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        onCamerasUpdate(camerasResponse.data.results || []);
        onClose();
      }
    } catch (error) {
      console.error('Error uploading CSV:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          onError('Session expirée. Veuillez vous reconnecter.');
          localStorage.removeItem('token');
          window.location.href = '/login';
        } else if (error.response?.status === 400) {
          onError(error.response.data.error || 'Format de fichier invalide ou données manquantes');
        } else {
          onError(error.response?.data?.error || 'Erreur lors de l\'importation du fichier CSV');
        }
      } else {
        onError('Erreur lors de l\'importation du fichier CSV');
      }
    } finally {
      setIsSubmitting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-xl z-50 w-full max-w-2xl mx-auto border border-gray-200">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-2xl font-bold text-gray-800">Ajouter une nouvelle caméra</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
          disabled={isSubmitting}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section: Informations Générales */}
        <fieldset className="border border-gray-300 rounded-lg p-4 pb-6">
          <legend className="text-md font-semibold text-gray-700 px-2">Informations Générales</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-y-5 gap-x-4 pt-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">Nom de la caméra</label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                placeholder="Ex: Caméra Principale Entrée"
                required
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label htmlFor="ip_address" className="block text-sm font-medium text-gray-700 mb-1">Adresse IP</label>
              <input
                type="text"
                id="ip_address"
                value={formData.ip_address}
                onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                placeholder="Ex: 192.168.1.100"
                required
                disabled={isSubmitting}
              />
            </div>
            <div className="col-span-1 md:col-span-2">
              <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">Emplacement (Description)</label>
              <input
                type="text"
                id="location"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                placeholder="Ex: Bâtiment A, Porte 2"
                disabled={isSubmitting}
              />
            </div>
          </div>
        </fieldset>

        {/* Section: Coordonnées Géographiques */}
        <fieldset className="border border-gray-300 rounded-lg p-4 pb-6">
          <legend className="text-md font-semibold text-gray-700 px-2">Coordonnées Géographiques</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-y-5 gap-x-4 pt-4">
            <div>
              <label htmlFor="latitude" className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
              <input
                type="text"
                id="latitude"
                value={formData.latitude}
                onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                placeholder="Ex: 34.0000 (Décimal)"
                required
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label htmlFor="longitude" className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
              <input
                type="text"
                id="longitude"
                value={formData.longitude}
                onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                placeholder="Ex: -6.0000 (Décimal)"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>
        </fieldset>

        {/* Actions Buttons */}
        <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-4 mt-6">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv"
            className="hidden"
            id="csv-upload"
            disabled={isSubmitting}
          />
          <label
            htmlFor="csv-upload"
            className={`w-full sm:w-auto flex justify-center items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 cursor-pointer transition-colors duration-200 ${
              isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {isSubmitting ? (
              <span className="flex items-center"><svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-green-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Importation...</span>
            ) : (
              'Importer CSV'
            )}
          </label>
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto flex justify-center items-center px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
            disabled={isSubmitting}
          >
            Annuler
          </button>
          <button
            type="submit"
            className={`w-full sm:w-auto flex justify-center items-center px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200 ${
              isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="flex items-center"><svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Ajout en cours...</span>
            ) : (
              'Ajouter'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export { AddCameraForm }; 
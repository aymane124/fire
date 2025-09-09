import { useState, useEffect } from 'react';
import { User, Mail, Phone, Save, Lock, Trash2 } from 'lucide-react';
import api from '../utils/axiosConfig';
import { useNavigate } from 'react-router-dom';

interface UserData {
  id: string;
  username: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
}

interface PasswordFormData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

function UserProfile() {
  const navigate = useNavigate();
  const [userData, setUserData] = useState<UserData | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<UserData>>({});
  const [error, setError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [passwordFormData, setPasswordFormData] = useState<PasswordFormData>({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await api.get('/auth/users/me/');
        setUserData(response.data);
        setFormData(response.data);
        setError(null);
      } catch (err: any) {
        console.error('Error fetching user profile data:', err);
        setError(err.message);
      }
    };

    fetchUserData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Updating user data:', formData);
      const response = await api.put('/auth/users/update_user_info/', formData);
      console.log('Update response:', response.data);
      if (response.data) {
        setUserData(response.data.user);
        setIsEditing(false);
        setError(null);
      }
    } catch (err: any) {
      console.error('Error updating user data:', err);
      setError(err.message);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    // Validation
    if (passwordFormData.new_password !== passwordFormData.confirm_password) {
      setPasswordError('Les mots de passe ne correspondent pas');
      return;
    }

    if (passwordFormData.new_password.length < 8) {
      setPasswordError('Le mot de passe doit contenir au moins 8 caractères');
      return;
    }

    try {
      const response = await api.put('/auth/users/update_user_info/', {
        current_password: passwordFormData.current_password,
        password: passwordFormData.new_password
      });

      if (response.data) {
        setPasswordSuccess('Mot de passe mis à jour avec succès');
        setPasswordFormData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      }
    } catch (err: any) {
      console.error('Error updating password:', err);
      setPasswordError(err.response?.data?.error || 'Erreur lors de la mise à jour du mot de passe');
    }
  };

  const handleDeleteProfile = async () => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.delete('/auth/users/me/');
      // Clear local storage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Redirect to login page
      navigate('/login');
    } catch (err: any) {
      console.error('Error deleting profile:', err);
      setDeleteError(err.response?.data?.error || 'Erreur lors de la suppression du profil');
      setShowDeleteConfirm(false);
    } finally {
      setIsDeleting(false);
    }
  };

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (!userData) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              <div className="h-4 bg-gray-200 rounded w-4/6"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header avec glassmorphism */}
        <div className="bg-white/70 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
          <div className="flex items-center space-x-6 mb-6">
            <div className="bg-gradient-to-r from-purple-500 to-indigo-600 p-4 rounded-2xl shadow-lg">
              <User className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-purple-800 to-slate-900 bg-clip-text text-transparent mb-2">
                {userData.first_name} {userData.last_name}
              </h1>
              <p className="text-slate-600 text-lg">@{userData.username}</p>
            </div>
          </div>
        </div>

        {/* Informations du profil avec glassmorphism */}
        <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
            Informations du Profil
          </h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">Username</label>
              <div className="flex items-center">
                <User className="h-6 w-6 text-purple-600 mr-3" />
                <input
                  type="text"
                  value={formData.username || ''}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  disabled={!isEditing}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-3">First Name</label>
                <input
                  type="text"
                  value={formData.first_name || ''}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  className="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  disabled={!isEditing}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-3">Last Name</label>
                <input
                  type="text"
                  value={formData.last_name || ''}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  className="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  disabled={!isEditing}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">Email</label>
              <div className="flex items-center">
                <Mail className="h-6 w-6 text-blue-600 mr-3" />
                <input
                  type="email"
                  value={formData.email || ''}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  disabled={!isEditing}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">Phone Number</label>
              <div className="flex items-center">
                <Phone className="h-6 w-6 text-green-600 mr-3" />
                <input
                  type="tel"
                  value={formData.phone_number || ''}
                  onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  disabled={!isEditing}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-4 pt-6">
              {isEditing ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditing(false);
                      setFormData(userData);
                    }}
                    className="px-6 py-3 border border-slate-300 rounded-xl text-slate-700 hover:bg-slate-50 transition-all duration-200 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                  >
                    <Save className="h-5 w-5 mr-2" />
                    Save Changes
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                >
                  Edit Profile
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Changement de mot de passe avec glassmorphism */}
        <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-8 mb-8">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-purple-800 bg-clip-text text-transparent mb-6">
            Changement de Mot de Passe
          </h2>
          <form onSubmit={handlePasswordChange} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">Current Password</label>
              <div className="flex items-center">
                <Lock className="h-6 w-6 text-purple-600 mr-3" />
                <input
                  type="password"
                  value={passwordFormData.current_password}
                  onChange={(e) => setPasswordFormData({...passwordFormData, current_password: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">New Password</label>
              <div className="flex items-center">
                <Lock className="h-6 w-6 text-blue-600 mr-3" />
                <input
                  type="password"
                  value={passwordFormData.new_password}
                  onChange={(e) => setPasswordFormData({...passwordFormData, new_password: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">Confirm New Password</label>
              <div className="flex items-center">
                <Lock className="h-6 w-6 text-green-600 mr-3" />
                <input
                  type="password"
                  value={passwordFormData.confirm_password}
                  onChange={(e) => setPasswordFormData({...passwordFormData, confirm_password: e.target.value})}
                  className="flex-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all duration-200 bg-white/50 backdrop-blur-sm"
                  required
                />
              </div>
            </div>

            {passwordError && (
              <div className="p-4 bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-xl shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="font-medium">{passwordError}</span>
                </div>
              </div>
            )}

            {passwordSuccess && (
              <div className="p-4 bg-green-50/80 backdrop-blur-sm border border-green-200 text-green-700 rounded-xl shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="font-medium">{passwordSuccess}</span>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-4">
              <button
                type="submit"
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
              >
                <Lock className="h-5 w-5 mr-2" />
                Change Password
              </button>
            </div>
          </form>
        </div>

        {/* Zone de danger avec glassmorphism */}
        <div className="bg-gradient-to-r from-red-50/80 to-pink-50/80 backdrop-blur-lg rounded-2xl border border-red-200/50 shadow-xl p-8">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent mb-6">
            Zone de Danger
          </h2>
          <div className="bg-red-50/60 backdrop-blur-sm border border-red-200 rounded-xl p-6">
            <p className="text-red-700 mb-6 text-lg font-medium">
              La suppression de votre compte est irréversible. Toutes vos données seront définitivement supprimées.
            </p>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl hover:from-red-700 hover:to-pink-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
            >
              <Trash2 className="h-5 w-5 mr-2" />
              Supprimer mon compte
            </button>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white/95 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl max-w-md w-full transform transition-all duration-300">
              <div className="p-8">
                <h3 className="text-2xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent mb-4">
                  Confirmer la suppression
                </h3>
                <p className="text-slate-600 mb-6 text-lg">
                  Êtes-vous sûr de vouloir supprimer votre compte ? Cette action est irréversible.
                </p>
                {deleteError && (
                  <div className="p-4 bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-700 rounded-xl shadow-lg mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="font-medium">{deleteError}</span>
                    </div>
                  </div>
                )}
                <div className="flex justify-end space-x-4">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={isDeleting}
                    className="px-6 py-3 border border-slate-300 rounded-xl text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-all duration-200 font-medium"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleDeleteProfile}
                    disabled={isDeleting}
                    className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl hover:from-red-700 hover:to-pink-700 flex items-center disabled:opacity-50 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                  >
                    {isDeleting ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3"></div>
                        Suppression en cours...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-5 w-5 mr-2" />
                        Confirmer la suppression
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UserProfile; 
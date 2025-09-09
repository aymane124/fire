import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axiosInstance, { fetchCSRFToken, getCSRFToken } from '../config/axios';
import { User, Mail, Phone, Lock, UserCircle, Eye, EyeOff, Shield, ArrowRight, ArrowLeft } from 'lucide-react';
import InwiLogo from '../assets/inwi-logo.svg';

interface RegisterProps {
  onRegister?: () => void;
}

function Register({ onRegister }: RegisterProps) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phone_number: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isFocused, setIsFocused] = useState({
    username: false,
    email: false,
    phone: false,
    password: false,
    confirmPassword: false,
    firstName: false,
    lastName: false
  });

  useEffect(() => {
    // Fetch CSRF token when component mounts
    const setupCSRF = async () => {
      try {
        await fetchCSRFToken();
      } catch (error) {
        console.error('Failed to fetch CSRF token:', error);
        setError('Erreur de configuration CSRF. Veuillez rafraîchir la page.');
      }
    };
    setupCSRF();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      setIsLoading(false);
      return;
    }

    try {
      // Ensure we have a CSRF token before submitting
      const csrfToken = getCSRFToken();
      if (!csrfToken) {
        await fetchCSRFToken();
      }

      const response = await axiosInstance.post('/api/auth/register/', {
        username: formData.username,
        email: formData.email,
        phone_number: formData.phone_number,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name
      });

      if (response.data.access) {
        // Store the access token
        localStorage.setItem('access_token', response.data.access);
        if (response.data.refresh) {
          localStorage.setItem('refresh_token', response.data.refresh);
        }
        
        if (onRegister) {
          onRegister();
        } else {
          navigate('/');
        }
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      if (error.response?.data?.error) {
        setError(error.response.data.error);
      } else if (error.response?.data?.username) {
        setError('Ce nom d\'utilisateur est déjà pris');
      } else if (error.response?.status === 403) {
        setError('Erreur CORS: Vérifiez la configuration du serveur');
      } else {
        setError('Une erreur est survenue lors de l\'inscription. Veuillez réessayer.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background Elements */}
      <div className="absolute inset-0">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-2xl">
          {/* Logo Section */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl mb-6">
              <img src={InwiLogo} alt="INWI Logo" className="h-10 w-auto" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Créer un compte</h1>
            <p className="text-white/70 text-lg">Rejoignez notre plateforme de gestion de pare-feu</p>
          </div>

          {/* Register Form */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl p-8">
            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-200 text-sm flex items-center gap-2">
                <Shield className="h-4 w-4" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Name Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative">
                  <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                    isFocused.firstName ? 'text-purple-400' : 'text-white/50'
                  }`}>
                    <UserCircle className="h-5 w-5" />
                  </div>
                  <input
                    type="text"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleChange}
                    onFocus={() => setIsFocused(prev => ({ ...prev, firstName: true }))}
                    onBlur={() => setIsFocused(prev => ({ ...prev, firstName: false }))}
                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                    placeholder="Prénom"
                    required
                  />
                </div>

                <div className="relative">
                  <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                    isFocused.lastName ? 'text-purple-400' : 'text-white/50'
                  }`}>
                    <UserCircle className="h-5 w-5" />
                  </div>
                  <input
                    type="text"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleChange}
                    onFocus={() => setIsFocused(prev => ({ ...prev, lastName: true }))}
                    onBlur={() => setIsFocused(prev => ({ ...prev, lastName: false }))}
                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                    placeholder="Nom"
                    required
                  />
                </div>
              </div>

              {/* Username Field */}
              <div className="relative">
                <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                  isFocused.username ? 'text-purple-400' : 'text-white/50'
                }`}>
                  <User className="h-5 w-5" />
                </div>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  onFocus={() => setIsFocused(prev => ({ ...prev, username: true }))}
                  onBlur={() => setIsFocused(prev => ({ ...prev, username: false }))}
                  className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                  placeholder="Nom d'utilisateur"
                  required
                />
              </div>

              {/* Email Field */}
              <div className="relative">
                <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                  isFocused.email ? 'text-purple-400' : 'text-white/50'
                }`}>
                  <Mail className="h-5 w-5" />
                </div>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  onFocus={() => setIsFocused(prev => ({ ...prev, email: true }))}
                  onBlur={() => setIsFocused(prev => ({ ...prev, email: false }))}
                  className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                  placeholder="Adresse email"
                  required
                />
              </div>

              {/* Phone Field */}
              <div className="relative">
                <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                  isFocused.phone ? 'text-purple-400' : 'text-white/50'
                }`}>
                  <Phone className="h-5 w-5" />
                </div>
                <input
                  type="tel"
                  name="phone_number"
                  value={formData.phone_number}
                  onChange={handleChange}
                  onFocus={() => setIsFocused(prev => ({ ...prev, phone: true }))}
                  onBlur={() => setIsFocused(prev => ({ ...prev, phone: false }))}
                  className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                  placeholder="Numéro de téléphone"
                  required
                />
              </div>

              {/* Password Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative">
                  <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                    isFocused.password ? 'text-purple-400' : 'text-white/50'
                  }`}>
                    <Lock className="h-5 w-5" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    onFocus={() => setIsFocused(prev => ({ ...prev, password: true }))}
                    onBlur={() => setIsFocused(prev => ({ ...prev, password: false }))}
                    className="w-full pl-12 pr-12 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                    placeholder="Mot de passe"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-white/50 hover:text-white/70 transition-colors duration-200"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>

                <div className="relative">
                  <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-200 ${
                    isFocused.confirmPassword ? 'text-purple-400' : 'text-white/50'
                  }`}>
                    <Lock className="h-5 w-5" />
                  </div>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    onFocus={() => setIsFocused(prev => ({ ...prev, confirmPassword: true }))}
                    onBlur={() => setIsFocused(prev => ({ ...prev, confirmPassword: false }))}
                    className="w-full pl-12 pr-12 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all duration-200 backdrop-blur-sm"
                    placeholder="Confirmer le mot de passe"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-white/50 hover:text-white/70 transition-colors duration-200"
                  >
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-4 px-6 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                ) : (
                  <>
                    Créer mon compte
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Login Link */}
            <div className="mt-6 text-center">
              <p className="text-white/70 text-sm">
                Déjà un compte ?{' '}
                <Link
                  to="/login"
                  className="font-semibold text-purple-300 hover:text-purple-200 transition-colors duration-200 underline decoration-purple-300/30 hover:decoration-purple-200/50"
                >
                  Se connecter
                </Link>
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-white/50 text-sm">
              © 2024 INWI. Tous droits réservés.
            </p>
          </div>
        </div>
      </div>

      {/* Custom CSS for animations */}
      <style>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </div>
  );
}

export default Register; 
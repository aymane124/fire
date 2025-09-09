import React, { useState, useEffect } from 'react';
import { MemoryRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { LogOut, Settings as SettingsIcon, Activity, HardDrive, Sparkles } from 'lucide-react';
import api from './utils/axiosConfig';
import { setNavigate } from './utils/navigation';
import Login from './components/Login';
import Register from './components/Register';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import FlowMatrix from './components/FlowMatrix';
import FirewallConfig from './components/FirewallConfig';
import Settings from './components/Settings';
import FirewallList from './components/FirewallList';
import WorldMap from './components/WorldMap';
import { AuthProvider } from './contexts/AuthContext';
import TemplateSection from './components/TemplateSection';
import UserProfile from './components/UserProfile';
import History from './components/History';
import DailyCheck from './components/DailyCheck';
import { Toaster } from 'react-hot-toast';
import NetworkMap from './components/NetworkMap';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminLogs from './pages/AdminLogs';
import AutomatedEmails from './pages/AutomatedEmails';
import InterfaceAlerts from './pages/InterfaceAlerts';
import TerminalTabs from './components/TerminalTabs';

// Protected Route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" />;
  }
  return <>{children}</>;
};

// Layout component for authenticated pages
const AuthenticatedLayout = ({ children }: { children: React.ReactNode }) => {
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  // Sidebar open/close state
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      delete api.defaults.headers.common['Authorization'];
      navigate('/login');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-900"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Sidebar 
        onLogout={handleLogout} 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen}
      />
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${sidebarOpen ? 'lg:ml-80' : 'ml-0'}`}>
        <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-50 to-slate-100">
          <div className="min-h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

// AppRoutes component that uses useNavigate
const AppRoutes = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setNavigate(navigate);
  }, [navigate]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const refreshToken = localStorage.getItem('refreshToken');
    
    if (token && refreshToken) {
      setIsAuthenticated(true);
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={() => setIsAuthenticated(true)} />} />
      <Route path="/register" element={<Register onRegister={() => setIsAuthenticated(true)} />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <Dashboard />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/firewalls"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <FirewallList />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <UserProfile />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <TemplateSection />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates/new"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <TemplateSection />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates/:id"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <TemplateSection />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/config"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <FirewallConfig />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/matrix"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <FlowMatrix />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/map"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <WorldMap />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <Settings />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <History />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/daily-check"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <DailyCheck />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/network-map"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <NetworkMap />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin-dashboard"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <AdminDashboard />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin-users"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <AdminUsers />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin-logs"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <AdminLogs />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/automated-emails"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <AutomatedEmails />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/interface-alerts"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <InterfaceAlerts />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/terminals"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <TerminalTabs />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/terminal/:firewallId"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <TerminalTabs />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

// Main App component
function App() {
  return (
    <Router>
      <Toaster position="top-right" />
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;
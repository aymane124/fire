import React, { useState } from 'react';
import { 
  LogOut, 
  Settings, 
  Activity, 
  HardDrive, 
  Terminal,
  Map, 
  FileText, 
  User, 
  Shield, 
  Clock,
  ChevronDown,
  ChevronRight,
  Network,
  ChevronLeft,
  Menu,
  X,
  Mail,
  AlertTriangle
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import inwiLogo from '../assets/inwi-logo.svg';

interface SidebarProps {
  onLogout: () => void;
  sidebarOpen: boolean;
  setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

interface NavItem {
  path: string;
  icon: React.ElementType;
  label: string;
  description?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const Sidebar = ({ onLogout, sidebarOpen, setSidebarOpen }: SidebarProps) => {
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    main: true,
    maps: true,
    settings: true,
    tools: true,
    admin: true
  });

  // Get user role from localStorage
  const role = localStorage.getItem('role');

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const navSections: NavSection[] = [
    {
      title: 'Main',
      items: [
        { path: '/firewalls', icon: Shield, label: 'Pare-feux', description: 'Gestion des pare-feux' },
        { path: '/daily-check', icon: Clock, label: 'Daily Check', description: 'Vérifications quotidiennes' },
        { path: '/config', icon: HardDrive, label: 'Backup config', description: 'Sauvegarde des configurations' },
      ]
    },
    {
      title: 'Maps',
      items: [
        { path: '/map', icon: Map, label: 'Mapping CCTV', description: 'Cartographie des caméras' },
        { path: '/network-map', icon: Network, label: 'Mapping FWs', description: 'Cartographie des pare-feux' },
      ]
    },
    {
      title: 'Settings',
      items: [
        { path: '/settings', icon: Settings, label: 'Paramètres', description: 'Configuration système' },
        { path: '/templates', icon: FileText, label: 'Configuration templates', description: 'Modèles de configuration' },
        { path: '/matrix', icon: Activity, label: 'Dynamic configuration', description: 'Configuration dynamique' },
      ]
    },
    {
      title: 'Tools',
      items: [
        { path: '/profile', icon: User, label: 'Profile', description: 'Gestion du profil' },
        { path: '/history', icon: Clock, label: 'Historique', description: 'Historique des actions' },
        { path: '/terminals', icon: Terminal, label: 'Terminaux', description: 'Accès SSH' },
      ]
    }
  ];

  // Admin-only section
  const adminSections: NavSection[] = role === 'admin' ? [
    {
      title: 'Admin',
      items: [
        { path: '/admin-users', icon: User, label: 'Gestion utilisateurs', description: 'Administration des utilisateurs' },
        { path: '/automated-emails', icon: Mail, label: 'Emails automatiques', description: 'Planification des emails quotidiens' },
        { path: '/interface-alerts', icon: AlertTriangle, label: 'Alertes interfaces', description: 'Interfaces down, alertes email' },
      ]
    }
  ] : [];

  // Combine admin and normal sections
  const allSections = [...adminSections, ...navSections];

  return (
    <>
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Toggle Button */}
      <button
        className={`fixed top-4 left-4 z-50 bg-gradient-to-r from-purple-600 to-purple-700 text-white p-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 ${
          sidebarOpen ? 'lg:left-64' : 'lg:left-4'
        }`}
        onClick={() => setSidebarOpen((open) => !open)}
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? (
          <X className="h-5 w-5" />
        ) : (
          <Menu className="h-5 w-5" />
        )}
      </button>

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-screen z-40 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } w-80 bg-gradient-to-b from-slate-900/95 to-slate-800/95 backdrop-blur-xl border-r border-white/10 shadow-2xl`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-center mb-4">
              <Link to="/" className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-xl p-3 hover:bg-white/20 transition-all duration-200 transform hover:scale-105">
                <img src={inwiLogo} alt="INWI Logo" className="h-8 w-auto" />
              </Link>
            </div>
            <div className="text-center">
              <Link to="/" className="hover:text-purple-300 transition-colors duration-200">
                <h1 className="text-xl font-bold text-white">INWI Firewall</h1>
                <p className="text-white/60 text-sm">Management System</p>
              </Link>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-4 custom-sidebar-scrollbar">
            <div className="space-y-4">
              {allSections.map((section) => (
                <div key={section.title} className="space-y-2">
                  <button
                    onClick={() => toggleSection(section.title.toLowerCase())}
                    className="flex items-center justify-between w-full p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all duration-200 group"
                  >
                    <span className="font-semibold text-white group-hover:text-purple-300 transition-colors duration-200">
                      {section.title}
                    </span>
                    {expandedSections[section.title.toLowerCase()] ? (
                      <ChevronDown className="h-4 w-4 text-white/60 group-hover:text-purple-300 transition-colors duration-200" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-white/60 group-hover:text-purple-300 transition-colors duration-200" />
                    )}
                  </button>
                  
                  {expandedSections[section.title.toLowerCase()] && (
                    <div className="space-y-1 pl-2">
                      {section.items.map((item) => {
                        const Icon = item.icon;
                        const active = isActive(item.path);
                        return (
                          <Link
                            key={item.path}
                            to={item.path}
                            className={`group flex items-start space-x-3 w-full p-3 rounded-xl transition-all duration-200 ${
                              active 
                                ? 'bg-gradient-to-r from-purple-600/20 to-purple-700/20 border border-purple-500/30 shadow-lg' 
                                : 'hover:bg-white/5 border border-transparent'
                            }`}
                          >
                            <div className={`p-2 rounded-lg transition-all duration-200 ${
                              active 
                                ? 'bg-purple-600 text-white shadow-lg' 
                                : 'bg-white/10 text-white/60 group-hover:bg-purple-600/20 group-hover:text-purple-300'
                            }`}>
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className={`font-medium transition-colors duration-200 ${
                                active ? 'text-white' : 'text-white/80 group-hover:text-white'
                              }`}>
                                {item.label}
                              </div>
                              {item.description && (
                                <div className="text-xs text-white/50 mt-1 line-clamp-2">
                                  {item.description}
                                </div>
                              )}
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-white/10">
            <button
              onClick={onLogout}
              className="flex items-center justify-center space-x-3 w-full p-3 rounded-xl bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-300 hover:text-red-200 transition-all duration-200 group"
            >
              <LogOut className="h-5 w-5" />
              <span className="font-medium">Se déconnecter</span>
            </button>
            
            <div className="mt-4 text-center">
              <p className="text-white/40 text-xs">
                © 2024 INWI. Tous droits réservés.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
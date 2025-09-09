import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, X, Plus, Monitor } from 'lucide-react';
import { firewallService, Firewall } from '../services/firewallService';
import { createWebSocketService } from '../services/websocketService';
import { useParams } from 'react-router-dom';

interface TerminalTab {
  id: string;
  firewallId: string;
  firewallName: string;
  firewallIp: string;
  isConnected: boolean;
}

interface TerminalMessage {
  type: 'command' | 'output' | 'error' | 'system';
  content: string;
  timestamp: Date;
}

const TerminalTabs: React.FC = () => {
  const { firewallId } = useParams<{ firewallId?: string }>();
  const [tabs, setTabs] = useState<TerminalTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [firewalls, setFirewalls] = useState<Firewall[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFirewallSelector, setShowFirewallSelector] = useState(false);
  const [messages, setMessages] = useState<Map<string, TerminalMessage[]>>(new Map());
  const [commandInput, setCommandInput] = useState<Map<string, string>>(new Map());
  const [history, setHistory] = useState<Map<string, string[]>>(new Map());
  const [historyIndex, setHistoryIndex] = useState<Map<string, number>>(new Map());
  const [isCommandExecuting, setIsCommandExecuting] = useState<Map<string, boolean>>(new Map());
  const [lastMessage, setLastMessage] = useState<Map<string, { content: string; timestamp: number }>>(new Map());
  
  const inputRefs = useRef<Map<string, HTMLInputElement | null>>(new Map());
  const terminalRefs = useRef<Map<string, HTMLDivElement | null>>(new Map());
  const wsServices = useRef<Map<string, any>>(new Map());
  const [pagerWaiting, setPagerWaiting] = useState<Map<string, boolean>>(new Map());

  useEffect(() => {
    fetchFirewalls();
  }, []);

  useEffect(() => {
    if (firewallId && firewalls.length > 0) {
      const targetFirewall = firewalls.find(fw => fw.id === firewallId);
      if (targetFirewall && !tabs.some(tab => tab.firewallId === firewallId)) {
        addTab(targetFirewall);
      }
    }
  }, [firewallId, firewalls, tabs]);

  const fetchFirewalls = async () => {
    try {
      const data = await firewallService.getFirewalls();
      const firewallsArray = data.results || data;
      setFirewalls(Array.isArray(firewallsArray) ? firewallsArray : []);
    } catch (error) {
      console.error('Erreur lors de la récupération des pare-feu:', error);
      setFirewalls([]);
    } finally {
      setLoading(false);
    }
  };

  const addTab = (firewall: Firewall) => {
    const tabId = `terminal-${firewall.id}-${Date.now()}`;
    const newTab: TerminalTab = {
      id: tabId,
      firewallId: firewall.id,
      firewallName: firewall.name,
      firewallIp: firewall.ip_address,
      isConnected: false,
    };

    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
    setMessages(prev => new Map(prev).set(tabId, []));
    setCommandInput(prev => new Map(prev).set(tabId, ''));
    setHistory(prev => new Map(prev).set(tabId, []));
    setHistoryIndex(prev => new Map(prev).set(tabId, -1));
    setIsCommandExecuting(prev => new Map(prev).set(tabId, false));
    setShowFirewallSelector(false);
  };

  const removeTab = (tabId: string) => {
    const wsService = wsServices.current.get(tabId);
    if (wsService) {
      wsService.disconnect();
      wsServices.current.delete(tabId);
    }

    setTabs(prev => prev.filter(tab => tab.id !== tabId));
    setMessages(prev => {
      const newMessages = new Map(prev);
      newMessages.delete(tabId);
      return newMessages;
    });
    setCommandInput(prev => {
      const newInput = new Map(prev);
      newInput.delete(tabId);
      return newInput;
    });
    setHistory(prev => {
      const newHistory = new Map(prev);
      newHistory.delete(tabId);
      return newHistory;
    });
    setHistoryIndex(prev => {
      const newIndex = new Map(prev);
      newIndex.delete(tabId);
      return newIndex;
    });
    setIsCommandExecuting(prev => {
      const newExecuting = new Map(prev);
      newExecuting.delete(tabId);
      return newExecuting;
    });

    if (activeTabId === tabId) {
      const remainingTabs = tabs.filter(tab => tab.id !== tabId);
      if (remainingTabs.length > 0) {
        setActiveTabId(remainingTabs[remainingTabs.length - 1].id);
      } else {
        setActiveTabId(null);
      }
    }
  };

  const MAX_MESSAGES = 1000;
  const addMessage = (tabId: string, type: TerminalMessage['type'], content: string) => {
    // Vérifier si c'est un message en double (système)
    if (type === 'system') {
      const lastMsg = lastMessage.get(tabId);
      const now = Date.now();
      const timeWindow = 2000; // 2 secondes
      
      if (lastMsg && 
          lastMsg.content === content && 
          (now - lastMsg.timestamp) < timeWindow) {
        // Message en double, ne pas l'ajouter
        return;
      }
      
      // Mettre à jour le dernier message
      setLastMessage(prev => new Map(prev).set(tabId, {
        content,
        timestamp: now
      }));
    }

    setMessages(prev => {
      const tabMessages = prev.get(tabId) || [];
      const now = new Date();
      // Only merge small output chunks to avoid large DOM nodes
      if (type === 'output' && tabMessages.length > 0 && content.length < 100) {
        const lastIdx = tabMessages.length - 1;
        const lastMsg = tabMessages[lastIdx];
        if (lastMsg.type === 'output' && lastMsg.content.length < 500) {
          const merged = [...tabMessages];
          merged[lastIdx] = { ...lastMsg, content: lastMsg.content + content, timestamp: now };
          const trimmed = merged.length > MAX_MESSAGES ? merged.slice(merged.length - MAX_MESSAGES) : merged;
          return new Map(prev).set(tabId, trimmed);
        }
      }
      const newMessage: TerminalMessage = { type, content, timestamp: now };
      const appended = [...tabMessages, newMessage];
      const trimmed = appended.length > MAX_MESSAGES ? appended.slice(appended.length - MAX_MESSAGES) : appended;
      return new Map(prev).set(tabId, trimmed);
    });

    // Auto scroll to bottom
    setTimeout(() => {
      const terminal = terminalRefs.current.get(tabId);
      if (terminal) {
        terminal.scrollTop = terminal.scrollHeight;
      }
    }, 10);
  };

  const connectToTerminal = async (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId);
    if (!tab) return;

    try {
      const service = createWebSocketService(tab.firewallId);

      service.onConnect(() => {
        setTabs(prev => prev.map(t => 
          t.id === tabId ? { ...t, isConnected: true } : t
        ));
        addMessage(tabId, 'system', 'Connexion établie');
        setTimeout(() => inputRefs.current.get(tabId)?.focus(), 50);
      });

              service.onMessage((message) => {
          if (message.type === 'output') {
            addMessage(tabId, 'output', message.content || '');
            // Sortie reçue, cacher l'état pager si présent
            setPagerWaiting(prev => new Map(prev).set(tabId, false));
          } else if (message.type === 'error') {
            addMessage(tabId, 'error', message.content || '');
          } else if (message.type === 'system') {
            const content = message.content || '';
            // Ignorer complètement les messages de commande terminée
            if (content.includes('Commande terminée')) {
              setIsCommandExecuting(prev => new Map(prev).set(tabId, false));
              setTimeout(() => inputRefs.current.get(tabId)?.focus(), 100);
              return; // Ne pas ajouter le message
            }
            // Supprimer les messages de type "Exécution: <cmd>" ou "Executing: <cmd>"
            const trimmed = content.trim();
            if (trimmed.startsWith('Exécution:') || trimmed.startsWith('Executing:')) {
              return;
            }
            addMessage(tabId, 'system', content);
          } else if (message.type === 'command_status') {
            if (message.status === 'executing') {
              // Mark executing but do not print "Exécution: ..."; show only device response
              setIsCommandExecuting(prev => new Map(prev).set(tabId, true));
            } else if (message.status === 'completed') {
              setIsCommandExecuting(prev => new Map(prev).set(tabId, false));
              setPagerWaiting(prev => new Map(prev).set(tabId, false));
              setTimeout(() => inputRefs.current.get(tabId)?.focus(), 100);
            }
          } else if (message.type === 'pager') {
            // Le backend indique un "--More--"
            setPagerWaiting(prev => new Map(prev).set(tabId, true));
          }
        });

      service.onDisconnect(() => {
        setTabs(prev => prev.map(t => 
          t.id === tabId ? { ...t, isConnected: false } : t
        ));
        addMessage(tabId, 'system', 'Connexion fermée');
      });

      service.onError(() => {
        setTabs(prev => prev.map(t => 
          t.id === tabId ? { ...t, isConnected: false } : t
        ));
        addMessage(tabId, 'error', 'Erreur de connexion');
      });

      await service.connect();
      wsServices.current.set(tabId, service);

      setTimeout(() => {
        service.sendMessage({ type: 'connect_ssh' });
      }, 400);
    } catch (error) {
      setTabs(prev => prev.map(t => 
        t.id === tabId ? { ...t, isConnected: false } : t
      ));
      addMessage(tabId, 'error', 'Erreur de connexion');
    }
  };

  const disconnectTerminal = (tabId: string) => {
    const wsService = wsServices.current.get(tabId);
    if (wsService) {
      wsService.sendMessage({ type: 'disconnect_ssh' });
      wsService.disconnect();
      wsServices.current.delete(tabId);
    }
    setTabs(prev => prev.map(t => 
      t.id === tabId ? { ...t, isConnected: false } : t
    ));
    setPagerWaiting(prev => new Map(prev).set(tabId, false));
  };

  const sendCommand = (tabId: string) => {
    const command = commandInput.get(tabId)?.trim();
    const wsService = wsServices.current.get(tabId);
    const isConnected = tabs.find(t => t.id === tabId)?.isConnected;
      const isExecuting = isCommandExecuting.get(tabId);

    if (!command || !wsService || !isConnected || isExecuting) return;

    addMessage(tabId, 'command', `C:> ${command}`);

    try {
      wsService.sendCommand(command);

      // Add to history
      const tabHistory = history.get(tabId) || [];
      if (command && tabHistory[tabHistory.length - 1] !== command) {
        setHistory(prev => new Map(prev).set(tabId, [...tabHistory, command]));
      }
      setHistoryIndex(prev => new Map(prev).set(tabId, -1));

      setCommandInput(prev => new Map(prev).set(tabId, ''));
      
              setTimeout(() => {
                const input = inputRefs.current.get(tabId);
                if (input) {
                  input.focus();
                }
      }, 10);
    } catch (error) {
      addMessage(tabId, 'error', `Erreur: ${error}`);
    }
  };

  const handleKeyDown = (tabId: string, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
        sendCommand(tabId);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const tabHistory = history.get(tabId) || [];
      const currentIndex = historyIndex.get(tabId) || -1;
      if (tabHistory.length > 0) {
        const newIndex = currentIndex < tabHistory.length - 1 ? currentIndex + 1 : currentIndex;
        const historyCommand = tabHistory[tabHistory.length - 1 - newIndex];
        setCommandInput(prev => new Map(prev).set(tabId, historyCommand));
      setHistoryIndex(prev => new Map(prev).set(tabId, newIndex));
    }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const currentIndex = historyIndex.get(tabId) || -1;
      if (currentIndex > 0) {
        const newIndex = currentIndex - 1;
      const tabHistory = history.get(tabId) || [];
        const historyCommand = tabHistory[tabHistory.length - 1 - newIndex];
        setCommandInput(prev => new Map(prev).set(tabId, historyCommand));
      setHistoryIndex(prev => new Map(prev).set(tabId, newIndex));
      } else if (currentIndex === 0) {
        setCommandInput(prev => new Map(prev).set(tabId, ''));
        setHistoryIndex(prev => new Map(prev).set(tabId, -1));
      }
    } else if (e.ctrlKey && (e.key === 'c' || e.key === 'C')) {
        e.preventDefault();
      const wsService = wsServices.current.get(tabId);
      if (wsService && isCommandExecuting.get(tabId)) {
        wsService.sendCommand('\u0003');
        addMessage(tabId, 'system', '(^C) - Commande interrompue');
        setIsCommandExecuting(prev => new Map(prev).set(tabId, false));
        setCommandInput(prev => new Map(prev).set(tabId, ''));
        setTimeout(() => inputRefs.current.get(tabId)?.focus(), 50);
      }
    }
  };

  const clearTerminal = (tabId: string) => {
    setMessages(prev => new Map(prev).set(tabId, []));
    setCommandInput(prev => new Map(prev).set(tabId, ''));
    setTimeout(() => inputRefs.current.get(tabId)?.focus(), 0);
  };

  const sendPagerAction = (tabId: string, action: 'page' | 'line' | 'quit') => {
    const wsService = wsServices.current.get(tabId);
    if (!wsService) return;
    wsService.sendMessage({ type: 'pager_action', action });
    if (action === 'quit') {
      setPagerWaiting(prev => new Map(prev).set(tabId, false));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 border-2 border-purple-400 opacity-20"></div>
          </div>
          <p className="mt-4 text-slate-600 text-lg font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <style>
        {`
          .terminal-scroll {
            height: calc(100vh - 200px) !important;
            max-height: calc(100vh - 200px) !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            border: 1px solid #4B5563 !important;
            scrollbar-width: thin !important;
            scrollbar-color: #4B5563 #1F2937 !important;
          }
          
          .terminal-scroll::-webkit-scrollbar {
            width: 8px !important;
          }
          
          .terminal-scroll::-webkit-scrollbar-track {
            background: #1F2937 !important;
          }
          
          .terminal-scroll::-webkit-scrollbar-thumb {
            background: #4B5563 !important;
            border-radius: 4px !important;
          }
          
          .terminal-scroll::-webkit-scrollbar-thumb:hover {
            background: #6B7280 !important;
          }
        `}
      </style>
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-black text-white flex flex-col overflow-hidden">
      {/* Header avec glassmorphism */}
      <div className="bg-black/80 backdrop-blur-lg border-b border-slate-700/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-3 rounded-xl shadow-lg">
              <TerminalIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <div className="text-2xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
                Terminal SSH
              </div>
              <div className="text-slate-400 text-lg">Sessions de connexion sécurisées</div>
            </div>
          </div>
          <button 
            onClick={() => setShowFirewallSelector(true)}
            className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl hover:from-green-700 hover:to-emerald-700 font-semibold flex items-center gap-3 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
          >
            <Plus className="h-5 w-5" />
            Nouveau Terminal
          </button>
        </div>
      </div>

      {/* Firewall Selector Modal */}
      {showFirewallSelector && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900/95 backdrop-blur-lg rounded-2xl border border-slate-700/50 shadow-2xl max-w-md w-full transform transition-all duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
                  Sélectionner un pare-feu
                </h3>
                <button
                  onClick={() => setShowFirewallSelector(false)}
                  className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-all duration-200"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {firewalls.length > 0 ? (
                  firewalls.map((firewall) => (
                    <button
                      key={firewall.id}
                      onClick={() => addTab(firewall)}
                      className="w-full p-4 text-left bg-slate-800/80 backdrop-blur-sm hover:bg-slate-700/80 rounded-xl flex items-center space-x-4 transition-all duration-200 border border-slate-700/50 hover:border-slate-600/50"
                    >
                      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-3 rounded-lg shadow-lg">
                        <Monitor className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-white text-lg">{firewall.name}</div>
                        <div className="text-slate-400 text-sm">{firewall.ip_address}</div>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <div className="bg-gradient-to-r from-slate-700 to-slate-800 p-4 rounded-xl mx-auto mb-4 w-16 h-16 flex items-center justify-center">
                      <Monitor className="h-8 w-8 text-slate-400" />
                    </div>
                    <div className="text-slate-400 text-lg font-medium">Aucun pare-feu disponible</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      {tabs.length > 0 && (
        <div className="bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50">
          <div className="flex overflow-x-auto">
            {tabs.map((tab) => (
              <div
                key={tab.id}
                className={`flex items-center space-x-4 px-6 py-4 border-r border-slate-700/50 cursor-pointer min-w-0 transition-all duration-200 ${
                  activeTabId === tab.id 
                    ? 'bg-slate-800/80 backdrop-blur-sm border-b-2 border-green-500 shadow-lg' 
                    : 'bg-slate-900/60 hover:bg-slate-800/60'
                }`}
                onClick={() => setActiveTabId(tab.id)}
              >
                <div className={`w-3 h-3 rounded-full ${tab.isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-sm font-semibold text-white">{tab.firewallName}</span>
                <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-lg">{tab.firewallIp}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeTab(tab.id);
                  }}
                  className="text-slate-400 hover:text-red-400 p-2 rounded-lg hover:bg-slate-700/50 transition-all duration-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Terminal Content */}
      {activeTabId && tabs.find(t => t.id === activeTabId) ? (
        <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50 p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
              {!tabs.find(t => t.id === activeTabId)?.isConnected ? (
                <button 
                  onClick={() => connectToTerminal(activeTabId)} 
                  className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 text-sm font-medium shadow-lg hover:shadow-xl transition-all duration-200"
                >
                Se connecter
            </button>
          ) : (
            <button 
                  onClick={() => disconnectTerminal(activeTabId)} 
                  className="px-4 py-2 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-lg hover:from-red-700 hover:to-pink-700 text-sm font-medium shadow-lg hover:shadow-xl transition-all duration-200"
            >
                  Déconnecter
            </button>
          )}
              <button 
                onClick={() => clearTerminal(activeTabId)} 
                className="px-4 py-2 bg-slate-700/80 backdrop-blur-sm text-white rounded-lg hover:bg-slate-600/80 text-sm font-medium transition-all duration-200"
              >
                Effacer
              </button>
            </div>
                        <div className="flex items-center space-x-3">
              <div className="text-xs text-slate-300">
                {isCommandExecuting.get(activeTabId) ? (
                  <span className="bg-gradient-to-r from-red-600 to-pink-600 px-3 py-1 rounded-lg font-medium">Commande en cours...</span>
                ) : (
                  <span className="bg-gradient-to-r from-green-600 to-emerald-600 px-3 py-1 rounded-lg font-medium">Prêt</span>
                )}
              </div>
              {pagerWaiting.get(activeTabId) && (
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-yellow-400">--More--</span>
                  <button
                    onClick={() => sendPagerAction(activeTabId, 'page')}
                    className="px-2 py-1 bg-slate-700/80 text-white rounded-lg text-xs hover:bg-slate-600/80"
                  >Espace</button>
                  <button
                    onClick={() => sendPagerAction(activeTabId, 'line')}
                    className="px-2 py-1 bg-slate-700/80 text-white rounded-lg text-xs hover:bg-slate-600/80"
                  >Entrée</button>
                  <button
                    onClick={() => sendPagerAction(activeTabId, 'quit')}
                    className="px-2 py-1 bg-slate-700/80 text-white rounded-lg text-xs hover:bg-slate-600/80"
                  >Quitter</button>
                </div>
              )}
              <button 
                onClick={() => {
                  const terminal = terminalRefs.current.get(activeTabId);
                  if (terminal) terminal.scrollTop = 0;
                }}
                className="px-3 py-1 bg-slate-700/80 backdrop-blur-sm text-white rounded-lg text-xs hover:bg-slate-600/80 transition-all duration-200"
              >
                ↑ Haut
              </button>
              <button 
                onClick={() => {
                  const terminal = terminalRefs.current.get(activeTabId);
                  if (terminal) terminal.scrollTop = terminal.scrollHeight;
                }}
                className="px-3 py-1 bg-slate-700/80 backdrop-blur-sm text-white rounded-lg text-xs hover:bg-slate-600/80 transition-all duration-200"
              >
                ↓ Bas
              </button>
            </div>
      </div>

      {/* Terminal Output */}
      <div className="flex-1 overflow-hidden bg-black">
        <div 
              className="p-4 font-mono text-sm leading-6 terminal-scroll" 
              ref={(el) => terminalRefs.current.set(activeTabId, el)}
            >
                            {/* Welcome message */}
              {messages.get(activeTabId)?.length === 0 && (
                <div className="text-gray-300">
                  Terminal connecté au pare-feu {tabs.find(t => t.id === activeTabId)?.firewallName}
                  <br /><br />
                  <div className="text-gray-400 text-xs">
                    === Terminal Ready ===
                    <br />
                    Tapez vos commandes ci-dessous...
                    <br /><br />
                    {Array.from({ length: 200 }, (_, i) => (
                      <div key={i} className="text-gray-500">
                        Ligne {i + 1} - Espace pour défilement... {i % 20 === 0 ? '🚀' : i % 10 === 0 ? '⚡' : i % 5 === 0 ? '🔥' : ''}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Messages */}
              {messages.get(activeTabId)?.map((msg, i) => (
                <div key={i} className={`${
                  msg.type === 'command' ? 'text-green-400 font-semibold' :
                  msg.type === 'error' ? 'text-red-400' :
                  msg.type === 'system' ? 'text-yellow-400' :
                  'text-gray-200'
                }`} style={{ whiteSpace: 'pre-wrap' }}>
                  {msg.content}
          </div>
              ))}

              {/* Command Input */}
              <div className="flex items-center mt-2">
                <span className="mr-3 font-mono font-bold text-green-400">C:&gt;</span>
                <input
                  ref={(el) => inputRefs.current.set(activeTabId, el)}
                  type="text"
                  value={commandInput.get(activeTabId) || ''}
                  onChange={(e) => setCommandInput(prev => new Map(prev).set(activeTabId, e.target.value))}
                  onKeyDown={(e) => handleKeyDown(activeTabId, e)}
                  disabled={!tabs.find(t => t.id === activeTabId)?.isConnected}
                  className="flex-1 bg-transparent text-white outline-none border-none font-mono"
                  placeholder={tabs.find(t => t.id === activeTabId)?.isConnected ? 'Tapez votre commande...' : "Se connecter d'abord..."}
                  autoCapitalize="off"
                  autoCorrect="off"
                  spellCheck={false}
                />
                  </div>
              </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-slate-900 via-gray-900 to-black">
          <div className="bg-slate-900/80 backdrop-blur-lg rounded-2xl border border-slate-700/50 shadow-2xl p-12 text-center">
            <div className="relative">
              <div className="bg-gradient-to-r from-slate-700 to-slate-800 p-6 rounded-2xl mx-auto mb-6 w-24 h-24 flex items-center justify-center">
                <TerminalIcon className="h-12 w-12 text-slate-400" />
              </div>
              <div className="absolute inset-0 animate-ping rounded-full w-24 h-24 bg-slate-400 opacity-20"></div>
            </div>
            <h3 className="text-2xl font-bold text-white mb-3">Aucun terminal ouvert</h3>
            <p className="text-slate-400 text-lg mb-8">Ouvrez un terminal pour vous connecter à vos pare-feu</p>
            <button
              onClick={() => setShowFirewallSelector(true)}
              className="px-8 py-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl hover:from-green-700 hover:to-emerald-700 font-semibold flex items-center gap-3 mx-auto shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
            >
              <Plus className="h-5 w-5" />
              Ouvrir un terminal
            </button>
          </div>
        </div>
      )}
    </div>
    </>
  );
};

export default TerminalTabs;

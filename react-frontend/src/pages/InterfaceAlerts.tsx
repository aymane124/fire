import React, { useEffect, useMemo, useState } from 'react';
import { interfaceAlertService, CreateAlertPayload } from '../services/interfaceAlertService';
import { firewallService, Firewall } from '../services/firewallService';
import api from '../utils/axiosConfig';
import { userService, User } from '../services/userService';
import { 
  InterfaceAlert, 
  InterfaceStatus, 
  AlertExecution, 
  MonitoringStats 
} from '../types/interfaceMonitor';
import { 
  Play, 
  ToggleLeft, 
  ToggleRight, 
  RefreshCw, 
  Plus, 
  Trash2, 
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  Settings
} from 'lucide-react';
import toast from 'react-hot-toast';

const InterfaceAlerts: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState<InterfaceAlert[]>([]);
  const [executions, setExecutions] = useState<AlertExecution[]>([]);
  const [firewalls, setFirewalls] = useState<Firewall[]>([]);
  const firewallsByTypeCount = useMemo(() => {
    const counts = new Map<string, number>();
    for (const fw of firewalls) {
      const typeName = typeof fw.firewall_type === 'string' ? fw.firewall_type : (fw.firewall_type as any)?.name;
      const key = (typeName || '').toString();
      if (!key) continue;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return counts;
  }, [firewalls]);
  const [users, setUsers] = useState<User[]>([]);
  const [fwTypes, setFwTypes] = useState<Array<{ id: string; name: string }>>([]);
  const uniqueFwTypes = useMemo(() => {
    const seen = new Set<string>();
    const list: Array<{ id: string; name: string }> = [];
    for (const t of fwTypes) {
      if (t?.name && !seen.has(t.name)) {
        seen.add(t.name);
        list.push(t);
      }
    }
    return list;
  }, [fwTypes]);
  const [stats, setStats] = useState<MonitoringStats | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [serviceAvailable, setServiceAvailable] = useState(true);

  const [form, setForm] = useState<CreateAlertPayload>({
    name: '',
    description: '',
    firewall: '',
    firewall_type: '',
    alert_type: 'interface_down',
    check_interval: 300, // 5 minutes in seconds
    threshold_value: undefined,
    command_template: 'show system interface',
    conditions: {},
    recipients: [],
    include_admin: true,
    include_superuser: true
  });

  // UI helpers for advanced conditions
  const [commandsText, setCommandsText] = useState<string>("config global\nget system interface");
  
  // Multiple firewall selection
  const [selectedFirewalls, setSelectedFirewalls] = useState<string[]>([]);

  const dedupedFirewalls = useMemo(() => {
    const map = new Map<string, Firewall>();
    for (const fw of firewalls) {
      if (!map.has(fw.ip_address)) map.set(fw.ip_address, fw);
    }
    return Array.from(map.values());
  }, [firewalls]);

  const ensureArray = (data: any) => (Array.isArray(data) ? data : (data?.results || data?.items || data?.data || []));

  const loadAll = async () => {
    setLoading(true);
    try {
      // Fetch all firewalls (try all_firewalls endpoint, else paginate)
      const fetchAllFirewalls = async (): Promise<Firewall[]> => {
        try {
          const res = await api.get('/firewalls/firewalls/all_firewalls/');
          const arr = Array.isArray(res.data) ? res.data : (res.data?.results || []);
          return arr as Firewall[];
        } catch {
          // Fallback to paginated list
          let all: Firewall[] = [];
          let next: string | null = '/firewalls/firewalls/';
          while (next) {
            const resPage: any = await api.get(next);
            const pageData: any = resPage.data;
            const items: Firewall[] = (pageData?.results || []) as Firewall[];
            all = all.concat(items);
            next = (pageData?.next as string) || null;
          }
          return all;
        }
      };

      const [alertsData, executionsData, firewallsData, usersData, statsData] = await Promise.all([
        interfaceAlertService.list(),
        interfaceAlertService.logs(),
        fetchAllFirewalls(),
        userService.getActiveUsers(),
        interfaceAlertService.getMonitoringStats()
      ]);
      setAlerts(ensureArray(alertsData));
      setExecutions(ensureArray(executionsData));
      setFirewalls(ensureArray(firewallsData));
      setUsers(ensureArray(usersData));
      setStats(statsData);
      setServiceAvailable(true);
      try {
        const types = await firewallService.getFirewallTypes();
        setFwTypes(types || []);
      } catch {}
    } catch (e: any) {
      if (e.message?.includes('Service not available')) {
        setServiceAvailable(false);
        setAlerts([]);
        setExecutions([]);
        setStats(null);
      } else {
      toast.error(e?.message || 'Erreur chargement');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const submit = async () => {
    try {
      if (!form.name || !form.alert_type || !form.check_interval) {
        toast.error('Champs requis manquants');
        return;
      }

      // Build minimal conditions: only commands
      const conditions: Record<string, any> = {};
      const cmdList = commandsText
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter((l) => l.length > 0);
      if (cmdList.length > 0) {
        conditions.commands = cmdList;
      }

      const payload: CreateAlertPayload = {
        name: form.name,
        description: form.description,
        firewall: form.firewall, // default single firewall; overridden when multiple selected
        firewall_type: (form.firewall_type || '').trim() || undefined,
        alert_type: form.alert_type,
        check_interval: 300, // fixed 5 minutes
        threshold_value: form.threshold_value,
        command_template: form.command_template,
        conditions: {
          ...conditions,
          ...(form.conditions || {})
        },
        recipients: form.recipients,
        include_admin: form.include_admin,
        include_superuser: form.include_superuser
      };

      const hasTargets = (selectedFirewalls.length > 0) || !!form.firewall || !!(form.firewall_type && form.firewall_type.trim());
      if (!hasTargets) {
        toast.error('Définissez une cible: sélection multiple, pare-feu unique, ou type');
        return;
      }

      const createdAlerts: any[] = [];
      if (selectedFirewalls.length > 0) {
        // Create ONE alert targeting multiple firewalls via M2M
        const onePayload = { ...payload, firewalls: selectedFirewalls } as any;
        try {
          const created = await interfaceAlertService.create(onePayload);
          createdAlerts.push(created);
        } catch (e: any) {
          toast.error('Erreur création (sélection multiple)');
        }
      } else if (form.firewall) {
        const perFwPayload = { ...payload, firewall: form.firewall } as any;
        try {
          const created = await interfaceAlertService.create(perFwPayload);
          createdAlerts.push(created);
        } catch (e: any) {
          toast.error('Erreur création (pare-feu unique)');
        }
      } else {
        try {
          const created = await interfaceAlertService.create(payload);
          createdAlerts.push(created);
        } catch (e: any) {
          toast.error('Erreur création (type de pare-feu)');
        }
      }
      if (createdAlerts.length > 0) {
        setAlerts((prev) => [...createdAlerts, ...ensureArray(prev)] as any);
        toast.success(`${createdAlerts.length} alerte(s) créée(s) avec succès`);
      }
      setForm({
        name: '',
        description: '',
        firewall: '',
        firewall_type: '',
        alert_type: 'interface_down',
        check_interval: 300,
        threshold_value: undefined,
        command_template: 'show system interface',
        conditions: {},
        recipients: [],
        include_admin: true,
        include_superuser: true
      });
      setCommandsText('config global\nget system interface');
      setSelectedFirewalls([]);
      setShowForm(false);
    } catch (e: any) {
      toast.error(e?.message || 'Erreur création');
    }
  };

  const toggle = async (alert: InterfaceAlert) => {
    try {
      const updated = await interfaceAlertService.toggleActive(alert.id);
      setAlerts((prev) => ensureArray(prev).map((a: any) => (a.id === alert.id ? updated : a)) as any);
      toast.success(alert.is_active ? 'Alerte désactivée' : 'Alerte activée');
    } catch (e: any) {
      toast.error(e?.message || 'Erreur action');
    }
  };

  const testAlert = async (alert: InterfaceAlert) => {
    try {
      await interfaceAlertService.test(alert.id);
      toast.success('Test d\'alerte lancé');
      // Reload executions to show the new test
      setTimeout(() => loadAll(), 2000);
    } catch (e: any) {
      toast.error(e?.message || 'Erreur test');
    }
  };

  const remove = async (alert: InterfaceAlert) => {
    try {
      await interfaceAlertService.remove(alert.id);
      setAlerts((prev) => ensureArray(prev).filter((a: any) => a.id !== alert.id) as any);
      toast.success('Alerte supprimée');
    } catch (e: any) {
      toast.error(e?.message || 'Erreur suppression');
    }
  };

  const formatInterval = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}j`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'up': return 'text-green-600';
      case 'down': return 'text-red-600';
      case 'error': return 'text-red-500';
      case 'warning': return 'text-yellow-600';
      default: return 'text-slate-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'up': return <CheckCircle size={16} className="text-green-600" />;
      case 'down': return <AlertTriangle size={16} className="text-red-600" />;
      case 'error': return <AlertTriangle size={16} className="text-red-500" />;
      case 'warning': return <AlertTriangle size={16} className="text-yellow-600" />;
      default: return <Clock size={16} className="text-slate-500" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Service Status Banner */}
      {!serviceAvailable && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} className="text-yellow-600" />
            <div>
              <h3 className="text-sm font-medium text-yellow-800">
                Service Interface Monitor non disponible
              </h3>
              <p className="text-sm text-yellow-700 mt-1">
                Le service de surveillance des interfaces est temporairement indisponible. 
                Les fonctionnalités d'alerte ne sont pas accessibles pour le moment.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
        <h1 className="text-2xl font-bold text-slate-800">Gestion des alertes d'interfaces</h1>
          <p className="text-slate-600 mt-1">Surveillance des interfaces des pare-feux FortiGate</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => setShowForm(!showForm)} 
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!serviceAvailable}
          >
            <Plus size={16}/> {showForm ? 'Annuler' : 'Nouvelle alerte'}
          </button>
        <button onClick={loadAll} className="px-3 py-2 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 flex items-center gap-2">
          <RefreshCw size={16}/> Rafraîchir
        </button>
      </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600">Total Alertes</p>
                <p className="text-2xl font-bold text-slate-800">{stats.total_alerts}</p>
              </div>
              <div className="p-2 bg-blue-100 rounded-lg">
                <AlertTriangle size={20} className="text-blue-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600">Alertes Actives</p>
                <p className="text-2xl font-bold text-green-600">{stats.active_alerts}</p>
              </div>
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle size={20} className="text-green-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600">Exécutions 24h</p>
                <p className="text-2xl font-bold text-slate-800">{stats.last_24h_executions}</p>
              </div>
              <div className="p-2 bg-purple-100 rounded-lg">
                <Clock size={20} className="text-purple-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600">Emails Envoyés</p>
                <p className="text-2xl font-bold text-slate-800">{stats.total_emails_sent}</p>
              </div>
              <div className="p-2 bg-orange-100 rounded-lg">
                <Users size={20} className="text-orange-600" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create form */}
      {showForm && serviceAvailable && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="font-semibold mb-4 text-lg">Créer une nouvelle alerte</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Nom de l'alerte *</label>
              <input 
                className="w-full border rounded-lg p-3" 
                placeholder="Ex: Surveillance interfaces RABAT"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Type d'alerte *</label>
              <select 
                className="w-full border rounded-lg p-3"
                value={form.alert_type}
                onChange={(e) => setForm((f) => ({ ...f, alert_type: e.target.value as any }))}
              >
                <option value="interface_down">Interface Down</option>
                <option value="interface_up">Interface Up</option>
                <option value="bandwidth_high">Bande passante élevée</option>
                <option value="error_count">Compteur d'erreurs</option>
                <option value="custom">Personnalisé</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-2">Pare-feux (sélection multiple)</label>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 max-h-44 overflow-auto border rounded-lg p-3">
                {dedupedFirewalls.map((fw) => {
                  const selected = selectedFirewalls.includes(fw.id);
                  return (
                    <button
                      key={fw.id}
                      type="button"
                      className={`text-left p-2 rounded border ${selected ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:bg-slate-50'}`}
                      onClick={() => {
                        setSelectedFirewalls((prev) => {
                          const list = [...prev];
                          const idx = list.indexOf(fw.id);
                          if (idx >= 0) { list.splice(idx, 1); } else { list.push(fw.id); }
                          return list;
                        });
                      }}
                    >
                      <div className="font-medium">{fw.name}</div>
                      <div className="text-xs text-slate-500">{fw.ip_address}</div>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-1">Astuce: Si vous laissez vide, le champ unique Pare-feu sera utilisé (ci-dessous).</p>
              <div className="mt-3">
                <label className="block text-sm font-medium text-slate-700 mb-2">Pare-feu (optionnel, si un seul)</label>
                <select
                  className="w-full border rounded-lg p-3"
                  value={form.firewall}
                  onChange={(e) => setForm((f) => ({ ...f, firewall: e.target.value }))}
                >
                  <option value="">Sélectionner un pare-feu</option>
                  {dedupedFirewalls.map((fw) => (
                    <option key={fw.id} value={fw.id}>
                      {fw.name} ({fw.ip_address})
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-3">
                <label className="block text-sm font-medium text-slate-700 mb-2">Type de pare-feu (optionnel)</label>
                <select
                  className="w-full border rounded-lg p-3"
                  value={form.firewall_type || ''}
                  onChange={(e) => setForm((f) => ({ ...f, firewall_type: e.target.value }))}
                >
                  <option value="">Sélectionner un type</option>
                  {uniqueFwTypes.map((t) => {
                    const c = firewallsByTypeCount.get(t.name) || 0;
                    return (
                      <option key={t.id} value={t.name}>{t.name} ({c})</option>
                    );
                  })}
                </select>
                <p className="text-xs text-slate-500 mt-1">Si défini, l'alerte s'exécutera sur tous les pare-feux de ce type.</p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Intervalle de vérification</label>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <span className="px-2 py-1 rounded bg-slate-100 border">5 minutes (fixe)</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Valeur seuil</label>
              <input 
                className="w-full border rounded-lg p-3" 
                type="number" 
                placeholder="Ex: 1000 (pour bande passante)"
                value={form.threshold_value || ''}
                onChange={(e) => setForm((f) => ({ ...f, threshold_value: e.target.value ? Number(e.target.value) : undefined }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Commande</label>
              <input 
                className="w-full border rounded-lg p-3" 
                placeholder="show system interface"
                value={form.command_template}
                onChange={(e) => setForm((f) => ({ ...f, command_template: e.target.value }))}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-2">Description</label>
            <textarea
                className="w-full border rounded-lg p-3" 
                placeholder="Description de l'alerte"
              rows={3}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          {/* Advanced conditions: commands, parse_from, mappings */}
          {/* Commands only (simplified parser) */}
          <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Commandes (une par ligne)</label>
              <textarea
                className="w-full border rounded-lg p-3 font-mono"
                rows={6}
                placeholder={`config global\nget system interface`}
                value={commandsText}
                onChange={(e) => setCommandsText(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Options d'email</label>
              <div className="flex items-center gap-2">
                <input
                  id="aggregate_email"
                  type="checkbox"
                  checked={Boolean((form as any).conditions?.aggregate_email)}
                  onChange={(e) => setForm((f) => ({
                    ...f,
                    conditions: {
                      ...(f.conditions || {}),
                      aggregate_email: e.target.checked
                    }
                  }))}
                />
                <label htmlFor="aggregate_email" className="text-sm text-slate-700">Envoyer un seul email cumulatif</label>
              </div>
              <p className="text-xs text-slate-500 mt-1">Cochez pour recevoir un email unique regroupant les résultats de tous les pare-feux ciblés.</p>
            </div>
          </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-2">Destinataires</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 max-h-44 overflow-auto border rounded-lg p-3">
                {users.map((user) => {
                  const selected = form.recipients.includes(user.id);
                return (
                    <button 
                      key={user.id}
                      type="button"
                          className={`text-left p-2 rounded border ${selected ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:bg-slate-50'}`}
                          onClick={() => {
                            setForm((f) => {
                          const list = [...f.recipients];
                          const idx = list.indexOf(user.id);
                          if (idx >= 0) { 
                            list.splice(idx, 1); 
                          } else { 
                            list.push(user.id); 
                          }
                          return { ...f, recipients: list };
                        });
                      }}
                    >
                      <div className="font-medium">{user.username}</div>
                      <div className="text-xs text-slate-500">{user.email}</div>
                  </button>
                );
              })}
            </div>
          </div>
            <div className="md:col-span-2 flex gap-4">
              <label className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  checked={form.include_admin}
                  onChange={(e) => setForm((f) => ({ ...f, include_admin: e.target.checked }))}
                />
                <span className="text-sm text-slate-700">Inclure les administrateurs</span>
              </label>
              <label className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  checked={form.include_superuser}
                  onChange={(e) => setForm((f) => ({ ...f, include_superuser: e.target.checked }))}
                />
                <span className="text-sm text-slate-700">Inclure les super-utilisateurs</span>
              </label>
            </div>
            <div className="md:col-span-2 flex justify-end gap-3">
              <button 
                onClick={() => setShowForm(false)} 
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg"
              >
                Annuler
              </button>
              <button 
                onClick={submit} 
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2"
              >
                <Plus size={16}/> Créer l'alerte
            </button>
          </div>
        </div>
      </div>
      )}

      {/* Alerts table */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h2 className="font-semibold mb-4 text-lg">Alertes configurées</h2>
        {!serviceAvailable ? (
          <div className="text-center py-8 text-slate-500">
            <AlertTriangle size={48} className="mx-auto mb-4 text-slate-300" />
            <p>Service non disponible</p>
          </div>
        ) : (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
                <tr className="text-left text-slate-600 border-b">
                  <th className="p-3">Nom</th>
                  <th className="p-3">Pare-feu</th>
                  <th className="p-3">Portée</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Statut</th>
                  <th className="p-3">Intervalle</th>
                  <th className="p-3">Dernière vérif</th>
                  <th className="p-3">Prochaine vérif</th>
                  <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
                {ensureArray(alerts).map((alert: InterfaceAlert) => (
                  <tr key={alert.id} className="border-b hover:bg-slate-50">
                    <td className="p-3">
                      <div>
                        <div className="font-medium">{alert.name}</div>
                        {alert.description && (
                          <div className="text-xs text-slate-500">{alert.description}</div>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <div>
                        {alert.firewalls && alert.firewalls.length > 0 ? (
                          <div className="space-y-1">
                            <div className="font-medium">{alert.firewalls.length} pare-feux</div>
                            <div className="flex flex-wrap gap-1">
                              {alert.firewalls.slice(0, 3).map((fw) => (
                                <span key={fw.id} className="px-2 py-0.5 text-xs rounded bg-slate-100 text-slate-700">{fw.name}</span>
                              ))}
                              {alert.firewalls.length > 3 && (
                                <span className="px-2 py-0.5 text-xs rounded bg-slate-50 text-slate-500">+{alert.firewalls.length - 3} autres</span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div>
                            <div className="font-medium">{alert.firewall?.name || '—'}</div>
                            <div className="text-xs text-slate-500">{alert.firewall?.ip_address || ''}</div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      {alert.firewall_type ? (
                        <span className="px-2 py-1 text-xs rounded bg-slate-100 text-slate-700">type: {alert.firewall_type}</span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                        {alert.alert_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(alert.last_status)}
                        <span className={getStatusColor(alert.last_status)}>
                          {alert.last_status}
                        </span>
                      </div>
                    </td>
                    <td className="p-3">{formatInterval(alert.check_interval)}</td>
                    <td className="p-3">
                      {alert.last_check ? new Date(alert.last_check).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      {alert.next_check ? new Date(alert.next_check).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <button 
                          onClick={() => testAlert(alert)} 
                          className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1"
                          title="Tester l'alerte"
                        >
                          <Play size={14}/> Test
                        </button>
                        <button 
                          onClick={() => toggle(alert)} 
                          className="px-2 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 flex items-center gap-1"
                          title={alert.is_active ? 'Désactiver' : 'Activer'}
                        >
                          {alert.is_active ? <><ToggleRight size={14}/> Désactiver</> : <><ToggleLeft size={14}/> Activer</>}
                        </button>
                        <button 
                          onClick={() => remove(alert)} 
                          className="px-2 py-1 rounded bg-red-600 hover:bg-red-700 text-white flex items-center gap-1"
                          title="Supprimer"
                        >
                          <Trash2 size={14}/> Supprimer
                    </button>
                      </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {/* Recent executions */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h2 className="font-semibold mb-4 text-lg">Exécutions récentes</h2>
        {!serviceAvailable ? (
          <div className="text-center py-8 text-slate-500">
            <AlertTriangle size={48} className="mx-auto mb-4 text-slate-300" />
            <p>Service non disponible</p>
          </div>
        ) : (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
                <tr className="text-left text-slate-600 border-b">
                  <th className="p-3">Date</th>
                  <th className="p-3">Alerte</th>
                  <th className="p-3">Statut</th>
                  <th className="p-3">Interfaces vérifiées</th>
                  <th className="p-3">Alertes déclenchées</th>
                  <th className="p-3">Emails envoyés</th>
                  <th className="p-3">Durée</th>
              </tr>
            </thead>
            <tbody>
                {ensureArray(executions).slice(0, 10).map((exec: AlertExecution) => (
                  <tr key={exec.id} className="border-b hover:bg-slate-50">
                    <td className="p-3">{new Date(exec.started_at).toLocaleString()}</td>
                    <td className="p-3">
                      {alerts.find(a => a.id === exec.alert)?.name || 'N/A'}
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        exec.status === 'completed' ? 'bg-green-100 text-green-800' :
                        exec.status === 'failed' ? 'bg-red-100 text-red-800' :
                        exec.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        'bg-slate-100 text-slate-800'
                      }`}>
                        {exec.status}
                      </span>
                    </td>
                    <td className="p-3">{exec.interfaces_checked}</td>
                    <td className="p-3">{exec.alerts_triggered}</td>
                    <td className="p-3">{exec.emails_sent}</td>
                    <td className="p-3">
                      {exec.duration ? `${exec.duration.toFixed(2)}s` : '-'}
                    </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  );
};

export default InterfaceAlerts;

import React, { useState, useEffect } from 'react';
import api from '../utils/axiosConfig';

interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface Firewall {
  id: string;
  name: string;
  ip_address: string;
  firewall_type: {
    id: string;
    name: string;
    description?: string;
  };
  owner: {
    id: string;
    username: string;
    email: string;
  };
}

interface Command {
  command: string;
  type: string;
  description?: string;
}

interface CommandTemplate {
  id: string;
  command: string;
  command_type: string;
  description?: string;
  created_at: string;
}

interface EmailSchedule {
  id: string;
  name: string;
  description: string;
  send_time: string;
  timezone: string;
  recipients?: User[];
  include_all_users: boolean;
  email_subject: string;
  email_template: string;
  firewalls?: Firewall[];
  commands_to_execute?: Command[];
  is_active: boolean;
  last_sent: string | null;
  next_send: string | null;
  created_at: string;
  recipients_count: number;
  firewalls_count: number;
  last_execution_status: string | null;
}

interface EmailExecution {
  id: string;
  execution_time: string;
  status: string;
  emails_sent: number;
  emails_failed: number;
  commands_executed: number;
  commands_failed: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

const AutomatedEmailManager: React.FC = () => {
  const [schedules, setSchedules] = useState<EmailSchedule[]>([]);
  const [executions, setExecutions] = useState<EmailExecution[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [firewalls, setFirewalls] = useState<Firewall[]>([]);
  const [templates, setTemplates] = useState<CommandTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<EmailSchedule | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [editLoading, setEditLoading] = useState(false);

  // État du formulaire de création
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    send_time: '09:00',
    timezone: 'UTC',
    email_subject: '',
    email_template: '',
    include_all_users: false,
    recipient_ids: [] as string[],
    firewall_ids: [] as string[],
    commands_to_execute: [] as Command[]
  });

  const addTemplateToForm = (tpl: CommandTemplate) => {
    const newCmd: Command = {
      command: tpl.command,
      type: tpl.command_type || 'general',
      description: tpl.description || ''
    };
    const exists = formData.commands_to_execute.some(
      c => c.command === newCmd.command && c.type === newCmd.type
    );
    if (exists) return;
    setFormData({
      ...formData,
      commands_to_execute: [...formData.commands_to_execute, newCmd]
    });
  };

     useEffect(() => {
     // Vérifier l'authentification au chargement
     const token = localStorage.getItem('token');
     const role = localStorage.getItem('role');
     
     if (!token) {
       console.error('Aucun token d\'authentification trouvé');
       alert('Vous devez être connecté pour accéder à cette page.');
       return;
     }
     
     if (role !== 'admin') {
       console.error('Accès non autorisé - rôle requis: admin');
       alert('Vous devez être administrateur pour accéder à cette page.');
       return;
     }
     
     // Configurer l'authentification pour toutes les requêtes
     api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
     
     fetchData();
   }, []);

     const fetchData = async () => {
     setLoading(true);
     try {
       console.log('Début du chargement des données...');
       
       const [schedulesRes, usersRes, firewallsRes, templatesRes] = await Promise.all([
         api.get('email/schedules/'),
         api.get('auth/users/'),
         api.get('firewalls/firewalls/all_firewalls/'),
         api.get('email/command-templates/')
       ]);
       
       console.log('Réponses API:', {
         schedules: schedulesRes.data,
         users: usersRes.data,
         firewalls: firewallsRes.data,
         templates: templatesRes.data
       });
       
       // S'assurer que nous avons des tableaux
       const schedulesData = Array.isArray(schedulesRes.data) ? schedulesRes.data : schedulesRes.data?.results || [];
       const usersData = Array.isArray(usersRes.data) ? usersRes.data : usersRes.data?.results || [];
       const firewallsData = Array.isArray(firewallsRes.data) ? firewallsRes.data : firewallsRes.data?.results || [];
       const templatesData = Array.isArray(templatesRes.data) ? templatesRes.data : templatesRes.data?.results || [];
       
       console.log('Données traitées:', {
         schedules: schedulesData,
         users: usersData,
         firewalls: firewallsData,
         templates: templatesData
       });
       
       setSchedules(schedulesData);
       setUsers(usersData);
       setFirewalls(firewallsData);
       setTemplates(templatesData);
     } catch (error: any) {
       console.error('Erreur lors du chargement des données:', error);
       console.error('Détails de l\'erreur:', {
         message: error.message,
         response: error.response?.data,
         status: error.response?.status
       });
       // En cas d'erreur, initialiser avec des tableaux vides
       setSchedules([]);
       setUsers([]);
       setFirewalls([]);
     } finally {
       setLoading(false);
     }
   };

     const handleCreateSchedule = async (e: React.FormEvent) => {
     e.preventDefault();
     
     // Validation
     if (formData.firewall_ids.length === 0) {
       alert('Veuillez sélectionner au moins un firewall.');
       return;
     }
     
     if (!formData.include_all_users && formData.recipient_ids.length === 0) {
       alert('Veuillez sélectionner au moins un destinataire ou cocher "Inclure tous les utilisateurs".');
       return;
     }
     
     // Vérifier l'authentification
     const token = localStorage.getItem('token');
     if (!token) {
       alert('Vous devez être connecté pour créer un planning.');
       return;
     }
     
     setLoading(true);
     
     try {
       const response = await api.post('email/schedules/', formData);
       setSchedules([...schedules, response.data]);
       setShowCreateForm(false);
       resetForm();
     } catch (error) {
       console.error('Erreur lors de la création du planning:', error);
       alert('Erreur lors de la création du planning. Veuillez réessayer.');
     } finally {
       setLoading(false);
     }
   };

     const handleExecuteSchedule = async (scheduleId: string) => {
     try {
       await api.post(`email/schedules/${scheduleId}/execute_now/`);
       alert('Exécution démarrée avec succès !');
       fetchData(); // Rafraîchir pour voir les nouvelles exécutions
     } catch (error) {
       console.error('Erreur lors de l\'exécution:', error);
     }
   };

     const handleToggleActive = async (scheduleId: string) => {
     try {
       const response = await api.post(`email/schedules/${scheduleId}/toggle_active/`);
       setSchedules(schedules.map(s => 
         s.id === scheduleId 
           ? { ...s, is_active: response.data.is_active }
           : s
       ));
     } catch (error) {
       console.error('Erreur lors du changement de statut:', error);
     }
   };

     const handleDeleteSchedule = async (scheduleId: string) => {
     if (!window.confirm('Êtes-vous sûr de vouloir supprimer ce planning ? Cette action est irréversible.')) {
       return;
     }
     
     try {
       await api.delete(`email/schedules/${scheduleId}/`);
       setSchedules(schedules.filter(s => s.id !== scheduleId));
       alert('Planning supprimé avec succès !');
     } catch (error) {
       console.error('Erreur lors de la suppression:', error);
       alert('Erreur lors de la suppression du planning. Veuillez réessayer.');
     }
   };

     const handleEditSchedule = async (schedule: EmailSchedule) => {
    try {
      setEditLoading(true);
      const res = await api.get(`email/schedules/${schedule.id}/`);
      const full = res.data as EmailSchedule;
      setSelectedSchedule(full);
      setFormData({
        name: full.name,
        description: full.description,
        send_time: full.send_time,
        timezone: full.timezone,
        email_subject: full.email_subject,
        email_template: full.email_template,
        include_all_users: full.include_all_users,
        recipient_ids: Array.isArray(full.recipients) ? full.recipients.map(r => r.id) : [],
        firewall_ids: Array.isArray(full.firewalls) ? full.firewalls.map(f => f.id) : [],
        commands_to_execute: Array.isArray(full.commands_to_execute) ? full.commands_to_execute : []
      });
      setShowEditForm(true);
    } catch (e) {
      console.error('Erreur lors du chargement du planning:', e);
      setSelectedSchedule(schedule);
      setShowEditForm(true);
    } finally {
      setEditLoading(false);
    }
  };

     const handleCancelEdit = () => {
     setShowEditForm(false);
     setSelectedSchedule(null);
     // Ne pas réinitialiser le formulaire pour préserver les données
   };

     const handleUpdateSchedule = async (e: React.FormEvent) => {
     e.preventDefault();
     
     if (!selectedSchedule) return;
     
     // Validation
     if (formData.firewall_ids.length === 0) {
       alert('Veuillez sélectionner au moins un firewall.');
       return;
     }
     
     if (!formData.include_all_users && formData.recipient_ids.length === 0) {
       alert('Veuillez sélectionner au moins un destinataire ou cocher "Inclure tous les utilisateurs".');
       return;
     }
     
     setLoading(true);
     
     try {
       const response = await api.put(`email/schedules/${selectedSchedule.id}/`, formData);
       setSchedules(schedules.map(s => 
         s.id === selectedSchedule.id ? response.data : s
       ));
       setShowEditForm(false);
       setSelectedSchedule(null);
       resetForm(); // Réinitialiser seulement après succès
       alert('Planning modifié avec succès !');
     } catch (error) {
       console.error('Erreur lors de la modification du planning:', error);
       alert('Erreur lors de la modification du planning. Veuillez réessayer.');
       // Ne pas réinitialiser en cas d'erreur pour permettre à l'utilisateur de corriger
     } finally {
       setLoading(false);
     }
   };

  const handleViewDetails = async (schedule: EmailSchedule) => {
    try {
      setDetailsLoading(true);
      const res = await api.get(`email/schedules/${schedule.id}/`);
      setSelectedSchedule(res.data as EmailSchedule);
    } catch (e) {
      console.error('Erreur lors du chargement des détails du planning:', e);
      setSelectedSchedule(schedule);
    } finally {
      setDetailsLoading(false);
    }
  };

  const addCommand = () => {
    setFormData({
      ...formData,
      commands_to_execute: [...formData.commands_to_execute, { command: '', type: 'general' }]
    });
  };

  const removeCommand = (index: number) => {
    setFormData({
      ...formData,
      commands_to_execute: formData.commands_to_execute.filter((_, i) => i !== index)
    });
  };

  const updateCommand = (index: number, field: keyof Command, value: string) => {
    const updatedCommands = [...formData.commands_to_execute];
    updatedCommands[index] = { ...updatedCommands[index], [field]: value };
    setFormData({ ...formData, commands_to_execute: updatedCommands });
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      send_time: '09:00',
      timezone: 'UTC',
      email_subject: '',
      email_template: '',
      include_all_users: false,
      recipient_ids: [],
      firewall_ids: [],
      commands_to_execute: []
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'running': return 'text-blue-600';
      case 'failed': return 'text-red-600';
      case 'pending': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

     return (
     <div className="p-6 bg-white rounded-lg shadow-lg">
       
       {/* Header */}
       <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gestionnaire d'Emails Automatiques</h1>
          <p className="text-gray-600 mt-2">
            Planifiez et gérez l'envoi automatique d'emails avec exécution de commandes sur les firewalls
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors"
        >
          Nouveau Planning
        </button>
      </div>

      {/* Liste des plannings */}
      <div className="grid gap-6 mb-8">
        {Array.isArray(schedules) && schedules.length > 0 ? (
          schedules.map((schedule) => (
            <div key={schedule.id} className="border border-gray-200 rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{schedule.name}</h3>
                  <p className="text-gray-600 mt-1">{schedule.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    schedule.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {schedule.is_active ? 'Actif' : 'Inactif'}
                  </span>
                  <button
                    onClick={() => handleToggleActive(schedule.id)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    {schedule.is_active ? 'Désactiver' : 'Activer'}
                  </button>
                </div>
              </div>

                           <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
               <div>
                 <span className="text-sm text-gray-500">Heure d'envoi</span>
                 <p className="font-medium">{schedule.send_time}</p>
               </div>
               <div>
                 <span className="text-sm text-gray-500">Destinataires</span>
                 <p className="font-medium">
                   {schedule.include_all_users ? 'Tous les utilisateurs' : `${schedule.recipients_count} utilisateur(s)`}
                 </p>
               </div>
               <div>
                 <span className="text-sm text-gray-500">Firewalls</span>
                 <p className="font-medium">{schedule.firewalls_count} firewall(s)</p>
               </div>
               <div>
                 <span className="text-sm text-gray-500">Prochain envoi</span>
                 <p className="font-medium">
                   {schedule.next_send ? new Date(schedule.next_send).toLocaleString() : 'Non programmé'}
                 </p>
               </div>
             </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleExecuteSchedule(schedule.id)}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
                >
                  Exécuter Maintenant
                </button>
                <button
                  onClick={() => handleViewDetails(schedule)}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  Voir Détails
                </button>
                <button
                  onClick={() => handleEditSchedule(schedule)}
                  className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700 transition-colors"
                >
                  Modifier
                </button>
                <button
                  onClick={() => handleDeleteSchedule(schedule.id)}
                  className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
                >
                  Supprimer
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucun planning d'email</h3>
            <p className="text-gray-500 mb-4">Commencez par créer votre premier planning d'email automatique.</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
            >
              Créer le premier planning
            </button>
          </div>
        )}
      </div>

      {/* Modal de création */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="relative bg-white rounded-lg p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              aria-label="Fermer"
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              onClick={() => setShowCreateForm(false)}
            >
              ✕
            </button>
            <h2 className="text-2xl font-bold mb-6">Nouveau Planning d'Email Automatique</h2>
            
            <form onSubmit={handleCreateSchedule} className="space-y-6">
              {/* Informations de base */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nom du planning *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Heure d'envoi *
                  </label>
                  <input
                    type="time"
                    value={formData.send_time}
                    onChange={(e) => setFormData({...formData, send_time: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg"
                  rows={3}
                />
              </div>

              {/* Configuration email */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sujet de l'email *
                  </label>
                  <input
                    type="text"
                    value={formData.email_subject}
                    onChange={(e) => setFormData({...formData, email_subject: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fuseau horaire
                  </label>
                  <select
                    value={formData.timezone}
                    onChange={(e) => setFormData({...formData, timezone: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                  >
                    <option value="UTC">UTC</option>
                    <option value="Europe/Paris">Europe/Paris</option>
                    <option value="America/New_York">America/New_York</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template de l'email *
                </label>
                <textarea
                  value={formData.email_template}
                  onChange={(e) => setFormData({...formData, email_template: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg"
                  rows={6}
                  placeholder="Bonjour {{USER_NAME}},

Voici le rapport quotidien de vos firewalls :

Commandes exécutées : {{TOTAL_COMMANDS}}
Commandes réussies : {{SUCCESSFUL_COMMANDS}}
Commandes échouées : {{FAILED_COMMANDS}}
Date d'exécution : {{EXECUTION_DATE}}

Cordialement,
L'équipe technique"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Variables disponibles : {'{{USER_NAME}}'}, {'{{TOTAL_COMMANDS}}'}, {'{{SUCCESSFUL_COMMANDS}}'}, {'{{FAILED_COMMANDS}}'}, {'{{EXECUTION_DATE}}'}
                </p>
              </div>

                             {/* Destinataires */}
               <div>
                 <label className="block text-sm font-medium text-gray-700 mb-2">
                   Destinataires
                 </label>
                 <div className="flex items-center mb-3">
                   <input
                     type="checkbox"
                     id="include_all_users"
                     checked={formData.include_all_users}
                     onChange={(e) => setFormData({...formData, include_all_users: e.target.checked})}
                     className="mr-2"
                   />
                   <label htmlFor="include_all_users">Inclure tous les utilisateurs</label>
                 </div>
                 
                 {!formData.include_all_users && (
                   <div className="space-y-2">
                     <div className="flex items-center gap-2 mb-2">
                       <button
                         type="button"
                         onClick={() => setFormData({...formData, recipient_ids: users.map(u => u.id)})}
                         className="text-sm text-blue-600 hover:text-blue-800 underline"
                       >
                         Sélectionner tous
                       </button>
                       <button
                         type="button"
                         onClick={() => setFormData({...formData, recipient_ids: []})}
                         className="text-sm text-red-600 hover:text-red-800 underline"
                       >
                         Désélectionner tous
                       </button>
                     </div>
                     <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2">
                       {Array.isArray(users) && users.map(user => (
                         <label key={user.id} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                           <input
                             type="checkbox"
                             checked={formData.recipient_ids.includes(user.id)}
                             onChange={(e) => {
                               if (e.target.checked) {
                                 setFormData({
                                   ...formData,
                                   recipient_ids: [...formData.recipient_ids, user.id]
                                 });
                               } else {
                                 setFormData({
                                   ...formData,
                                   recipient_ids: formData.recipient_ids.filter(id => id !== user.id)
                                 });
                               }
                             }}
                             className="mr-3"
                           />
                           <div>
                             <div className="font-medium">{user.first_name} {user.last_name}</div>
                             <div className="text-sm text-gray-500">{user.email}</div>
                           </div>
                         </label>
                       ))}
                     </div>
                     <div className="text-sm text-gray-500">
                       {formData.recipient_ids.length} utilisateur(s) sélectionné(s)
                     </div>
                   </div>
                 )}
               </div>

                             {/* Firewalls */}
               <div>
                 <label className="block text-sm font-medium text-gray-700 mb-2">
                   Firewalls à vérifier *
                 </label>
                 
                 {/* Sélection par type de firewall */}
                 <div className="mb-4">
                   <h4 className="text-sm font-medium text-gray-700 mb-2">Sélection par type :</h4>
                   <div className="flex flex-wrap gap-2">
                     {Array.isArray(firewalls) && 
                       [...new Set(firewalls.map(f => f.firewall_type.name))].map(firewallType => {
                         const typeFirewalls = firewalls.filter(f => f.firewall_type.name === firewallType);
                         const allSelected = typeFirewalls.every(f => formData.firewall_ids.includes(f.id));
                         const someSelected = typeFirewalls.some(f => formData.firewall_ids.includes(f.id));
                         
                         return (
                           <button
                             key={firewallType}
                             type="button"
                             onClick={() => {
                               if (allSelected) {
                                 // Désélectionner tous les firewalls de ce type
                                 setFormData({
                                   ...formData,
                                   firewall_ids: formData.firewall_ids.filter(id => 
                                     !typeFirewalls.some(f => f.id === id)
                                   )
                                 });
                               } else {
                                 // Sélectionner tous les firewalls de ce type
                                 const newIds = [...new Set([
                                   ...formData.firewall_ids,
                                   ...typeFirewalls.map(f => f.id)
                                 ])];
                                 setFormData({
                                   ...formData,
                                   firewall_ids: newIds
                                 });
                               }
                             }}
                             className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                               allSelected 
                                 ? 'bg-blue-600 text-white' 
                                 : someSelected 
                                   ? 'bg-blue-200 text-blue-800' 
                                   : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                             }`}
                           >
                             {firewallType} ({typeFirewalls.length})
                           </button>
                         );
                       })
                     }
                   </div>
                 </div>
                 
                 {/* Sélection individuelle des firewalls */}
                 <div className="space-y-2">
                   <div className="flex items-center gap-2 mb-2">
                     <button
                       type="button"
                       onClick={() => setFormData({...formData, firewall_ids: firewalls.map(f => f.id)})}
                       className="text-sm text-blue-600 hover:text-blue-800 underline"
                     >
                       Sélectionner tous
                     </button>
                     <button
                       type="button"
                       onClick={() => setFormData({...formData, firewall_ids: []})}
                       className="text-sm text-red-600 hover:text-red-800 underline"
                     >
                       Désélectionner tous
                     </button>
                   </div>
                   
                   <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2">
                     {Array.isArray(firewalls) && firewalls.map(firewall => (
                       <label key={firewall.id} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                         <input
                           type="checkbox"
                           checked={formData.firewall_ids.includes(firewall.id)}
                           onChange={(e) => {
                             if (e.target.checked) {
                               setFormData({
                                 ...formData,
                                 firewall_ids: [...formData.firewall_ids, firewall.id]
                               });
                             } else {
                               setFormData({
                                 ...formData,
                                 firewall_ids: formData.firewall_ids.filter(id => id !== firewall.id)
                               });
                             }
                           }}
                           className="mr-3"
                         />
                         <div className="flex-1">
                           <div className="font-medium">{firewall.name}</div>
                           <div className="text-sm text-gray-500">
                             {firewall.ip_address} - {firewall.firewall_type.name}
                           </div>
                         </div>
                       </label>
                     ))}
                   </div>
                   
                   <div className="text-sm text-gray-500">
                     {formData.firewall_ids.length} firewall(s) sélectionné(s)
                   </div>
                   
                   {/* Types de firewalls sélectionnés */}
                   {formData.firewall_ids.length > 0 && (
                     <div className="mt-2">
                       <span className="text-sm text-gray-500">Types sélectionnés : </span>
                       {Array.isArray(firewalls) && 
                         [...new Set(
                           firewalls
                             .filter(f => formData.firewall_ids.includes(f.id))
                             .map(f => f.firewall_type.name)
                         )].map(type => (
                           <span key={type} className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mr-1 mb-1">
                             {type}
                           </span>
                         ))
                       }
                     </div>
                   )}
                 </div>
               </div>

              {/* Commandes */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Commandes à exécuter
                  </label>
                  <button
                    type="button"
                    onClick={addCommand}
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                  >
                    + Ajouter Commande
                  </button>
                </div>
                
                                 {Array.isArray(formData.commands_to_execute) && formData.commands_to_execute.map((command, index) => (
                  <div key={index} className="flex gap-2 mb-2">
                    <select
                      value={command.type}
                      onChange={(e) => updateCommand(index, 'type', e.target.value)}
                      className="p-2 border border-gray-300 rounded"
                    >
                      <option value="general">Général</option>
                      <option value="cisco">Cisco</option>
                      <option value="fortinet">Fortinet</option>
                      <option value="paloalto">Palo Alto</option>
                    </select>
                    <input
                      type="text"
                      value={command.command}
                      onChange={(e) => updateCommand(index, 'command', e.target.value)}
                      placeholder="Commande à exécuter"
                      className="flex-1 p-2 border border-gray-300 rounded"
                    />
                    <button
                      type="button"
                      onClick={() => removeCommand(index)}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                    >
                      Supprimer
                    </button>
                  </div>
                ))}
                
                {/* Modèles de commandes (depuis le backend) */}
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">Modèles de commandes :</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Array.isArray(templates) && templates.map((tpl) => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => addTemplateToForm(tpl)}
                        className="text-left p-2 border border-gray-200 rounded hover:bg-gray-50 text-sm"
                      >
                        <div className="font-medium">{tpl.command}</div>
                        <div className="text-gray-500">{tpl.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-4 pt-6 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Créer le Planning
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de détails */}
      {selectedSchedule && !showEditForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="relative bg-white rounded-lg p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              aria-label="Fermer"
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              onClick={() => setSelectedSchedule(null)}
            >
              ✕
            </button>
            <h2 className="text-2xl font-bold mb-6">Détails du Planning</h2>
            {detailsLoading && (
              <div className="mb-4 text-sm text-gray-500">Chargement des détails...</div>
            )}
            
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-3">Informations générales</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Nom</p>
                    <p className="font-medium">{selectedSchedule.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Heure d'envoi</p>
                    <p className="font-medium">{selectedSchedule.send_time}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Description</p>
                    <p className="font-medium">{selectedSchedule.description || 'Aucune description'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Statut</p>
                    <span className={`px-2 py-1 rounded-full text-sm font-medium ${
                      selectedSchedule.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {selectedSchedule.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </div>
                </div>
              </div>

                             <div>
                 <h3 className="font-semibold text-lg mb-3">Destinataires ({selectedSchedule.recipients_count || 0})</h3>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                   {Array.isArray(selectedSchedule.recipients) && selectedSchedule.recipients.length > 0 ? (
                     selectedSchedule.recipients.map(user => (
                       <div key={user.id} className="p-3 bg-gray-50 rounded-lg border">
                         <div className="font-medium">{user.first_name} {user.last_name}</div>
                         <div className="text-sm text-gray-600">{user.email}</div>
                       </div>
                     ))
                   ) : (
                     <div className="col-span-2 text-gray-500 italic">Aucun destinataire spécifique (tous les utilisateurs inclus)</div>
                   )}
                 </div>
               </div>

                             <div>
                 <h3 className="font-semibold text-lg mb-3">Firewalls ({selectedSchedule.firewalls_count || 0})</h3>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                   {Array.isArray(selectedSchedule.firewalls) && selectedSchedule.firewalls.length > 0 ? (
                     selectedSchedule.firewalls.map(firewall => (
                       <div key={firewall.id} className="p-3 bg-gray-50 rounded-lg border">
                         <div className="font-medium">{firewall.name}</div>
                         <div className="text-sm text-gray-600">{firewall.ip_address}</div>
                         <div className="text-xs text-gray-500">{firewall.firewall_type.name}</div>
                       </div>
                     ))
                   ) : (
                     <div className="col-span-2 text-gray-500 italic">Aucun firewall sélectionné</div>
                   )}
                 </div>
               </div>

              <div>
                <h3 className="font-semibold text-lg mb-3">Commandes à exécuter ({selectedSchedule.commands_to_execute?.length || 0})</h3>
                <div className="space-y-3">
                  {Array.isArray(selectedSchedule.commands_to_execute) && selectedSchedule.commands_to_execute.length > 0 ? (
                    selectedSchedule.commands_to_execute.map((cmd, index) => (
                      <div key={index} className="p-3 bg-gray-50 rounded-lg border">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="font-medium">{cmd.command}</div>
                            <div className="text-sm text-gray-600">Type: {cmd.type}</div>
                            {cmd.description && (
                              <div className="text-sm text-gray-500 mt-1">{cmd.description}</div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-gray-500 italic">Aucune commande configurée</div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-3">Configuration Email</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Sujet de l'email</p>
                    <p className="font-medium">{selectedSchedule.email_subject}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Template de l'email</p>
                    <div className="p-4 bg-gray-50 rounded-lg border whitespace-pre-wrap text-sm">
                      {selectedSchedule.email_template}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-4 mt-6">
              <button
                onClick={() => handleEditSchedule(selectedSchedule)}
                className="px-6 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
              >
                Modifier
              </button>
              <button
                onClick={() => setSelectedSchedule(null)}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de modification */}
      {showEditForm && selectedSchedule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="relative bg-white rounded-lg p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              aria-label="Fermer"
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              onClick={handleCancelEdit}
            >
              ✕
            </button>
            <h2 className="text-2xl font-bold mb-6">Modifier le Planning</h2>
            {/* Infos actuelles du planning */}
            <div className="mb-6 p-4 bg-gray-50 border rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-gray-500">Nom</div>
                  <div className="font-medium">{selectedSchedule.name}</div>
                </div>
                <div>
                  <div className="text-gray-500">Heure d'envoi</div>
                  <div className="font-medium">{selectedSchedule.send_time}</div>
                </div>
                <div>
                  <div className="text-gray-500">Prochain envoi</div>
                  <div className="font-medium">{selectedSchedule.next_send ? new Date(selectedSchedule.next_send).toLocaleString() : 'Non programmé'}</div>
                </div>
                <div>
                  <div className="text-gray-500">Dernier envoi</div>
                  <div className="font-medium">{selectedSchedule.last_sent ? new Date(selectedSchedule.last_sent).toLocaleString() : 'Jamais'}</div>
                </div>
                <div>
                  <div className="text-gray-500">Destinataires</div>
                  <div className="font-medium">{selectedSchedule.include_all_users ? 'Tous les utilisateurs' : `${selectedSchedule.recipients_count || 0} utilisateur(s)`}</div>
                </div>
                <div>
                  <div className="text-gray-500">Firewalls</div>
                  <div className="font-medium">{selectedSchedule.firewalls_count || 0}</div>
                </div>
              </div>
            </div>
            
            <form onSubmit={handleUpdateSchedule} className="space-y-6">
              {/* Informations de base */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nom du planning *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Heure d'envoi *
                  </label>
                  <input
                    type="time"
                    value={formData.send_time}
                    onChange={(e) => setFormData({...formData, send_time: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg"
                  rows={3}
                />
              </div>

              {/* Configuration email */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sujet de l'email *
                  </label>
                  <input
                    type="text"
                    value={formData.email_subject}
                    onChange={(e) => setFormData({...formData, email_subject: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fuseau horaire
                  </label>
                  <select
                    value={formData.timezone}
                    onChange={(e) => setFormData({...formData, timezone: e.target.value})}
                    className="w-full p-3 border border-gray-300 rounded-lg"
                  >
                    <option value="UTC">UTC</option>
                    <option value="Europe/Paris">Europe/Paris</option>
                    <option value="America/New_York">America/New_York</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template de l'email *
                </label>
                <textarea
                  value={formData.email_template}
                  onChange={(e) => setFormData({...formData, email_template: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg"
                  rows={6}
                  placeholder="Bonjour {{USER_NAME}},

Voici le rapport quotidien de vos firewalls :

Commandes exécutées : {{TOTAL_COMMANDS}}
Commandes réussies : {{SUCCESSFUL_COMMANDS}}
Commandes échouées : {{FAILED_COMMANDS}}
Date d'exécution : {{EXECUTION_DATE}}

Cordialement,
L'équipe technique"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Variables disponibles : {'{{USER_NAME}}'}, {'{{TOTAL_COMMANDS}}'}, {'{{SUCCESSFUL_COMMANDS}}'}, {'{{FAILED_COMMANDS}}'}, {'{{EXECUTION_DATE}}'}
                </p>
              </div>

              {/* Destinataires */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Destinataires
                </label>
                <div className="flex items-center mb-3">
                  <input
                    type="checkbox"
                    id="include_all_users_edit"
                    checked={formData.include_all_users}
                    onChange={(e) => setFormData({...formData, include_all_users: e.target.checked})}
                    className="mr-2"
                  />
                  <label htmlFor="include_all_users_edit">Inclure tous les utilisateurs</label>
                </div>
                
                {!formData.include_all_users && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                      <button
                        type="button"
                        onClick={() => setFormData({...formData, recipient_ids: users.map(u => u.id)})}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                      >
                        Sélectionner tous
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormData({...formData, recipient_ids: []})}
                        className="text-sm text-red-600 hover:text-red-800 underline"
                      >
                        Désélectionner tous
                      </button>
                    </div>
                    <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2">
                      {Array.isArray(users) && users.map(user => (
                        <label key={user.id} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.recipient_ids.includes(user.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFormData({
                                  ...formData,
                                  recipient_ids: [...formData.recipient_ids, user.id]
                                });
                              } else {
                                setFormData({
                                  ...formData,
                                  recipient_ids: formData.recipient_ids.filter(id => id !== user.id)
                                });
                              }
                            }}
                            className="mr-3"
                          />
                          <div>
                            <div className="font-medium">{user.first_name} {user.last_name}</div>
                            <div className="text-sm text-gray-500">{user.email}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                    <div className="text-sm text-gray-500">
                      {formData.recipient_ids.length} utilisateur(s) sélectionné(s)
                    </div>
                  </div>
                )}
              </div>

              {/* Firewalls */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Firewalls à vérifier *
                </label>
                
                {/* Sélection par type de firewall */}
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Sélection par type :</h4>
                  <div className="flex flex-wrap gap-2">
                    {Array.isArray(firewalls) && 
                      [...new Set(firewalls.map(f => f.firewall_type.name))].map(firewallType => {
                        const typeFirewalls = firewalls.filter(f => f.firewall_type.name === firewallType);
                        const allSelected = typeFirewalls.every(f => formData.firewall_ids.includes(f.id));
                        const someSelected = typeFirewalls.some(f => formData.firewall_ids.includes(f.id));
                        
                        return (
                          <button
                            key={firewallType}
                            type="button"
                            onClick={() => {
                              if (allSelected) {
                                // Désélectionner tous les firewalls de ce type
                                setFormData({
                                  ...formData,
                                  firewall_ids: formData.firewall_ids.filter(id => 
                                    !typeFirewalls.some(f => f.id === id)
                                  )
                                });
                              } else {
                                // Sélectionner tous les firewalls de ce type
                                const newIds = [...new Set([
                                  ...formData.firewall_ids,
                                  ...typeFirewalls.map(f => f.id)
                                ])];
                                setFormData({
                                  ...formData,
                                  firewall_ids: newIds
                                });
                              }
                            }}
                            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                              allSelected 
                                ? 'bg-blue-600 text-white' 
                                : someSelected 
                                  ? 'bg-blue-200 text-blue-800' 
                                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                          >
                            {firewallType} ({typeFirewalls.length})
                          </button>
                        );
                      })
                    }
                  </div>
                </div>
                
                {/* Sélection individuelle des firewalls */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <button
                      type="button"
                      onClick={() => setFormData({...formData, firewall_ids: firewalls.map(f => f.id)})}
                      className="text-sm text-blue-600 hover:text-blue-800 underline"
                    >
                      Sélectionner tous
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({...formData, firewall_ids: []})}
                      className="text-sm text-red-600 hover:text-red-800 underline"
                    >
                      Désélectionner tous
                    </button>
                  </div>
                  
                  <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2">
                    {Array.isArray(firewalls) && firewalls.map(firewall => (
                      <label key={firewall.id} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.firewall_ids.includes(firewall.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                firewall_ids: [...formData.firewall_ids, firewall.id]
                              });
                            } else {
                              setFormData({
                                ...formData,
                                firewall_ids: formData.firewall_ids.filter(id => id !== firewall.id)
                              });
                            }
                          }}
                          className="mr-3"
                        />
                        <div className="flex-1">
                          <div className="font-medium">{firewall.name}</div>
                          <div className="text-sm text-gray-500">
                            {firewall.ip_address} - {firewall.firewall_type.name}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                  
                  <div className="text-sm text-gray-500">
                    {formData.firewall_ids.length} firewall(s) sélectionné(s)
                  </div>
                </div>
              </div>

              {/* Commandes */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Commandes à exécuter
                  </label>
                  <button
                    type="button"
                    onClick={addCommand}
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                  >
                    + Ajouter Commande
                  </button>
                </div>
                
                {Array.isArray(formData.commands_to_execute) && formData.commands_to_execute.map((command, index) => (
                  <div key={index} className="flex gap-2 mb-2">
                    <select
                      value={command.type}
                      onChange={(e) => updateCommand(index, 'type', e.target.value)}
                      className="p-2 border border-gray-300 rounded"
                    >
                      <option value="general">Général</option>
                      <option value="cisco">Cisco</option>
                      <option value="fortinet">Fortinet</option>
                      <option value="paloalto">Palo Alto</option>
                    </select>
                    <input
                      type="text"
                      value={command.command}
                      onChange={(e) => updateCommand(index, 'command', e.target.value)}
                      placeholder="Commande à exécuter"
                      className="flex-1 p-2 border border-gray-300 rounded"
                    />
                    <button
                      type="button"
                      onClick={() => removeCommand(index)}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                    >
                      Supprimer
                    </button>
                  </div>
                ))}
                
                {/* Modèles de commandes (depuis le backend) */}
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">Modèles de commandes :</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Array.isArray(templates) && templates.map((tpl) => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => addTemplateToForm(tpl)}
                        className="text-left p-2 border border-gray-200 rounded hover:bg-gray-50 text-sm"
                      >
                        <div className="font-medium">{tpl.command}</div>
                        <div className="text-gray-500">{tpl.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-4 pt-6 border-t">
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
                >
                  Modifier le Planning
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AutomatedEmailManager;

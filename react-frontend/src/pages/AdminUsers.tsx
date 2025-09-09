import React, { useEffect, useState } from 'react';
import api from '../utils/axiosConfig';

interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser?: boolean;
}

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form, setForm] = useState<Partial<User> & { password?: string }>({});
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState<'all' | 'admin' | 'user'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'frozen'>('all');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/auth/users/');
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];
      setUsers(data);
    } catch (err) {
      setError('Erreur lors du chargement des utilisateurs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setForm(user);
    setCreating(false);
  };

  const handleDelete = async (user: User) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    try {
      await api.delete(`/auth/users/${user.id}/`);
      fetchUsers();
    } catch {
      setError('Erreur lors de la suppression');
    }
  };

  const handleFreeze = async (user: User) => {
    try {
      await api.post(`/auth/users/${user.id}/freeze/`);
      fetchUsers();
    } catch {
      setError('Erreur lors du freeze');
    }
  };

  const handleUnfreeze = async (user: User) => {
    try {
      await api.post(`/auth/users/${user.id}/unfreeze/`);
      fetchUsers();
    } catch {
      setError('Erreur lors du unfreeze');
    }
  };

  const handlePromoteToAdmin = async (user: User) => {
    if (!window.confirm(`Promouvoir ${user.username} en administrateur ?`)) return;
    try {
      await api.post(`/auth/users/${user.id}/promote_to_admin/`);
      fetchUsers();
    } catch {
      setError('Erreur lors de la promotion en admin');
    }
  };

  const handlePromoteToSuperuser = async (user: User) => {
    if (!window.confirm(`Promouvoir ${user.username} en superutilisateur ?`)) return;
    try {
      await api.post(`/auth/users/${user.id}/promote_to_superuser/`);
      fetchUsers();
    } catch {
      setError("Erreur lors de la promotion en superutilisateur");
    }
  };

  const handleDemoteFromSuperuser = async (user: User) => {
    if (!window.confirm(`Rétrograder ${user.username} de superutilisateur ?`)) return;
    try {
      await api.post(`/auth/users/${user.id}/demote_from_superuser/`);
      fetchUsers();
    } catch (e) {
      setError("Erreur lors de la rétrogradation du superutilisateur");
    }
  };

  const handleDemoteFromAdmin = async (user: User) => {
    if (!window.confirm(`Rétrograder ${user.username} en utilisateur normal ?`)) return;
    try {
      await api.post(`/auth/users/${user.id}/demote_from_admin/`);
      fetchUsers();
    } catch {
      setError('Erreur lors de la rétrogradation');
    }
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await api.put(`/auth/users/${editingUser.id}/`, form);
      } else {
        // Use registration endpoint for creating users
        await api.post('/auth/register/', {
          username: form.username,
          email: form.email,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
          phone_number: form.phone_number,
        });
      }
      setEditingUser(null);
      setForm({});
      setCreating(false);
      fetchUsers();
    } catch {
      setError('Erreur lors de la sauvegarde');
    }
  };

  const closeModal = () => {
    setEditingUser(null);
    setCreating(false);
    setForm({});
  };

  const normalized = (value: string) => (value || '').toLowerCase();
  const filteredUsers = users.filter((u) => {
    const matchesSearch = [u.username, u.email, u.first_name, u.last_name, u.phone_number]
      .some((f) => normalized(f).includes(normalized(search)));
    const matchesRole = filterRole === 'all' ? true : filterRole === 'admin' ? u.is_staff : !u.is_staff;
    const matchesStatus = filterStatus === 'all' ? true : filterStatus === 'active' ? u.is_active : !u.is_active;
    return matchesSearch && matchesRole && matchesStatus;
  });

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-purple-900 to-pink-600 p-8">
      <div className="bg-white p-8 rounded-2xl shadow-2xl w-full max-w-6xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h1 className="text-2xl font-bold text-purple-700">Gestion des utilisateurs</h1>
          <div className="flex items-center gap-2">
            <button
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              onClick={() => { setEditingUser(null); setForm({}); setCreating(true); }}
            >
              Ajouter un utilisateur
            </button>
          </div>
        </div>
        {error && <div className="mb-4 p-2 bg-red-100 text-red-700 rounded">{error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          <input
            type="text"
            placeholder="Rechercher (nom, email, téléphone)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border p-2 rounded w-full"
          />
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value as 'all' | 'admin' | 'user')}
            className="border p-2 rounded w-full"
          >
            <option value="all">Tous les rôles</option>
            <option value="admin">Admins</option>
            <option value="user">Utilisateurs</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as 'all' | 'active' | 'frozen')}
            className="border p-2 rounded w-full"
          >
            <option value="all">Tous les statuts</option>
            <option value="active">Actifs</option>
            <option value="frozen">Freezés</option>
          </select>
        </div>

        <div className="rounded-xl border overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Chargement...</div>
          ) : filteredUsers.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Aucun utilisateur trouvé</div>
          ) : (
            <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
              <table className="w-full table-auto">
                <thead className="sticky top-0 z-10">
                  <tr className="bg-purple-100">
                    <th className="p-3 text-left">Nom d'utilisateur</th>
                    <th className="p-3 text-left">Email</th>
                    <th className="p-3 text-left">Prénom</th>
                    <th className="p-3 text-left">Nom</th>
                    <th className="p-3 text-left">Téléphone</th>
                    <th className="p-3 text-left">Statut</th>
                    <th className="p-3 text-left">Rôle</th>
                    <th className="p-3 text-left">Superuser</th>
                    <th className="p-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(user => (
                    <tr key={user.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium text-gray-800">{user.username}</td>
                      <td className="p-3">{user.email}</td>
                      <td className="p-3">{user.first_name}</td>
                      <td className="p-3">{user.last_name}</td>
                      <td className="p-3">{user.phone_number}</td>
                      <td className="p-3">
                        {user.is_active ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">Actif</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">Freezé</span>
                        )}
                      </td>
                      <td className="p-3">
                        {user.is_staff ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">Admin</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">Utilisateur</span>
                        )}
                      </td>
                      <td className="p-3">
                        {user.is_superuser ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-black text-white">Superuser</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">—</span>
                        )}
                      </td>
                      <td className="p-3 space-x-2 whitespace-nowrap">
                        <button className="px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => handleEdit(user)}>Éditer</button>
                        <button className="px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700" onClick={() => handleDelete(user)}>Supprimer</button>
                        {user.is_active ? (
                          <button className="px-2 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600" onClick={() => handleFreeze(user)}>Freezer</button>
                        ) : (
                          <button className="px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700" onClick={() => handleUnfreeze(user)}>Défreezer</button>
                        )}
                        {user.is_staff ? (
                          <button className="px-2 py-1 bg-orange-500 text-white rounded hover:bg-orange-600" onClick={() => handleDemoteFromAdmin(user)}>Rétrograder</button>
                        ) : (
                          <button className="px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700" onClick={() => handlePromoteToAdmin(user)}>Promouvoir</button>
                        )}
                        {user.is_superuser ? (
                          <button className="px-2 py-1 bg-gray-800 text-white rounded hover:bg-black" onClick={() => handleDemoteFromSuperuser(user)}>Retirer super</button>
                        ) : (
                          <button className="px-2 py-1 bg-gray-700 text-white rounded hover:bg-gray-800" onClick={() => handlePromoteToSuperuser(user)}>Rendre super</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {(editingUser || creating) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={closeModal} />
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-purple-700">
                  {editingUser ? 'Modifier utilisateur' : 'Créer un utilisateur'}
                </h2>
                <button onClick={closeModal} className="text-gray-500 hover:text-gray-700">✕</button>
              </div>
              <form onSubmit={handleFormSubmit} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input
                    type="text"
                    name="username"
                    placeholder="Nom d'utilisateur"
                    value={form.username || ''}
                    onChange={handleFormChange}
                    className="border p-2 rounded w-full"
                    required
                  />
                  <input
                    type="email"
                    name="email"
                    placeholder="Email"
                    value={form.email || ''}
                    onChange={handleFormChange}
                    className="border p-2 rounded w-full"
                    required
                  />
                  <input
                    type="text"
                    name="first_name"
                    placeholder="Prénom"
                    value={form.first_name || ''}
                    onChange={handleFormChange}
                    className="border p-2 rounded w-full"
                  />
                  <input
                    type="text"
                    name="last_name"
                    placeholder="Nom"
                    value={form.last_name || ''}
                    onChange={handleFormChange}
                    className="border p-2 rounded w-full"
                  />
                  <input
                    type="text"
                    name="phone_number"
                    placeholder="Téléphone"
                    value={form.phone_number || ''}
                    onChange={handleFormChange}
                    className="border p-2 rounded w-full"
                  />
                  {!editingUser && (
                    <input
                      type="password"
                      name="password"
                      placeholder="Mot de passe"
                      value={form.password as string || ''}
                      onChange={handleFormChange}
                      className="border p-2 rounded w-full"
                      required
                    />
                  )}
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" className="px-4 py-2 bg-gray-200 text-gray-800 rounded" onClick={closeModal}>
                    Annuler
                  </button>
                  <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                    {editingUser ? 'Enregistrer' : 'Créer'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminUsers; 
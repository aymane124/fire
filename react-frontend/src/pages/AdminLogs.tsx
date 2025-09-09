import React from 'react';

const AdminLogs: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 to-pink-600">
      <div className="bg-white p-8 rounded-lg shadow-xl w-96">
        <h1 className="text-2xl font-bold mb-4 text-purple-700">Logs système</h1>
        <p className="text-gray-700">Page réservée à la consultation des logs système.</p>
      </div>
    </div>
  );
};

export default AdminLogs; 
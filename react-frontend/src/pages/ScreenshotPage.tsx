import React, { useState } from 'react';
import api from '../utils/axiosConfig';

interface ScreenshotResponse {
  image_base64: string;
  width: number;
  height: number;
  url: string;
  report_id?: string;
  excel_download_url?: string;
}

const ScreenshotPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ip, setIp] = useState<string>('');
  const [protocol, setProtocol] = useState<'http' | 'https'>('https');
  const [fullPage, setFullPage] = useState<boolean>(true);
  const [ignoreHttps, setIgnoreHttps] = useState<boolean>(true);
  const [generateExcel, setGenerateExcel] = useState<boolean>(false);
  const [excelDownloadUrl, setExcelDownloadUrl] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  const handleCapture = async () => {
    setLoading(true);
    setError(null);
    setImageBase64(null);
    setExcelDownloadUrl(null);
    setReportId(null);
    
    try {
      if (!ip.trim()) {
        setError('Please enter firewall IP address');
        setLoading(false);
        return;
      }
      
      const payload: any = {
        ip_address: ip.trim(),
        protocol,
        full_page: fullPage,
        ignore_https_errors: ignoreHttps,
        generate_excel: generateExcel  // Nouveau paramètre
      };
      
      const res = await api.post<ScreenshotResponse>('/screenshots/capture/', payload);
      setImageBase64(res.data.image_base64);
      
      // Gérer la réponse Excel
      if (res.data.excel_download_url) {
        setExcelDownloadUrl(res.data.excel_download_url);
        setReportId(res.data.report_id || null);
      }
      
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error';
      setError(String(detail));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadExcel = () => {
    if (excelDownloadUrl) {
      // Ouvrir le téléchargement dans un nouvel onglet
      window.open(excelDownloadUrl, '_blank');
    }
  };


  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Screenshot</h1>

      <div className="mb-4 p-3 bg-white border rounded">
        <p className="text-sm text-slate-600">
          Remplissez l'IP du firewall. L'app se connectera automatiquement et naviguera vers le dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm text-slate-600 mb-1">Protocol</label>
          <select
            value={protocol}
            onChange={(e) => setProtocol(e.target.value as 'http' | 'https')}
            className="w-full px-3 py-2 border rounded bg-white"
          >
            <option value="https">https</option>
            <option value="http">http</option>
          </select>
          <p className="text-xs text-slate-500 mt-1">https recommandé (certificat autosigné accepté si activé ci‑dessous).</p>
        </div>
        <div>
          <label className="block text-sm text-slate-600 mb-1">Adresse IP du firewall</label>
          <input
            type="text"
            placeholder="ex: 172.16.24.130"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          />
          <p className="text-xs text-slate-500 mt-1">L'app se connectera automatiquement et naviguera vers le dashboard.</p>
        </div>
      </div>

      <div className="flex items-center gap-6 mb-6">
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={fullPage} onChange={(e) => setFullPage(e.target.checked)} />
          <span className="text-sm text-slate-700">Capture pleine page</span>
        </label>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={ignoreHttps} onChange={(e) => setIgnoreHttps(e.target.checked)} />
          <span className="text-sm text-slate-700">Ignorer les erreurs HTTPS (certificat autosigné)</span>
        </label>
        <label className="inline-flex items-center gap-2">
          <input 
            type="checkbox" 
            checked={generateExcel} 
            onChange={(e) => setGenerateExcel(e.target.checked)} 
          />
          <span className="text-sm text-slate-700">Générer un fichier Excel avec la photo</span>
        </label>
      </div>

      <div className="flex gap-3 mb-4">
        <button
          onClick={handleCapture}
          disabled={loading}
          className="px-4 py-2 rounded bg-purple-700 text-white hover:bg-purple-800 disabled:opacity-50"
        >
          {loading ? 'Capturing…' : 'Lancer la capture'}
        </button>
        
        {excelDownloadUrl && (
          <button
            onClick={handleDownloadExcel}
            className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 flex items-center gap-2"
          >
            📊 Télécharger Excel
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-600">
          {error}
        </div>
      )}

      {excelDownloadUrl && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-green-700">
          ✅ Fichier Excel généré avec succès ! Cliquez sur "Télécharger Excel" pour le récupérer.
        </div>
      )}

      {imageBase64 && (
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-lg font-medium">Screenshot capturé</h3>
            {reportId && (
              <span className="text-sm text-gray-500">Rapport ID: {reportId}</span>
            )}
          </div>
          <img
            src={`data:image/png;base64,${imageBase64}`}
            alt="Screenshot"
            className="border rounded shadow max-w-full"
          />
        </div>
      )}
    </div>
  );
};

export default ScreenshotPage;


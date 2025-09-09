import { useState, useRef, useEffect } from 'react';
import { Save, ArrowLeft, Plus, Info, Trash2, Loader2, Edit2, Download } from 'lucide-react';
import { templateService, variableService, Template, Variable } from '../services/templateService';
import { useParams, useNavigate } from 'react-router-dom';
import { API_URL } from '../config.ts';
import axios from 'axios';

function TemplateEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [templateContent, setTemplateContent] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [variables, setVariables] = useState<Variable[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [newVariable, setNewVariable] = useState({ name: '', description: '' });
  const [showTooltip, setShowTooltip] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const loadVariables = async () => {
    try {
      const variables = await variableService.getVariables();
      
      // Vérifier si les variables sont valides
      if (Array.isArray(variables)) {
        // Trier les variables par nom pour un affichage cohérent
        const sortedVariables = variables.sort((a, b) => a.name.localeCompare(b.name));
        setVariables(sortedVariables);
      } else {
        setVariables([]);
      }
    } catch (error) {
      setError('Erreur lors du chargement des variables');
      setVariables([]);
    }
  };

  const loadTemplates = async () => {
    try {
      setIsLoading(true);
      const response = await templateService.getTemplates();
      if (Array.isArray(response)) {
        setTemplates(response);
      } else {
        setTemplates([]);
      }
    } catch (error) {
      setError('Erreur lors du chargement des templates');
      setTemplates([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadTemplate(id);
    }
    loadVariables();
    loadTemplates();
    
    // Suppression de l'auto-refresh
  }, [id]);

  const loadTemplate = async (templateId: string) => {
    try {
      setIsLoading(true);
      const template = await templateService.getTemplate(parseInt(templateId));
      const variables = await variableService.getVariables();
      setTemplateName(template.name);
      setTemplateContent(template.content);
      setVariables(variables);
    } catch (error) {
      setError('Erreur lors du chargement du template');
    } finally {
      setIsLoading(false);
    }
  };

  const insertVariable = (varName: string) => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = textarea.value;
      const newText = text.substring(0, start) + `{{ ${varName} }}` + text.substring(end);
      setTemplateContent(newText);
      
      // Restore cursor position after the inserted variable
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + varName.length + 6, start + varName.length + 6);
      }, 0);
    }
  };

  const handleAddVariable = async () => {
    if (!newVariable.name || !newVariable.description) {
      setError('Veuillez remplir tous les champs de la variable');
      return;
    }

    try {
      setIsLoading(true);
      const addedVariable = await variableService.createVariable(newVariable);
      if (id) {
        await variableService.addVariableToTemplate(parseInt(id), addedVariable.id);
      }
      setNewVariable({ name: '', description: '' });
      // Recharger les variables après l'ajout
      await loadVariables();
    } catch (error) {
      setError('Erreur lors de l\'ajout de la variable');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveVariable = async (variableId: number) => {
    try {
      setIsLoading(true);
      await variableService.deleteVariable(variableId);
      // Recharger les variables après la suppression
      await loadVariables();
    } catch (error) {
      setError('Erreur lors de la suppression de la variable');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!templateName) {
      setError('Veuillez donner un nom au template');
      return;
    }

    try {
      setIsLoading(true);
      const templateData = {
        name: templateName,
        content: templateContent
      };

      if (id) {
        await templateService.updateTemplate(parseInt(id), templateData);
      } else {
        await templateService.createTemplate({
          ...templateData,
          description: '',
          variables: []
        });
      }
      
      navigate('/templates');
    } catch (error) {
      setError('Erreur lors de la sauvegarde du template');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteTemplate = async (templateId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce template ?')) {
      try {
        setIsLoading(true);
        await templateService.deleteTemplate(templateId);
        await loadTemplates();
      } catch (error) {
        setError('Erreur lors de la suppression du template');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleDownloadExcel = async (templateId: number) => {
    try {
      setIsLoading(true);
      const response = await axios.get(
        `${API_URL}/templates/${templateId}/download_excel/`,
        {
          responseType: 'blob',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      // Create a blob from the response data
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);

      // Create a temporary link element
      const link = document.createElement('a');
      link.href = url;
      link.download = `template_${templateId}_${new Date().toISOString()}.xlsx`;

      // Append to the document, click it, and remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the URL
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading Excel file:', error);
      setError('Failed to download Excel file');
    } finally {
      setIsLoading(false);
    }
  };

  // Ajout d'une fonction de rafraîchissement manuel
  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadVariables(), loadTemplates()]);
    } catch (error) {
      setError('Erreur lors du rafraîchissement');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {id ? 'Modifier le Template' : 'Nouveau Template'}
          </h1>
          <p className="text-gray-600">Créez des templates avec des variables pour configurations dynamique des firewalls</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
          title="Rafraîchir"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-md">
          {error}
        </div>
      )}

      <div className="flex gap-6">
        {/* Main Editor Section */}
        <div className="flex-1">
          <div className="mb-4">
            <label htmlFor="templateName" className="block text-sm font-medium text-gray-700 mb-1">
              Nom du Template
            </label>
            <input
              id="templateName"
              name="templateName"
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500"
              placeholder="Entrez le nom du template"
            />
          </div>

          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <textarea
              ref={textareaRef}
              value={templateContent}
              onChange={(e) => setTemplateContent(e.target.value)}
              className="w-full h-[500px] p-4 font-mono text-sm bg-gray-900 text-gray-100 border-0 focus:ring-0 resize-none"
              placeholder="Entrez le contenu du template ici..."
              style={{
                lineHeight: '1.5',
                tabSize: 2
              }}
            />
          </div>

          <div className="mt-4 flex gap-4">
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              ) : (
                <Save className="w-5 h-5 mr-2" />
              )}
              {isLoading ? 'Enregistrement...' : 'Enregistrer'}
            </button>
            <button
              onClick={() => navigate('/templates')}
              className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Retour
            </button>
            {id && (
              <button
                onClick={() => handleDeleteTemplate(parseInt(id))}
                disabled={isLoading}
                className="flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Trash2 className="w-5 h-5 mr-2" />
                Supprimer
              </button>
            )}
          </div>
        </div>

        {/* Variables Sidebar */}
        <div className="w-80">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Variables Disponibles</h2>
            
            <div className="space-y-4 mb-6">
              {variables && variables.length > 0 ? (
                <>
                  {/* Required Variables Section */}
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-purple-600 mb-2 flex items-center">
                      <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                      Variables Requises
                    </h3>
                    <div className="space-y-2">
                      {variables
                        .filter(variable => [
                          'Hostname', 'IP Address', 'VDOM', 'Name', 'Source Address',
                          'Source Description', 'Source Interface', 'Destination Address',
                          'Destination Description', 'Destination Interface', 'Service'
                        ].includes(variable.name))
                        .map((variable) => (
                          <div
                            key={`variable-${variable.id || variable.name}`}
                            className="group relative"
                          >
                            <div className="flex items-center justify-between p-2 bg-purple-50 hover:bg-purple-100 rounded-md transition-colors duration-200">
                              <button
                                onClick={() => insertVariable(variable.name)}
                                className="flex-1 text-left flex items-center"
                              >
                                <span className="text-purple-700 font-medium">{variable.name}</span>
                              </button>
                              <div className="flex items-center gap-2">
                                <Info className="w-4 h-4 text-purple-400" />
                                <button
                                  onClick={() => handleRemoveVariable(variable.id!)}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Trash2 className="w-4 h-4 text-red-500 hover:text-red-700" />
                                </button>
                              </div>
                            </div>
                            {showTooltip === variable.name && (
                              <div className="absolute z-10 w-48 px-3 py-2 bg-gray-800 text-white text-sm rounded-md shadow-lg -top-8 right-0">
                                {variable.description}
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Custom Variables Section */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-600 mb-2 flex items-center">
                      <span className="w-2 h-2 bg-gray-400 rounded-full mr-2"></span>
                      Variables Personnalisées
                    </h3>
                    <div className="space-y-2">
                      {variables
                        .filter(variable => ![
                          'Hostname', 'IP Address', 'VDOM', 'Name', 'Source Address',
                          'Source Description', 'Source Interface', 'Destination Address',
                          'Destination Description', 'Destination Interface', 'Service'
                        ].includes(variable.name))
                        .map((variable) => (
                          <div
                            key={`variable-${variable.id || variable.name}`}
                            className="group relative"
                          >
                            <div className="flex items-center justify-between p-2 bg-gray-50 hover:bg-gray-100 rounded-md transition-colors duration-200">
                              <button
                                onClick={() => insertVariable(variable.name)}
                                className="flex-1 text-left flex items-center"
                              >
                                <span className="text-gray-700">{variable.name}</span>
                              </button>
                              <div className="flex items-center gap-2">
                                <Info className="w-4 h-4 text-gray-400" />
                                <button
                                  onClick={() => handleRemoveVariable(variable.id!)}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Trash2 className="w-4 h-4 text-red-500 hover:text-red-700" />
                                </button>
                              </div>
                            </div>
                            {showTooltip === variable.name && (
                              <div className="absolute z-10 w-48 px-3 py-2 bg-gray-800 text-white text-sm rounded-md shadow-lg -top-8 right-0">
                                {variable.description}
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center text-gray-500 py-4">
                  Aucune variable disponible
                </div>
              )}
            </div>

            <div className="border-t pt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Ajouter une variable</h3>
              <div className="space-y-3">
                <div>
                  <label htmlFor="variableName" className="block text-sm text-gray-600 mb-1">
                    Nom de la variable
                  </label>
                  <input
                    id="variableName"
                    name="variableName"
                    type="text"
                    value={newVariable.name}
                    onChange={(e) => setNewVariable({ ...newVariable, name: e.target.value })}
                    placeholder="Nom de la variable"
                    className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="variableDescription" className="block text-sm text-gray-600 mb-1">
                    Description
                  </label>
                  <input
                    id="variableDescription"
                    name="variableDescription"
                    type="text"
                    value={newVariable.description}
                    onChange={(e) => setNewVariable({ ...newVariable, description: e.target.value })}
                    placeholder="Description"
                    className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                <button
                  onClick={handleAddVariable}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors duration-200"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4 mr-2" />
                  )}
                  Ajouter
                </button>
              </div>
            </div>

            {/* Templates List */}
            <div className="border-t mt-6 pt-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Templates</h3>
                <button
                  onClick={() => navigate('/templates/new')}
                  className="flex items-center px-3 py-1.5 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Nouveau
                </button>
              </div>
              <div className="space-y-3">
                {isLoading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
                  </div>
                ) : templates && templates.length > 0 ? (
                  templates.map((template) => (
                    <div
                      key={`template-${template.id}`}
                      className="flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-md"
                    >
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{template.name}</div>
                        <div className="text-sm text-gray-500">
                          Créé le: {template.created_at ? new Date(template.created_at).toLocaleDateString() : 'N/A'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/templates/${template.id}`)}
                          className="p-1 text-blue-500 hover:text-blue-700"
                          title="Modifier"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDownloadExcel(template.id)}
                          className="p-1 text-green-500 hover:text-green-700"
                          title="Télécharger Excel"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="p-1 text-red-500 hover:text-red-700"
                          title="Supprimer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-4">
                    Aucun template disponible
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TemplateEditor;
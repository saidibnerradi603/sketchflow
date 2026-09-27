import React, { useState, useEffect } from 'react';
import { 
  PauseCircle, 
  CheckCircle2, 
  X, 
  Settings2, 
  Layers, 
  ShieldCheck, 
  AlertTriangle,
  UploadCloud,
  KeyRound,
  Plus,
  Trash2,
  Box,
  Split,
  Terminal,
  Webhook
} from 'lucide-react';

export default function HumanReviewModal({
  isOpen,
  sketchGraph,
  compiledWorkflow,
  validationReport,
  onApprove,
  onCancel,
  isDeploying = false
}) {
  // Generic node configurations map: { [nodeName]: { parameters: {}, credentials: {} } }
  const [nodeConfigs, setNodeConfigs] = useState({});
  const [newParamKeys, setNewParamKeys] = useState({});

  useEffect(() => {
    if (compiledWorkflow && compiledWorkflow.nodes) {
      const initialConfigs = {};
      compiledWorkflow.nodes.forEach((node) => {
        initialConfigs[node.name] = {
          parameters: { ...(node.parameters || {}) },
          credentialType: '',
          credentialNameOrId: ''
        };
      });
      setNodeConfigs(initialConfigs);
    }
  }, [compiledWorkflow]);

  if (!isOpen) return null;

  const handleParamChange = (nodeName, key, value) => {
    setNodeConfigs((prev) => ({
      ...prev,
      [nodeName]: {
        ...(prev[nodeName] || {}),
        parameters: {
          ...(prev[nodeName]?.parameters || {}),
          [key]: value
        }
      }
    }));
  };

  const handleRemoveParam = (nodeName, key) => {
    setNodeConfigs((prev) => {
      const currentParams = { ...(prev[nodeName]?.parameters || {}) };
      delete currentParams[key];
      return {
        ...prev,
        [nodeName]: {
          ...(prev[nodeName] || {}),
          parameters: currentParams
        }
      };
    });
  };

  const handleAddCustomParam = (nodeName) => {
    const key = (newParamKeys[nodeName] || '').trim();
    if (!key) return;

    setNodeConfigs((prev) => ({
      ...prev,
      [nodeName]: {
        ...(prev[nodeName] || {}),
        parameters: {
          ...(prev[nodeName]?.parameters || {}),
          [key]: ''
        }
      }
    }));
    setNewParamKeys((prev) => ({ ...prev, [nodeName]: '' }));
  };

  const handleCredentialChange = (nodeName, field, value) => {
    setNodeConfigs((prev) => ({
      ...prev,
      [nodeName]: {
        ...(prev[nodeName] || {}),
        [field]: value
      }
    }));
  };

  const handleSubmit = () => {
    // Format custom parameters and credentials for the backend
    const submission = {};
    Object.entries(nodeConfigs).forEach(([nodeName, config]) => {
      const formatted = {
        parameters: config.parameters || {}
      };

      if (config.credentialType && config.credentialNameOrId) {
        formatted.credentials = {
          [config.credentialType.trim()]: {
            id: config.credentialNameOrId.trim(),
            name: config.credentialNameOrId.trim()
          }
        };
      }
      submission[nodeName] = formatted;
    });

    onApprove(submission);
  };

  const nodes = compiledWorkflow?.nodes || [];
  const errors = validationReport?.errors || [];
  const isValid = validationReport?.valid ?? true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl rounded-2xl border border-white/15 bg-[#0F172A] shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <PauseCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white tracking-tight">
                Universal Human-in-the-Loop Review Checkpoint
              </h2>
              <p className="text-xs text-slate-400">
                Inspect AI-synthesized node parameters and bind credentials for any service before deployment.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeploying}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Linter Diagnostics Banner */}
          <div className={`p-4 rounded-xl border flex items-start space-x-3 ${
            isValid
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-amber-500/10 border-amber-500/20 text-amber-300'
          }`}>
            {isValid ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            )}
            <div className="text-xs space-y-1">
              <div className="font-semibold flex items-center space-x-2">
                <span>{isValid ? 'Workflow Architecture Validated' : 'Validation Diagnostics'}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 border border-white/10 text-white">
                  {nodes.length} Nodes • {Object.keys(compiledWorkflow?.connections || {}).length} Connections
                </span>
              </div>
              <p className="text-slate-300">
                {isValid
                  ? 'All node connections, execution order, and entry points conform to official n8n specifications.'
                  : 'Synthesized with warnings. You can adjust parameters or bind credentials below.'}
              </p>
              {errors.length > 0 && (
                <ul className="list-disc list-inside space-y-0.5 pt-1 text-amber-200/90 font-mono">
                  {errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Dynamic Service-Agnostic Nodes List */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center">
              <Layers className="w-4 h-4 mr-1.5 text-indigo-400" />
              Workflow Node Architecture & Configuration
            </h3>

            <div className="space-y-4">
              {nodes.map((node) => {
                const nodeConfig = nodeConfigs[node.name] || { parameters: {} };
                const params = nodeConfig.parameters || {};
                const paramEntries = Object.entries(params);

                return (
                  <div
                    key={node.name}
                    className="p-5 rounded-xl border border-white/10 bg-white/[0.02] hover:border-white/20 transition-all space-y-4"
                  >
                    {/* Node Header Pill */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/5">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                          <Box className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-white">{node.name}</h4>
                          <span className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                            {node.type}
                          </span>
                        </div>
                      </div>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400 self-start sm:self-auto">
                        Pos: [{node.position?.[0]}, {node.position?.[1]}]
                      </span>
                    </div>

                    {/* Dynamic Parameters List */}
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center">
                          <Settings2 className="w-3.5 h-3.5 mr-1 text-slate-500" />
                          Node Parameters ({paramEntries.length})
                        </label>
                      </div>

                      {paramEntries.length === 0 ? (
                        <p className="text-xs text-slate-500 italic">No initial parameters configured.</p>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {paramEntries.map(([key, val]) => {
                            const isComplex = typeof val === 'object' && val !== null;
                            const displayValue = isComplex ? JSON.stringify(val) : String(val ?? '');

                            return (
                              <div key={key} className="space-y-1 bg-black/30 p-2.5 rounded-lg border border-white/5">
                                <div className="flex items-center justify-between">
                                  <span className="text-[11px] font-mono font-medium text-cyan-300 truncate max-w-[200px]">
                                    {key}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveParam(node.name, key)}
                                    className="text-slate-600 hover:text-rose-400 p-0.5 transition-colors"
                                    title="Remove parameter"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </div>
                                <input
                                  type="text"
                                  value={displayValue}
                                  onChange={(e) => {
                                    let newVal = e.target.value;
                                    if (isComplex) {
                                      try {
                                        newVal = JSON.parse(e.target.value);
                                      } catch {
                                        // Keep as string if typing
                                      }
                                    }
                                    handleParamChange(node.name, key, newVal);
                                  }}
                                  className="w-full text-xs font-mono bg-black/50 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-400"
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Add Custom Parameter Control */}
                      <div className="flex items-center space-x-2 pt-1">
                        <input
                          type="text"
                          placeholder="Add parameter name (e.g. channel, url, apiKey)..."
                          value={newParamKeys[node.name] || ''}
                          onChange={(e) => setNewParamKeys((prev) => ({ ...prev, [node.name]: e.target.value }))}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault();
                              handleAddCustomParam(node.name);
                            }
                          }}
                          className="flex-1 text-xs font-mono bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-400"
                        />
                        <button
                          type="button"
                          onClick={() => handleAddCustomParam(node.name)}
                          className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-slate-300 transition-colors"
                        >
                          <Plus className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Add</span>
                        </button>
                      </div>
                    </div>

                    {/* Universal Credential & Authentication Binding */}
                    <div className="pt-3 border-t border-white/5 bg-white/[0.01] p-3 rounded-lg border border-dashed border-white/10 space-y-2">
                      <div className="flex items-center space-x-1.5 text-xs font-medium text-slate-300">
                        <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                        <span>Authentication & Credentials (Optional)</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">
                            Credential Type (e.g. slackApi, stripeApi, postgres, etc.)
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. slackApi, postgres, stripeApi"
                            value={nodeConfig.credentialType || ''}
                            onChange={(e) => handleCredentialChange(node.name, 'credentialType', e.target.value)}
                            className="w-full text-xs font-mono bg-black/40 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-400"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">
                            Credential Name / ID in your n8n instance
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. Production Key or Credential ID"
                            value={nodeConfig.credentialNameOrId || ''}
                            onChange={(e) => handleCredentialChange(node.name, 'credentialNameOrId', e.target.value)}
                            className="w-full text-xs font-mono bg-black/40 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-400"
                          />
                        </div>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-white/10 bg-white/[0.02] flex items-center justify-between">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeploying}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-colors"
          >
            Cancel Pipeline
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isDeploying}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl font-medium text-xs text-white bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 shadow-lg shadow-emerald-500/20 transition-all active:scale-[0.98]"
          >
            <UploadCloud className="w-4 h-4 text-emerald-200" />
            <span>Approve & Deploy to n8n Instance</span>
          </button>
        </div>

      </div>
    </div>
  );
}

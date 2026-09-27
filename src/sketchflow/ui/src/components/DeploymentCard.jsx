import React, { useState } from 'react';
import { 
  CheckCircle2, 
  ExternalLink, 
  Play, 
  Webhook, 
  Clock, 
  Check, 
  Copy, 
  Loader2, 
  Terminal,
  Activity
} from 'lucide-react';
import { testWebhookLive } from '../services/agentStream';

export default function DeploymentCard({
  deploymentResult,
  testResult: initialTestResult
}) {
  const [testResult, setTestResult] = useState(initialTestResult);
  const [isTesting, setIsTesting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [testPayload, setTestPayload] = useState(
    JSON.stringify(
      {
        lead_name: 'John Doe',
        company: 'Acme Corp',
        deal_value: 12000,
        email: 'john@acme.com',
        timestamp: new Date().toISOString()
      },
      null,
      2
    )
  );

  if (!deploymentResult) return null;

  const webhookUrl = deploymentResult.webhook_urls?.[0] || 'http://localhost:5678/webhook/test';
  const editorUrl = deploymentResult.editor_url || `http://localhost:5678/workflow/${deploymentResult.workflow_id}`;

  const handleCopyWebhook = () => {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFireWebhook = async () => {
    setIsTesting(true);
    try {
      let parsedPayload = {};
      try {
        parsedPayload = JSON.parse(testPayload);
      } catch (e) {
        alert('Invalid JSON in test payload');
        setIsTesting(false);
        return;
      }

      const res = await testWebhookLive({
        webhookUrl: webhookUrl,
        payload: parsedPayload
      });
      setTestResult(res);
    } catch (err) {
      console.error('Failed to trigger webhook test:', err);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-emerald-500/30 bg-[#0F172A] p-6 shadow-2xl space-y-6 glow-emerald">
      
      {/* Header & Status */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-semibold text-white">
                {deploymentResult.workflow_name || 'Synthesized Workflow'}
              </h3>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active & Live
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Workflow ID: <code className="font-mono text-slate-300">{deploymentResult.workflow_id}</code>
            </p>
          </div>
        </div>

        {/* 1-Click Launch n8n Editor */}
        <a
          href={editorUrl}
          target="_blank"
          rel="noreferrer"
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-medium shadow-lg shadow-indigo-500/20 transition-all active:scale-[0.98]"
        >
          <span>Open in n8n Canvas Editor</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Webhook Endpoint Strip */}
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center">
          <Webhook className="w-3.5 h-3.5 mr-1.5 text-indigo-400" />
          Live Webhook Endpoint
        </label>
        <div className="flex items-center space-x-2">
          <div className="flex-1 bg-black/40 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-300 overflow-x-auto truncate">
            {webhookUrl}
          </div>
          <button
            type="button"
            onClick={handleCopyWebhook}
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-colors"
            title="Copy URL"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Interactive Webhook Test Runner */}
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-200 flex items-center">
            <Activity className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
            Fire Live Test Event
          </span>
          <button
            type="button"
            onClick={handleFireWebhook}
            disabled={isTesting}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium text-xs transition-colors shadow-md shadow-emerald-500/20 disabled:opacity-50"
          >
            {isTesting ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Triggering...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>Send Webhook POST</span>
              </>
            )}
          </button>
        </div>

        {/* Payload JSON Editor */}
        <textarea
          rows={5}
          value={testPayload}
          onChange={(e) => setTestPayload(e.target.value)}
          className="w-full text-xs font-mono bg-black/50 border border-white/10 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-indigo-400"
          placeholder="JSON Payload"
        />

        {/* Test Result Display */}
        {testResult && (
          <div className="pt-2 border-t border-white/5 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Response Status:</span>
              <span className={`font-mono font-semibold ${
                testResult.success ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {testResult.status_code || 200} OK ({testResult.latency_ms || 32}ms)
              </span>
            </div>
            {testResult.response_data && (
              <pre className="text-[11px] font-mono bg-black/60 border border-white/5 rounded-lg p-2.5 text-emerald-300 overflow-x-auto">
                {JSON.stringify(testResult.response_data, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>

    </div>
  );
}

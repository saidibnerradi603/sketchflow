import React from 'react';
import { 
  Network, 
  Server, 
  Cpu, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle,
  FileCode2,
  Sparkles
} from 'lucide-react';

export default function Navbar({
  n8nStatus = 'connected',
  preferredProvider = 'nvidia',
  onProviderChange,
  isProcessing = false
}) {
  return (
    <header className="border-b border-white/10 bg-[#0B0F19]/90 backdrop-blur-md sticky top-0 z-30 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand identity */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-[1px] shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-[#080C14] rounded-[11px] flex items-center justify-center">
              <Network className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-semibold text-lg tracking-tight text-white flex items-center">
                SketchFlow
              </h1>
              <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Agentic v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 font-normal">
              Visual Diagram to Autonomous n8n Workflow Synthesizer
            </p>
          </div>
        </div>

        {/* Center / Right Control Panel */}
        <div className="flex items-center space-x-4">
          
          {/* Docker n8n instance status badge */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/10 text-xs">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">n8n Docker:</span>
            {n8nStatus === 'connected' ? (
              <span className="flex items-center space-x-1.5 text-emerald-400 font-medium">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span>Active (Port 5678)</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 text-amber-400 font-medium">
                <AlertCircle className="w-3 h-3 text-amber-400" />
                <span>Checking...</span>
              </span>
            )}
          </div>

          {/* Model Provider Selector */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/10 text-xs">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400 hidden md:inline">Intelligence:</span>
            <select
              value={preferredProvider}
              onChange={(e) => onProviderChange(e.target.value)}
              disabled={isProcessing}
              className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none cursor-pointer pr-1"
            >
              <option value="nvidia" className="bg-[#0F172A] text-slate-100">
                NVIDIA NIM (Kimi-k3 + Nemotron)
              </option>
              <option value="groq" className="bg-[#0F172A] text-slate-100">
                Groq Cloud (Qwen 3.8 + GPT-OSS)
              </option>
            </select>
          </div>

          {/* API Docs Button */}
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs text-slate-300 transition-colors"
            title="FastAPI Swagger Documentation"
          >
            <FileCode2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden lg:inline">Swagger API</span>
            <ExternalLink className="w-3 h-3 text-slate-500" />
          </a>
        </div>

      </div>
    </header>
  );
}

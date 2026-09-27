import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Trash2, 
  Eye, 
  Cpu, 
  PauseCircle, 
  UploadCloud, 
  Activity,
  CheckCircle2,
  Clock,
  Radio,
  Brain,
  Wrench,
  ChevronDown,
  ChevronRight,
  Code2,
  Sparkles,
  AlertCircle,
  Check
} from 'lucide-react';

export default function TelemetryConsole({
  logs = [],
  reasoningTrace = [],
  toolCalls = [],
  currentStep = 'idle',
  threadId = null,
  onClear
}) {
  const [activeTab, setActiveTab] = useState('terminal'); // 'terminal' | 'reasoning' | 'tools'
  const [expandedTools, setExpandedTools] = useState({});
  const scrollRef = useRef(null);

  // Auto-scroll terminal tab
  useEffect(() => {
    if (activeTab === 'terminal' && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, activeTab]);

  // Steps definition for lifecycle stepper
  const steps = [
    { id: 'perceive', label: 'Perception', icon: Eye },
    { id: 'compile', label: 'DAG Synthesis', icon: Cpu },
    { id: 'awaiting_review', label: 'Human Review', icon: PauseCircle },
    { id: 'deploy', label: 'n8n Deployment', icon: UploadCloud },
    { id: 'completed', label: 'Live Verification', icon: CheckCircle2 }
  ];

  const getStepStatus = (stepId) => {
    const stepOrder = ['started', 'perceive', 'compile', 'awaiting_review', 'deploy', 'completed'];
    const currentIndex = stepOrder.indexOf(currentStep);
    const thisIndex = stepOrder.indexOf(stepId);

    if (currentStep === 'completed') return 'completed';
    if (currentIndex === thisIndex) return 'active';
    if (currentIndex > thisIndex) return 'completed';
    return 'pending';
  };

  const toggleToolExpand = (id) => {
    setExpandedTools((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Helper to format log badges without raw emojis
  const formatLogItem = (log) => {
    let cleanText = log
      .replace(/🚀/g, '')
      .replace(/🔍/g, '')
      .replace(/✅/g, '')
      .replace(/📐/g, '')
      .replace(/⏸️/g, '')
      .replace(/🩺/g, '')
      .replace(/⚡/g, '')
      .replace(/⚠️/g, '')
      .replace(/🩹/g, '')
      .replace(/🎉/g, '')
      .replace(/🟢/g, '')
      .replace(/❌/g, '')
      .trim();

    let Icon = Terminal;
    let badgeColor = 'text-slate-400 bg-white/5 border-white/10';

    if (cleanText.includes('[Perception]')) {
      Icon = Eye;
      badgeColor = 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
    } else if (cleanText.includes('[Compiler]')) {
      Icon = Cpu;
      badgeColor = 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20';
    } else if (cleanText.includes('[Review]')) {
      Icon = PauseCircle;
      badgeColor = 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    } else if (cleanText.includes('[Deploy]') || cleanText.includes('[Deployment]')) {
      Icon = UploadCloud;
      badgeColor = 'text-purple-400 bg-purple-500/10 border-purple-500/20';
    } else if (cleanText.includes('[Self-Heal') || cleanText.includes('[Self-Healing]')) {
      Icon = Activity;
      badgeColor = 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    } else if (cleanText.includes('[Live Verification]')) {
      Icon = Activity;
      badgeColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    } else if (cleanText.includes('[Agent]')) {
      Icon = Radio;
      badgeColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    }

    return { cleanText, Icon, badgeColor };
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-white/10 bg-[#0B0F19] overflow-hidden shadow-2xl">
      
      {/* Console Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Agent Telemetry
          </span>
          {threadId && (
            <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-2 py-0.5 rounded border border-white/10">
              Session: {threadId.slice(0, 8)}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              currentStep === 'idle' ? 'bg-slate-400' : 'bg-indigo-400'
            }`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${
              currentStep === 'idle' ? 'bg-slate-500' : 'bg-indigo-500'
            }`}></span>
          </span>
          <span className="text-[11px] font-mono text-slate-400 uppercase">
            {currentStep}
          </span>
          {(logs.length > 0 || toolCalls.length > 0) && (
            <button
              type="button"
              onClick={onClear}
              className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-slate-300 transition-colors ml-2"
              title="Clear telemetry"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Visual Stepper */}
      <div className="grid grid-cols-5 border-b border-white/10 bg-black/20 px-3 py-2 text-center">
        {steps.map((step) => {
          const status = getStepStatus(step.id);
          const StepIcon = step.icon;

          let colorClass = 'text-slate-500 border-transparent';
          if (status === 'active') {
            colorClass = 'text-indigo-400 border-indigo-500/50 bg-indigo-500/10 font-semibold';
          } else if (status === 'completed') {
            colorClass = 'text-emerald-400 border-emerald-500/30';
          }

          return (
            <div
              key={step.id}
              className={`flex items-center justify-center space-x-1 py-1 px-1 rounded-md text-[11px] border transition-all ${colorClass}`}
            >
              <StepIcon className="w-3 h-3" />
              <span className="hidden sm:inline truncate">{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center space-x-1 px-3 py-2 border-b border-white/10 bg-white/[0.01]">
        <button
          type="button"
          onClick={() => setActiveTab('terminal')}
          className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'terminal'
              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Console Stream</span>
          {logs.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/10 text-slate-300 font-mono">
              {logs.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('reasoning')}
          className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'reasoning'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
        >
          <Brain className="w-3.5 h-3.5" />
          <span>Reasoning Trace</span>
          {reasoningTrace.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-300 font-mono">
              {reasoningTrace.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('tools')}
          className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'tools'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
        >
          <Wrench className="w-3.5 h-3.5" />
          <span>Tool Calls</span>
          {toolCalls.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 font-mono">
              {toolCalls.length}
            </span>
          )}
        </button>
      </div>

      {/* Main Tab View Area */}
      <div className="flex-1 overflow-y-auto terminal-scroll bg-[#080C14]/90 p-4">
        
        {/* TAB 1: Console Logs */}
        {activeTab === 'terminal' && (
          <div ref={scrollRef} className="space-y-2 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-slate-600 space-y-2 select-none">
                <Radio className="w-6 h-6 text-slate-700 animate-pulse" />
                <p className="text-xs">Awaiting workflow synthesis task...</p>
                <p className="text-[10px] text-slate-700">Events will stream here in real time via SSE</p>
              </div>
            ) : (
              logs.map((log, index) => {
                const { cleanText, Icon, badgeColor } = formatLogItem(log);
                return (
                  <div
                    key={index}
                    className="flex items-start space-x-2.5 animate-fadeIn"
                  >
                    <div className={`mt-0.5 p-1 rounded border flex-shrink-0 ${badgeColor}`}>
                      <Icon className="w-3 h-3" />
                    </div>
                    <div className="flex-1 leading-relaxed text-slate-300 break-words">
                      {cleanText}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* TAB 2: Chain of Thought Reasoning */}
        {activeTab === 'reasoning' && (
          <div className="space-y-3">
            {reasoningTrace.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-slate-600 space-y-2 select-none">
                <Brain className="w-6 h-6 text-slate-700" />
                <p className="text-xs">No reasoning recorded yet.</p>
                <p className="text-[10px] text-slate-700">The agent's internal monologue will appear here.</p>
              </div>
            ) : (
              reasoningTrace.map((r, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 space-y-2 relative overflow-hidden group hover:border-cyan-500/30 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">
                      Step: {r.step || 'General'}
                    </span>
                    <span className="text-[10px] text-slate-500 flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{r.timestamp ? new Date(r.timestamp * 1000).toLocaleTimeString() : `Thought #${i + 1}`}</span>
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans pl-1">
                    {r.thought}
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 3: Tool Calls Inspector */}
        {activeTab === 'tools' && (
          <div className="space-y-2.5">
            {toolCalls.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-slate-600 space-y-2 select-none">
                <Wrench className="w-6 h-6 text-slate-700" />
                <p className="text-xs">No tool calls dispatched yet.</p>
                <p className="text-[10px] text-slate-700">Tool inputs, outputs, and latencies will stream here.</p>
              </div>
            ) : (
              toolCalls.map((tc, idx) => {
                const isExpanded = !!expandedTools[tc.id || idx];
                const isRunning = tc.status === 'running';
                const isSuccess = tc.status === 'success';
                const isWarning = tc.status === 'warning';
                const isError = tc.status === 'error';

                return (
                  <div
                    key={tc.id || idx}
                    className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden transition-all hover:border-amber-500/30"
                  >
                    {/* Tool Bar Header */}
                    <div
                      onClick={() => toggleToolExpand(tc.id || idx)}
                      className="flex items-center justify-between p-3 cursor-pointer select-none hover:bg-white/[0.02] transition-colors"
                    >
                      <div className="flex items-center space-x-2.5">
                        <button
                          type="button"
                          className="text-slate-400 group-hover:text-white"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          )}
                        </button>
                        <Wrench className="w-3.5 h-3.5 text-amber-400" />
                        <span className="font-mono text-xs text-slate-200 font-semibold">
                          {tc.tool}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2">
                        {tc.duration_ms !== undefined && (
                          <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10">
                            {tc.duration_ms}ms
                          </span>
                        )}

                        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border ${
                          isRunning
                            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30 animate-pulse'
                            : isSuccess
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : isWarning
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}>
                          {tc.status || 'done'}
                        </span>
                      </div>
                    </div>

                    {/* Expandable JSON Detail Payload */}
                    {isExpanded && (
                      <div className="border-t border-white/5 bg-black/40 p-3 space-y-3 font-mono text-[11px]">
                        {tc.input && (
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold block mb-1">
                              Input Arguments:
                            </span>
                            <pre className="p-2 rounded bg-black/60 border border-white/5 text-amber-300/90 overflow-x-auto">
                              {JSON.stringify(tc.input, null, 2)}
                            </pre>
                          </div>
                        )}

                        {tc.output && (
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold block mb-1">
                              Output Result:
                            </span>
                            <pre className="p-2 rounded bg-black/60 border border-white/5 text-emerald-300/90 overflow-x-auto max-h-80 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed">
                              {typeof tc.output === 'string'
                                ? tc.output
                                : tc.output.content && typeof tc.output.content === 'string'
                                ? `--- Documentation Retrieved from ${tc.output.source || 'docs.n8n.io'} (${tc.output.length_chars || tc.output.content.length} chars) ---\n\n${tc.output.content}`
                                : JSON.stringify(tc.output, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

      </div>

    </div>
  );
}

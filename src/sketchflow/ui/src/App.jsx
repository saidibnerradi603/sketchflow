import React, { useState, useEffect } from 'react';
import { 
  PenTool, 
  UploadCloud, 
  Terminal, 
  CheckCircle2, 
  Radio, 
  Sparkles,
  Server,
  Layers,
  ArrowRight
} from 'lucide-react';

import Navbar from './components/Navbar';
import WhiteboardCanvas from './components/WhiteboardCanvas';
import PhotoUploader from './components/PhotoUploader';
import TelemetryConsole from './components/TelemetryConsole';
import HumanReviewModal from './components/HumanReviewModal';
import DeploymentCard from './components/DeploymentCard';

import { 
  startAgentStream, 
  resumeAgentStream, 
  checkSystemHealth 
} from './services/agentStream';

export default function App() {
  const [activeTab, setActiveTab] = useState('whiteboard');
  const [preferredProvider, setPreferredProvider] = useState('nvidia');
  const [n8nStatus, setN8nStatus] = useState('connected');
  
  // Pipeline Execution State
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [currentStep, setCurrentStep] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [reasoningTrace, setReasoningTrace] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  
  // Artifacts State
  const [selectedImage, setSelectedImage] = useState(null);
  const [sketchGraph, setSketchGraph] = useState(null);
  const [compiledWorkflow, setCompiledWorkflow] = useState(null);
  const [layoutPositions, setLayoutPositions] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [deploymentResult, setDeploymentResult] = useState(null);
  const [testResult, setTestResult] = useState(null);
  
  // Human-in-the-Loop Modal
  const [isReviewOpen, setIsReviewOpen] = useState(false);

  // Health check on mount
  useEffect(() => {
    checkSystemHealth().then((res) => {
      if (res && res.status === 'healthy') {
        setN8nStatus('connected');
      }
    });
  }, []);

  const handleStartSynthesis = async (inputData = null) => {
    const dataToUse = inputData || selectedImage;
    if (!dataToUse && !selectedImage) return;

    setIsProcessing(true);
    setDeploymentResult(null);
    setTestResult(null);
    setCurrentStep('started');
    const newThreadId = 'session-' + Date.now().toString(36);
    setThreadId(newThreadId);
    setLogs(['[Agent] Initializing autonomous SketchFlow pipeline stream...']);
    setReasoningTrace([]);
    setToolCalls([]);

    await startAgentStream({
      imageBase64: dataToUse?.base64 || null,
      imagePath: dataToUse?.path || null,
      preferredProvider: preferredProvider,
      threadId: newThreadId,
      onEvent: (eventType, data) => {
        if (eventType === 'started') {
          if (data.initial_log) {
            setLogs((prev) => [...prev, data.initial_log]);
          }
        } else if (eventType === 'thought') {
          setReasoningTrace((prev) => {
            const exists = prev.some((r) => r.thought === data.thought && r.step === data.step);
            if (exists) return prev;
            return [...prev, { ...data, timestamp: data.timestamp || Date.now() / 1000 }];
          });
        } else if (eventType === 'tool_call') {
          setToolCalls((prev) => {
            const toolId = data.id || data.tool;
            const existingIdx = prev.findIndex((t) => (t.id && t.id === toolId) || t.tool === data.tool);
            if (existingIdx >= 0) {
              const updated = [...prev];
              updated[existingIdx] = { ...updated[existingIdx], ...data };
              return updated;
            }
            return [...prev, data];
          });
        } else if (eventType === 'node_update') {
          if (data.current_step) setCurrentStep(data.current_step);
          if (data.logs && data.logs.length > 0) {
            setLogs(data.logs);
          }
          if (data.reasoning_trace && data.reasoning_trace.length > 0) {
            setReasoningTrace(data.reasoning_trace);
          }
          if (data.tool_calls && data.tool_calls.length > 0) {
            setToolCalls(data.tool_calls);
          }
          if (data.sketch_graph) setSketchGraph(data.sketch_graph);
          if (data.compiled_workflow) setCompiledWorkflow(data.compiled_workflow);
          if (data.layout_positions) setLayoutPositions(data.layout_positions);
          if (data.validation_report) setValidationReport(data.validation_report);
        } else if (eventType === 'checkpoint') {
          setCurrentStep('awaiting_review');
          if (data.sketch_graph) setSketchGraph(data.sketch_graph);
          if (data.compiled_workflow) setCompiledWorkflow(data.compiled_workflow);
          if (data.validation_report) setValidationReport(data.validation_report);
          if (data.reasoning_trace) setReasoningTrace(data.reasoning_trace);
          if (data.tool_calls) setToolCalls(data.tool_calls);
          if (data.logs) setLogs(data.logs);
          setIsProcessing(false);
          setIsReviewOpen(true);
        } else if (eventType === 'error') {
          setLogs((prev) => [...prev, `[Error] ${data.error}`]);
          setIsProcessing(false);
        }
      },
      onError: (err) => {
        setLogs((prev) => [...prev, `[Connection Error] ${err.message}`]);
        setIsProcessing(false);
      }
    });
  };

  const handleApproveCheckpoint = async (customParams) => {
    setIsReviewOpen(false);
    setIsDeploying(true);
    setCurrentStep('deploy');
    setLogs((prev) => [...prev, '[Review] User approved checkpoint. Resuming deployment to n8n...']);

    await resumeAgentStream({
      threadId: threadId,
      humanApproved: true,
      customParameters: customParams,
      onEvent: (eventType, data) => {
        if (eventType === 'thought') {
          setReasoningTrace((prev) => {
            const exists = prev.some((r) => r.thought === data.thought && r.step === data.step);
            if (exists) return prev;
            return [...prev, { ...data, timestamp: data.timestamp || Date.now() / 1000 }];
          });
        } else if (eventType === 'tool_call') {
          setToolCalls((prev) => {
            const toolId = data.id || data.tool;
            const existingIdx = prev.findIndex((t) => (t.id && t.id === toolId) || t.tool === data.tool);
            if (existingIdx >= 0) {
              const updated = [...prev];
              updated[existingIdx] = { ...updated[existingIdx], ...data };
              return updated;
            }
            return [...prev, data];
          });
        } else if (eventType === 'node_update') {
          if (data.current_step) setCurrentStep(data.current_step);
          if (data.logs) setLogs(data.logs);
          if (data.reasoning_trace && data.reasoning_trace.length > 0) {
            setReasoningTrace(data.reasoning_trace);
          }
          if (data.tool_calls && data.tool_calls.length > 0) {
            setToolCalls(data.tool_calls);
          }
          if (data.deployment_result) setDeploymentResult(data.deployment_result);
          if (data.test_result) setTestResult(data.test_result);
        } else if (eventType === 'complete') {
          setCurrentStep('completed');
          if (data.deployment_result) setDeploymentResult(data.deployment_result);
          if (data.test_result) setTestResult(data.test_result);
          if (data.reasoning_trace) setReasoningTrace(data.reasoning_trace);
          if (data.tool_calls) setToolCalls(data.tool_calls);
          if (data.logs) setLogs(data.logs);
          setIsDeploying(false);
        } else if (eventType === 'error') {
          setLogs((prev) => [...prev, `[Deploy Error] ${data.error}`]);
          setIsDeploying(false);
        }
      },
      onError: (err) => {
        setLogs((prev) => [...prev, `[Resume Connection Error] ${err.message}`]);
        setIsDeploying(false);
      }
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#080C14] text-slate-100">
      
      {/* Top Navigation */}
      <Navbar
        n8nStatus={n8nStatus}
        preferredProvider={preferredProvider}
        onProviderChange={setPreferredProvider}
        isProcessing={isProcessing || isDeploying}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Visual Creation & Diagram Ingestion Studio (7 cols) */}
        <section className="lg:col-span-7 flex flex-col space-y-4">
          
          {/* Tab Selector Header */}
          <div className="flex items-center justify-between p-1.5 rounded-xl bg-white/[0.03] border border-white/10">
            <div className="flex items-center space-x-1">
              <button
                type="button"
                onClick={() => setActiveTab('whiteboard')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'whiteboard'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <PenTool className="w-3.5 h-3.5" />
                <span>Whiteboard Studio</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('upload')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'upload'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Photo / Sketch Upload</span>
              </button>
            </div>

            <div className="text-[11px] text-slate-500 font-mono hidden sm:inline px-2">
              {activeTab === 'whiteboard' ? 'Excalidraw Vector Canvas' : 'Vision Multimodal OCR'}
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 min-h-[500px]">
            {activeTab === 'whiteboard' ? (
              <WhiteboardCanvas
                onSynthesize={(data) => {
                  setSelectedImage(data);
                  handleStartSynthesis(data);
                }}
                isProcessing={isProcessing || isDeploying}
              />
            ) : (
              <PhotoUploader
                onImageSelected={setSelectedImage}
                onSynthesize={() => handleStartSynthesis()}
                isProcessing={isProcessing || isDeploying}
              />
            )}
          </div>

          {/* Deployment Card (Appears once successfully deployed) */}
          {deploymentResult && (
            <DeploymentCard
              deploymentResult={deploymentResult}
              testResult={testResult}
            />
          )}

        </section>

        {/* Right Column: Telemetry & Synthesis Hub (5 cols) */}
        <section className="lg:col-span-5 flex flex-col space-y-4">
          <TelemetryConsole
            logs={logs}
            reasoningTrace={reasoningTrace}
            toolCalls={toolCalls}
            currentStep={currentStep}
            threadId={threadId}
            onClear={() => {
              setLogs([]);
              setReasoningTrace([]);
              setToolCalls([]);
            }}
          />
        </section>

      </main>

      {/* Human-in-the-Loop Review Modal */}
      <HumanReviewModal
        isOpen={isReviewOpen}
        sketchGraph={sketchGraph}
        compiledWorkflow={compiledWorkflow}
        validationReport={validationReport}
        onApprove={handleApproveCheckpoint}
        onCancel={() => setIsReviewOpen(false)}
        isDeploying={isDeploying}
      />

    </div>
  );
}

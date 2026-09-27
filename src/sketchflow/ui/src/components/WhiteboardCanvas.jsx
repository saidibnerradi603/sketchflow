import React, { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, 
  Trash2, 
  FolderDown, 
  Loader2, 
  PenTool, 
  RotateCcw
} from 'lucide-react';

export default function WhiteboardCanvas({
  onSynthesize,
  isProcessing = false
}) {
  const [excalidrawAPI, setExcalidrawAPI] = useState(null);
  const [ExcalidrawComponent, setExcalidrawComponent] = useState(null);
  const [exportHelper, setExportHelper] = useState(null);
  const [isLoadingBundle, setIsLoadingBundle] = useState(true);

  // Dynamically import Excalidraw to ensure clean client-side rendering
  useEffect(() => {
    let isMounted = true;
    import('@excalidraw/excalidraw')
      .then((comp) => {
        if (isMounted) {
          setExcalidrawComponent(() => comp.Excalidraw);
          setExportHelper(() => comp.exportToBlob);
          setIsLoadingBundle(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load @excalidraw/excalidraw bundle:', err);
        setIsLoadingBundle(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleClear = () => {
    if (excalidrawAPI) {
      excalidrawAPI.resetScene();
      excalidrawAPI.updateScene({
        appState: {
          viewBackgroundColor: '#ffffff',
          currentItemStrokeColor: '#000000',
          currentItemBackgroundColor: 'transparent'
        }
      });
    }
  };

  const handleSynthesize = async () => {
    if (!excalidrawAPI || !exportHelper) return;

    try {
      const elements = typeof excalidrawAPI.getSceneElements === 'function'
        ? excalidrawAPI.getSceneElements()
        : (typeof excalidrawAPI.getElements === 'function' ? excalidrawAPI.getElements() : []);

      if (!elements || elements.length === 0) {
        alert('Please draw your workflow diagram on the canvas before synthesizing.');
        return;
      }

      const appState = excalidrawAPI.getAppState ? excalidrawAPI.getAppState() : {};
      const files = excalidrawAPI.getFiles ? excalidrawAPI.getFiles() : {};

      const blob = await exportHelper({
        elements,
        appState: {
          ...appState,
          exportWithDarkMode: false,
          exportBackground: true,
          viewBackgroundColor: '#ffffff'
        },
        files,
        mimeType: 'image/png'
      });

      const reader = new FileReader();
      reader.onloadend = () => {
        const base64Data = reader.result;
        onSynthesize({
          base64: base64Data,
          path: null
        });
      };
      reader.readAsDataURL(blob);

    } catch (err) {
      console.error('Failed to export canvas to image:', err);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handleClear}
            disabled={isProcessing}
            className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-white/10 transition-colors flex items-center space-x-1.5"
            title="Reset Canvas"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Canvas</span>
          </button>
        </div>

        {/* Synthesize Button */}
        <button
          type="button"
          onClick={handleSynthesize}
          disabled={isProcessing || isLoadingBundle}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-xl font-medium text-xs transition-all shadow-md ${
            isProcessing || isLoadingBundle
              ? 'bg-white/5 text-slate-500 border border-white/5 cursor-not-allowed'
              : 'bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white shadow-indigo-500/20 active:scale-[0.98]'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Synthesizing...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
              <span>Synthesize Drawn Workflow</span>
            </>
          )}
        </button>
      </div>

      {/* Canvas Workspace */}
      <div className="relative flex-1 min-h-[460px] rounded-2xl overflow-hidden border border-white/10 bg-white shadow-2xl">
        {isLoadingBundle ? (
          <div className="w-full h-full flex flex-col items-center justify-center space-y-3 bg-[#080C14]">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            <p className="text-xs text-slate-400">Loading Whiteboard Studio...</p>
          </div>
        ) : ExcalidrawComponent ? (
          <ExcalidrawComponent
            excalidrawAPI={(api) => setExcalidrawAPI(api)}
            theme="light"
            initialData={{
              appState: {
                viewBackgroundColor: '#ffffff',
                currentItemStrokeColor: '#000000',
                currentItemBackgroundColor: 'transparent',
                currentItemFontFamily: 1
              }
            }}
            UIOptions={{
              canvasActions: {
                loadScene: false,
                saveToActiveFile: false,
                theme: false
              }
            }}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-slate-400">
            <PenTool className="w-8 h-8 text-slate-500 mb-2" />
            <p className="text-sm">Whiteboard Canvas failed to initialize.</p>
            <p className="text-xs text-slate-600 mt-1">Please use the Photo / Diagram Uploader tab.</p>
          </div>
        )}
      </div>

    </div>
  );
}

import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Image as ImageIcon, 
  FileText, 
  Sparkles, 
  Trash2, 
  CheckCircle2, 
  Loader2
} from 'lucide-react';

export default function PhotoUploader({
  onImageSelected,
  onSynthesize,
  isProcessing = false
}) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result);
      if (onImageSelected) {
        onImageSelected({
          file: file,
          base64: reader.result,
          path: null
        });
      }
    };
    reader.readAsDataURL(file);
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    if (inputRef.current) inputRef.current.value = '';
    if (onImageSelected) onImageSelected(null);
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      
      {/* Dropzone container */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !previewUrl && inputRef.current?.click()}
        className={`relative flex-1 min-h-[340px] rounded-2xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center p-6 text-center ${
          dragActive
            ? 'border-indigo-400 bg-indigo-500/10 glow-indigo'
            : previewUrl
            ? 'border-white/10 bg-[#0B0F19]/50'
            : 'border-white/15 bg-white/[0.02] hover:border-white/30 hover:bg-white/[0.03] cursor-pointer'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/jpg"
          onChange={handleChange}
          className="hidden"
          disabled={isProcessing}
        />

        {previewUrl ? (
          <div className="relative w-full h-full flex flex-col items-center justify-center">
            <img
              src={previewUrl}
              alt="Diagram Preview"
              className="max-h-[300px] w-auto object-contain rounded-xl shadow-2xl border border-white/10"
            />
            <div className="mt-4 flex items-center space-x-3">
              <span className="text-xs font-mono text-slate-400 bg-white/5 px-2.5 py-1 rounded-md border border-white/10">
                {selectedFile?.name || 'Uploaded Image'}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  clearSelection();
                }}
                disabled={isProcessing}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-colors"
                title="Remove diagram"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-3 pointer-events-none">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-inner">
              <UploadCloud className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Drag & drop whiteboard photo or paper sketch
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PNG, JPG, or WEBP up to 20MB
              </p>
            </div>
            <button
              type="button"
              className="mt-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-medium text-slate-300 hover:bg-white/10 pointer-events-auto"
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
            >
              Browse Files
            </button>
          </div>
        )}
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-end pt-2">
        {/* Primary Action Button */}
        <button
          type="button"
          onClick={onSynthesize}
          disabled={!previewUrl || isProcessing}
          className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all shadow-lg ${
            !previewUrl || isProcessing
              ? 'bg-white/5 text-slate-500 border border-white/5 cursor-not-allowed'
              : 'bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white shadow-indigo-500/20 active:scale-[0.98]'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Analyzing Diagram...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-cyan-300" />
              <span>Synthesize n8n Workflow</span>
            </>
          )}
        </button>
      </div>

    </div>
  );
}

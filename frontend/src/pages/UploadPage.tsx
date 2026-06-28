import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileVideo, Sparkles, Zap, DollarSign, Cpu, Clock, Globe } from 'lucide-react';
import { ModelType, ModeType } from '../types';
import { api } from '../services/api';
import { ErrorBanner } from '../components/ui/ErrorBanner';

const MODEL_RATES: Record<ModelType, { name: string; badge: string; desc: string; inRate: number; outRate: number }> = {
  'gemini-3.1-pro': {
    name: 'Gemini 3.1 Pro', badge: 'Highest Quality',
    desc: 'Deep multi-modal audit with frame-accurate precision & 2M token context.',
    inRate: 2.00, outRate: 12.00,
  },
  'gemini-3.5-flash': {
    name: 'Gemini 3.5 Flash', badge: 'Best Value',
    desc: 'High speed multimodal engine balanced for detailed audio-visual verification.',
    inRate: 1.50, outRate: 9.00,
  },
  'gemini-2.5-flash': {
    name: 'Gemini 2.5 Flash', badge: 'Budget',
    desc: 'Cost-optimized analysis ideal for rapid draft reviews and quick checks.',
    inRate: 0.30, outRate: 2.50,
  },
};

const LANGUAGES = [
  { code: 'hu', label: 'Hungarian (Magyar)' },
  { code: 'en', label: 'English' },
  { code: 'de', label: 'German (Deutsch)' },
  { code: 'es', label: 'Spanish (Español)' },
  { code: 'fr', label: 'French (Français)' },
];

const ALLOWED_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv'];

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [model, setModel] = useState<ModelType>('gemini-3.5-flash');
  const [mode, setMode] = useState<ModeType>('realtime');
  const [videoLanguage, setVideoLanguage] = useState<string>('hu');
  const [reportLanguage, setReportLanguage] = useState<string>('hu');
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  const estimatedCost = useMemo(() => {
    if (!file) return 0.00;
    const sizeMb = file.size / (1024 * 1024);
    const estInputTokens = Math.round(sizeMb * 900) + 5000;
    const estOutputTokens = 2500;
    const rate = MODEL_RATES[model];
    let cost = (estInputTokens / 1_000_000) * rate.inRate + (estOutputTokens / 1_000_000) * rate.outRate;
    if (mode === 'batch') cost *= 0.50;
    return Math.max(cost, 0.001);
  }, [file, model, mode]);

  const validateAndSetFile = useCallback((selected: File) => {
    const ext = selected.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext || '')) {
      setError('Invalid format. Please select an MP4, MOV, AVI, or MKV file.');
      return;
    }
    setFile(selected);
    setError(null);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  // Drag and Drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  }, [validateAndSetFile]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    // Simulate progress during upload (fetch doesn't support upload progress natively)
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => Math.min(prev + Math.random() * 8, 90));
    }, 400);

    try {
      const res = await api.uploadJob(file, prompt, model, mode, videoLanguage, reportLanguage);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setTimeout(() => navigate(`/jobs/${res.job_id}`), 300);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.detail || err.message || 'Error uploading video');
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 animate-fade-in">
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-3">
          AI Video Quality <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">Auditor</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          Upload your video for exhaustive, frame-accurate multimodal AI analysis powered by Google Gemini AI.
        </p>
      </div>

      {error && <div className="mb-6"><ErrorBanner message={error} onRetry={() => setError(null)} /></div>}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* File Upload Zone — with real drag-and-drop */}
        <div
          className={`glass-panel p-8 rounded-2xl border-2 border-dashed text-center transition-all duration-200 ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-950/30 scale-[1.01]'
              : file
              ? 'border-emerald-500/40 bg-emerald-950/10'
              : 'border-slate-700 hover:border-slate-600'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <label className="cursor-pointer block group">
            <input
              type="file"
              accept=".mp4,.mov,.avi,.mkv"
              onChange={handleFileChange}
              className="hidden"
              id="video-upload-input"
            />
            <div className={`w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center transition-all ${
              isDragOver
                ? 'bg-indigo-600/30 border-indigo-500/40 scale-110'
                : file
                ? 'bg-emerald-600/10 border-emerald-500/20'
                : 'bg-indigo-600/10 border-indigo-500/20 group-hover:scale-110 group-hover:bg-indigo-600/20'
            } border`}>
              {file ? <FileVideo className="w-8 h-8 text-emerald-400" /> : <Upload className="w-8 h-8 text-indigo-400" />}
            </div>
            {file ? (
              <div>
                <p className="font-semibold text-lg text-emerald-300">{file.name}</p>
                <p className="text-sm text-slate-400 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB • Click or drop to replace</p>
              </div>
            ) : (
              <div>
                <p className="font-semibold text-lg text-slate-200">
                  {isDragOver ? 'Drop your video here' : 'Drag & Drop or Click to Upload Video'}
                </p>
                <p className="text-sm text-slate-400 mt-1">Supports MP4, MOV, AVI, MKV up to 2GB</p>
              </div>
            )}
          </label>
        </div>

        {/* Upload Progress Bar */}
        {uploading && (
          <div className="space-y-2 animate-fade-in">
            <div className="flex justify-between text-xs font-mono text-slate-400">
              <span>Uploading & initializing pipeline...</span>
              <span>{Math.round(uploadProgress)}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Language Selection Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800">
          <label className="block text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Globe className="w-4 h-4 text-indigo-400" />
            Language Configurations
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="video-lang" className="block text-xs font-medium text-slate-400 mb-1.5">Video Audio Language</label>
              <select
                id="video-lang"
                value={videoLanguage}
                onChange={(e) => setVideoLanguage(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors text-sm"
              >
                {LANGUAGES.map((lang) => (<option key={`video-${lang.code}`} value={lang.code}>{lang.label}</option>))}
              </select>
            </div>
            <div>
              <label htmlFor="report-lang" className="block text-xs font-medium text-slate-400 mb-1.5">Audit Report Language</label>
              <select
                id="report-lang"
                value={reportLanguage}
                onChange={(e) => setReportLanguage(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors text-sm"
              >
                {LANGUAGES.map((lang) => (<option key={`report-${lang.code}`} value={lang.code}>{lang.label}</option>))}
              </select>
            </div>
          </div>
        </div>

        {/* Custom Requirements Prompt */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800">
          <label htmlFor="analysis-prompt" className="block text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Analysis Requirements & Custom Focus (Optional)
          </label>
          <textarea
            id="analysis-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="E.g., Pay special attention to code typos in terminal windows, Hungarian terminology consistency, and filler words."
            className="w-full h-28 bg-slate-900/80 border border-slate-700/80 rounded-xl p-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Model Selector Cards */}
        <div>
          <label className="block text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" />
            Select AI Engine
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(Object.keys(MODEL_RATES) as ModelType[]).map((mKey) => {
              const info = MODEL_RATES[mKey];
              const isSelected = model === mKey;
              return (
                <div
                  key={mKey}
                  onClick={() => setModel(mKey)}
                  className={`cursor-pointer p-5 rounded-2xl border transition-all relative ${
                    isSelected
                      ? 'bg-indigo-950/40 border-indigo-500 shadow-lg shadow-indigo-500/10'
                      : 'glass-panel border-slate-800 hover:border-slate-700'
                  }`}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setModel(mKey)}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-bold text-slate-100">{info.name}</span>
                    <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full ${
                      mKey === 'gemini-3.5-flash' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-slate-800 text-slate-300'
                    }`}>
                      {info.badge}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">{info.desc}</p>
                  <div className="text-[11px] font-mono text-slate-400 pt-3 border-t border-slate-800/80 flex justify-between">
                    <span>In: ${info.inRate}/M</span>
                    <span>Out: ${info.outRate}/M</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Execution Mode & Live Cost Estimator */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel p-6 rounded-2xl border border-slate-800">
            <label className="block text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              Processing Mode
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMode('realtime')}
                className={`py-3 px-4 rounded-xl font-medium text-sm border transition-all flex items-center justify-center gap-2 ${
                  mode === 'realtime'
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                }`}
              >
                <Zap className="w-4 h-4" /> Realtime
              </button>
              <button
                type="button"
                onClick={() => setMode('batch')}
                className={`py-3 px-4 rounded-xl font-medium text-sm border transition-all flex items-center justify-center gap-2 ${
                  mode === 'batch'
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                }`}
              >
                <DollarSign className="w-4 h-4" /> Batch (50% Off)
              </button>
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
            <span className="text-sm font-semibold text-slate-400 block mb-1">Estimated Run Cost</span>
            <div className="flex items-baseline gap-2 my-auto">
              <span className="text-3xl font-mono font-extrabold text-emerald-400">${estimatedCost.toFixed(4)}</span>
              <span className="text-xs text-slate-400">USD</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Calculated based on file size, selected model rates, and execution tier.
            </p>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!file || uploading}
          id="submit-analysis-btn"
          className={`w-full py-4 rounded-2xl font-bold text-lg text-white shadow-xl transition-all flex items-center justify-center gap-3 ${
            !file || uploading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:opacity-90 shadow-indigo-600/25 hover:shadow-indigo-600/40'
          }`}
        >
          {uploading ? (
            <>
              <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Processing Upload...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-6 h-6" />
              <span>Start Video Quality Analysis</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};

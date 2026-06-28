import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileVideo, ArrowRight, RefreshCw } from 'lucide-react';
import { JobStatusResponse, JobStatus } from '../types';
import { api } from '../services/api';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { StatusStepper, StageDefinition } from '../components/ui/StatusStepper';
import { QuotaBanner } from '../components/ui/QuotaBanner';

const STAGES: StageDefinition[] = [
  { id: 'PREPROCESSING', name: 'Stage 1: Preprocessing', desc: 'Normalizing video layout & extracting clean audio stream via FFmpeg...' },
  { id: 'TRANSCRIBING', name: 'Stage 2: Transcribing', desc: 'Aligning word-level timestamps with Whisper audio transcription...' },
  { id: 'ANALYZING', name: 'Stage 3: AI Analysis', desc: 'Running multimodal audit with Gemini AI engine...' },
  { id: 'VALIDATING', name: 'Stage 4: Validation', desc: 'Cross-validating potential critical issues...' },
  { id: 'FINALIZING', name: 'Stage 5: Finalizing', desc: 'Compiling scorecards and saving final report...' },
];

const STAGE_ORDER: JobStatus[] = ['QUEUED', 'PREPROCESSING', 'TRANSCRIBING', 'ANALYZING', 'VALIDATING', 'FINALIZING', 'DONE'];

export const JobStatusPage: React.FC = () => {
  const { job_id } = useParams<{ job_id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [countdownSeconds, setCountdownSeconds] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const startTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!job_id) return;

    const fetchStatus = async () => {
      try {
        const data = await api.getJobStatus(job_id);
        setJob(data);
        setError(null);

        if (data.is_quota_limited && data.retry_after_seconds) {
          setCountdownSeconds(Math.ceil(data.retry_after_seconds));
        } else if (!data.is_quota_limited) {
          setCountdownSeconds(0);
        }

        if (data.status === 'DONE') {
          setTimeout(() => navigate(`/jobs/${job_id}/report`), 1500);
        }
      } catch (err: any) {
        setError(err.detail || err.message || 'Failed to fetch status');
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [job_id, navigate]);

  // Countdown timer for rate limits
  useEffect(() => {
    if (countdownSeconds <= 0) return;
    const timer = setInterval(() => {
      setCountdownSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdownSeconds]);

  // Elapsed time tracker
  useEffect(() => {
    if (!job || job.status === 'DONE' || job.status === 'FAILED') return;
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [job]);

  const formatElapsed = (secs: number): string => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const getProgressPercentage = (): number => {
    if (!job) return 0;
    if (job.status === 'DONE') return 100;
    if (job.status === 'FAILED') return 0;
    const currentIndex = STAGE_ORDER.indexOf(job.status);
    if (currentIndex <= 0) return 10;
    return Math.min(95, Math.round((currentIndex / (STAGE_ORDER.length - 1)) * 100));
  };

  if (error) {
    return (
      <div className="max-w-xl mx-auto my-20 px-4 space-y-6 animate-fade-in">
        <ErrorBanner message={error} variant="error" />
        <div className="flex justify-center gap-3">
          <button
            onClick={() => { setError(null); startTimeRef.current = Date.now(); }}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
          <button
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium transition-colors"
          >
            Return to Upload Studio
          </button>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-xl mx-auto my-20 text-center animate-fade-in">
        <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400 font-medium">Connecting to job worker engine...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12 animate-fade-in">
      <div className="glass-panel p-8 rounded-3xl border border-slate-800 mb-8 shadow-2xl relative overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-6 mb-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-indigo-400 font-mono font-bold">Job Status Monitor</span>
            <h1 className="text-2xl font-bold text-white mt-1 flex items-center gap-3">
              <FileVideo className="w-6 h-6 text-slate-400 shrink-0" />
              <span className="truncate max-w-md">{job.original_filename}</span>
            </h1>
          </div>
          <div className="text-right shrink-0 space-y-1">
            <div>
              <span className="text-xs text-slate-400 block">Model Engine</span>
              <span className="font-mono text-sm font-semibold text-slate-200">{job.model_used}</span>
            </div>
            {job.status !== 'DONE' && job.status !== 'FAILED' && (
              <div>
                <span className="text-xs text-slate-400 block">Elapsed</span>
                <span className="font-mono text-sm font-semibold text-indigo-300">{formatElapsed(elapsedSeconds)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-slate-400 font-mono mb-2">
            <span>Pipeline Execution Progress</span>
            <span>{getProgressPercentage()}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                job.status === 'FAILED' ? 'bg-red-500'
                : job.status === 'DONE' ? 'bg-emerald-500'
                : 'bg-gradient-to-r from-indigo-500 to-teal-400 animate-pulse'
              }`}
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>
        </div>

        {/* Quota Warning Banner */}
        {job.is_quota_limited && <QuotaBanner countdownSeconds={countdownSeconds} />}

        {job.status === 'FAILED' ? (
          <div className="p-5 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm space-y-3">
            <ErrorBanner message={job.error_message || 'Unknown processing error'} variant="error" />
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium transition-colors"
            >
              Upload New Video
            </button>
          </div>
        ) : (
          <StatusStepper
            stages={STAGES}
            currentStatus={job.status}
            isQuotaLimited={job.is_quota_limited || false}
          />
        )}
      </div>

      {job.status === 'DONE' && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/50 via-teal-950/50 to-indigo-950/50 border border-emerald-500/30 text-center animate-pulse-glow">
          <h2 className="text-lg font-bold text-emerald-300 mb-2">Analysis Completed Successfully!</h2>
          <p className="text-sm text-slate-300 mb-4">Redirecting to executive report scorecard...</p>
          <button
            onClick={() => navigate(`/jobs/${job_id}/report`)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-600/20 transition-all"
          >
            <span>View Full Report</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

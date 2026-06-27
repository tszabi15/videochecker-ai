import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, Loader2, AlertTriangle, FileVideo, Cpu, ArrowRight, Clock } from 'lucide-react';
import { JobStatusResponse, JobStatus } from '../types';
import { api } from '../services/api';

const STAGES: { id: JobStatus; name: string; desc: string }[] = [
  { id: 'PREPROCESSING', name: 'Stage 1: Preprocessing', desc: 'Normalizing video layout & extracting clean audio stream via FFmpeg...' },
  { id: 'TRANSCRIBING', name: 'Stage 2: Transcribing', desc: 'Aligning word-level timestamps with OpenAI Whisper...' },
  { id: 'ANALYZING', name: 'Stage 3: AI Analysis', desc: 'Running multimodal audit with Gemini 3.5 Flash...' },
  { id: 'VALIDATING', name: 'Stage 4: Validation', desc: 'Cross-validating potential critical issues...' },
  { id: 'FINALIZING', name: 'Stage 5: Finalizing', desc: 'Compiling scorecards and saving final report...' },
];

export const JobStatusPage: React.FC = () => {
  const { job_id } = useParams<{ job_id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [countdownSeconds, setCountdownSeconds] = useState<number>(0);

  useEffect(() => {
    if (!job_id) return;

    const fetchStatus = async () => {
      try {
        const data = await api.getJobStatus(job_id);
        setJob(data);

        if (data.is_quota_limited && data.retry_after_seconds) {
          setCountdownSeconds(Math.ceil(data.retry_after_seconds));
        } else if (!data.is_quota_limited) {
          setCountdownSeconds(0);
        }

        if (data.status === 'DONE') {
          setTimeout(() => {
            navigate(`/jobs/${job_id}/report`);
          }, 1500);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch status');
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [job_id, navigate]);

  // Client-side live countdown timer effect
  useEffect(() => {
    if (countdownSeconds <= 0) return;

    const timer = setInterval(() => {
      setCountdownSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [countdownSeconds]);

  if (error) {
    return (
      <div className="max-w-xl mx-auto my-20 p-8 rounded-2xl bg-red-950/40 border border-red-500/40 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-red-200 mb-2">Analysis Task Error</h2>
        <p className="text-slate-300 text-sm mb-6">{error}</p>
        <button onClick={() => navigate('/')} className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium">
          Return to Upload Studio
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-xl mx-auto my-20 text-center">
        <Loader2 className="w-10 h-10 text-indigo-400 animate-spin mx-auto mb-4" />
        <p className="text-slate-400 font-medium">Connecting to job worker engine...</p>
      </div>
    );
  }

  const STAGE_ORDER: JobStatus[] = ['QUEUED', 'PREPROCESSING', 'TRANSCRIBING', 'ANALYZING', 'VALIDATING', 'FINALIZING', 'DONE'];
  const currentIndex = STAGE_ORDER.indexOf(job.status);

  const getStageState = (stageId: JobStatus) => {
    const stageIndex = STAGE_ORDER.indexOf(stageId);

    if (job.status === 'FAILED') return 'failed';
    if (job.status === 'DONE') return 'completed';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'active';
    return 'pending';
  };

  const getProgressPercentage = () => {
    if (job.status === 'DONE') return 100;
    if (job.status === 'FAILED') return 0;
    if (currentIndex <= 0) return 10;
    return Math.min(95, Math.round((currentIndex / (STAGE_ORDER.length - 1)) * 100));
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="glass-panel p-8 rounded-3xl border border-slate-800 mb-8 shadow-2xl relative overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-6 mb-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-indigo-400 font-mono font-bold">Job Status Monitor</span>
            <h1 className="text-2xl font-bold text-white mt-1 flex items-center gap-3">
              <FileVideo className="w-6 h-6 text-slate-400 shrink-0" />
              <span className="truncate max-w-md">{job.original_filename}</span>
            </h1>
          </div>
          <div className="text-right shrink-0">
            <span className="text-xs text-slate-400 block">Model Engine</span>
            <span className="font-mono text-sm font-semibold text-slate-200">{job.model_used}</span>
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
                job.status === 'FAILED'
                  ? 'bg-red-500'
                  : job.status === 'DONE'
                  ? 'bg-emerald-500'
                  : 'bg-gradient-to-r from-indigo-500 to-teal-400 animate-pulse'
              }`}
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>
        </div>

        {/* Dynamic Quota Limit Warning Banner & Live Countdown Timer */}
        {job.is_quota_limited && (
          <div className="mb-8 p-5 rounded-2xl bg-amber-950/70 border border-amber-500/60 flex items-start gap-4 shadow-xl shadow-amber-950/40 animate-pulse">
            <AlertTriangle className="w-7 h-7 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-amber-200 mb-1.5 flex items-center gap-2">
                <span>⚠️ Google Free-Tier rate limit reached</span>
              </h4>
              <p className="text-xs text-amber-300/95 leading-relaxed font-medium">
                The system is automatically waiting for{' '}
                <span className="font-mono font-bold text-amber-200 px-1.5 py-0.5 bg-amber-900/60 rounded border border-amber-500/40">
                  {countdownSeconds}s
                </span>{' '}
                before retrying. Do not close this page.
              </p>
            </div>
          </div>
        )}

        {job.status === 'FAILED' ? (
          <div className="p-5 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm">
            <p className="font-bold mb-1 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              Processing Failed:
            </p>
            <p className="font-mono text-xs bg-red-950/60 p-3 rounded-xl mt-2 border border-red-900/40">{job.error_message || 'Unknown processing error'}</p>
          </div>
        ) : (
          <div className="space-y-6 relative before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800/80">
            {STAGES.map((stg) => {
              const state = getStageState(stg.id);
              const isBlockedByQuota = state === 'active' && job.is_quota_limited;

              return (
                <div key={stg.id} className="flex items-start gap-4 relative z-10">
                  <div className="mt-0.5 bg-slate-950 p-1 rounded-full">
                    {state === 'completed' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                    {state === 'active' && !isBlockedByQuota && <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />}
                    {state === 'active' && isBlockedByQuota && <Clock className="w-6 h-6 text-amber-400 animate-bounce" />}
                    {state === 'pending' && <Circle className="w-6 h-6 text-slate-700" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className={`font-semibold text-base ${
                        state === 'active'
                          ? isBlockedByQuota ? 'text-amber-300' : 'text-indigo-300'
                          : state === 'completed'
                          ? 'text-slate-200'
                          : 'text-slate-500'
                      }`}>
                        {stg.name}
                      </h3>
                      {state === 'active' && !isBlockedByQuota && (
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 animate-pulse">
                          In Progress
                        </span>
                      )}
                      {isBlockedByQuota && (
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-300 animate-pulse">
                          Backed Off
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{stg.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
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

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, Loader2, AlertTriangle, FileVideo, Cpu, ArrowRight } from 'lucide-react';
import { JobStatusResponse, JobStatus } from '../types';
import { api } from '../services/api';

const STAGES: { id: JobStatus; name: string; desc: string }[] = [
  { id: 'PREPROCESSING', name: 'Stage 1: Preprocessing', desc: 'Normalizing video resolution & audio extraction.' },
  { id: 'TRANSCRIBING', name: 'Stage 2: Transcribing', desc: 'Processing audio track & extracting word timestamps.' },
  { id: 'ANALYZING', name: 'Stage 3: AI Analysis', desc: 'Multimodal AI checklist audit & technical inspection.' },
  { id: 'DONE', name: 'Stage 4 & 5: Validation & Finalize', desc: 'Validating issue telemetry & generating scorecards.' },
];

export const JobStatusPage: React.FC = () => {
  const { job_id } = useParams<{ job_id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job_id) return;

    const fetchStatus = async () => {
      try {
        const data = await api.getJobStatus(job_id);
        setJob(data);

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
        <p className="text-slate-400">Connecting to job worker engine...</p>
      </div>
    );
  }

  const getStageState = (stageId: JobStatus) => {
    const order: JobStatus[] = ['QUEUED', 'PREPROCESSING', 'TRANSCRIBING', 'ANALYZING', 'DONE'];
    const currentIndex = order.indexOf(job.status);
    const stageIndex = order.indexOf(stageId);

    if (job.status === 'FAILED') return 'failed';
    if (job.status === 'DONE') return 'completed';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="glass-panel p-8 rounded-3xl border border-slate-800 mb-8">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-6 mb-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-indigo-400 font-mono font-bold">Job Status Monitor</span>
            <h1 className="text-2xl font-bold text-white mt-1 flex items-center gap-3">
              <FileVideo className="w-6 h-6 text-slate-400" />
              {job.original_filename}
            </h1>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Model Engine</span>
            <span className="font-mono text-sm font-semibold text-slate-200">{job.model_used}</span>
          </div>
        </div>

        {job.status === 'FAILED' ? (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm">
            <p className="font-bold mb-1">Processing Failed:</p>
            <p className="font-mono">{job.error_message || 'Unknown processing error'}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {STAGES.map((stg) => {
              const state = getStageState(stg.id);
              return (
                <div key={stg.id} className="flex items-start gap-4">
                  <div className="mt-1">
                    {state === 'completed' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                    {state === 'active' && <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />}
                    {state === 'pending' && <Circle className="w-6 h-6 text-slate-700" />}
                  </div>
                  <div className="flex-1">
                    <h3 className={`font-semibold text-base ${state === 'active' ? 'text-indigo-300' : state === 'completed' ? 'text-slate-200' : 'text-slate-500'}`}>
                      {stg.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">{stg.desc}</p>
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

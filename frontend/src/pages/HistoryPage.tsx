import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, FileText, Trash2, ShieldCheck, ShieldAlert, Clock, ArrowUpRight } from 'lucide-react';
import { JobListItem } from '../types';
import { api } from '../services/api';
import { ErrorBanner } from '../components/ui/ErrorBanner';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to load job history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleDelete = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this job and its associated data?')) return;

    setDeletingId(jobId);
    try {
      await api.deleteJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
    } catch (err: any) {
      alert(`Delete failed: ${err.detail || err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DONE':
        return <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-semibold inline-flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> DONE</span>;
      case 'FAILED':
        return <span className="bg-red-500/20 text-red-300 border border-red-500/30 text-xs px-2.5 py-1 rounded-full font-semibold inline-flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> FAILED</span>;
      default:
        return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs px-2.5 py-1 rounded-full font-mono animate-pulse inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {status}</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-slate-800">
        <div>
          <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
            <History className="w-8 h-8 text-indigo-400" />
            <span>Analysis Jobs History</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">Review past video quality audits, scores, and cost metrics.</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 text-white text-sm font-semibold shadow-lg shadow-indigo-600/20 transition-all self-start sm:self-auto"
        >
          + New Analysis
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchJobs} />}

      {loading ? (
        <div className="glass-panel rounded-3xl border border-slate-800 p-6 space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-slate-900/60 animate-pulse" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="glass-panel p-16 rounded-3xl border border-slate-800 text-center space-y-4">
          <FileText className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-200">No Analysis History Found</h3>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            You haven't run any video quality checks yet. Head over to the Upload Studio to submit your first video.
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all"
          >
            Go to Upload Studio
          </button>
        </div>
      ) : (
        <div className="glass-panel rounded-3xl border border-slate-800 overflow-hidden">
          {/* Desktop Table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-xs uppercase font-mono text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4">Filename</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Model Engine</th>
                  <th className="px-6 py-4">Overall Score</th>
                  <th className="px-6 py-4">Cost (USD)</th>
                  <th className="px-6 py-4">Submitted</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => navigate(job.status === 'DONE' ? `/jobs/${job.id}/report` : `/jobs/${job.id}`)}
                    className="hover:bg-slate-900/50 cursor-pointer transition-colors group"
                  >
                    <td className="px-6 py-4 font-medium text-white max-w-xs truncate">
                      {job.original_filename}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(job.status)}</td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">{job.model_used}</td>
                    <td className="px-6 py-4 font-mono font-bold">
                      {job.overall_score !== undefined && job.overall_score !== null ? (
                        <span className={job.overall_score >= 7.0 ? 'text-emerald-400' : 'text-red-400'}>
                          {job.overall_score.toFixed(1)} / 10
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-emerald-400">${(job.cost_usd || 0).toFixed(4)}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(job.submitted_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => navigate(job.status === 'DONE' ? `/jobs/${job.id}/report` : `/jobs/${job.id}`)}
                          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="Open details"
                        >
                          <ArrowUpRight className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, job.id)}
                          disabled={deletingId === job.id}
                          className="p-2 rounded-lg bg-slate-800 hover:bg-red-950/60 text-slate-400 hover:text-red-300 transition-colors"
                          title="Delete job"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List */}
          <div className="md:hidden divide-y divide-slate-800/60">
            {jobs.map((job) => (
              <div
                key={job.id}
                onClick={() => navigate(job.status === 'DONE' ? `/jobs/${job.id}/report` : `/jobs/${job.id}`)}
                className="p-5 space-y-3 hover:bg-slate-900/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-white truncate text-base">{job.original_filename}</h3>
                  {getStatusBadge(job.status)}
                </div>
                <div className="flex items-center justify-between text-xs font-mono text-slate-400 pt-1">
                  <span>Model: {job.model_used}</span>
                  <span className="text-emerald-400 font-bold">${(job.cost_usd || 0).toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                  <span>Score: {job.overall_score ? `${job.overall_score.toFixed(1)}/10` : 'N/A'}</span>
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDelete(e, job.id)}
                      disabled={deletingId === job.id}
                      className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-red-300"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

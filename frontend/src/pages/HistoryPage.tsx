import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { History, FileVideo, Trash2, ExternalLink, RefreshCw } from 'lucide-react';
import { JobListItem } from '../types';
import { api } from '../services/api';

export const HistoryPage: React.FC = () => {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (!window.confirm('Are you sure you want to delete this analysis job and purging related files?')) return;
    try {
      await api.deleteJob(id);
      setJobs(jobs.filter(j => j.id !== id));
    } catch (err) {
      alert('Failed to delete job');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
            <History className="w-8 h-8 text-indigo-400" /> Jobs Audit History
          </h1>
          <p className="text-slate-400 text-sm mt-1">Review previously audited videos, execution telemetry, and executive reports.</p>
        </div>
        <button
          onClick={loadJobs}
          className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-colors"
          title="Refresh table"
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/90 text-xs font-mono uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4">Filename</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Model</th>
                <th className="px-6 py-4">Duration</th>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Cost (USD)</th>
                <th className="px-6 py-4">Submitted At</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    No video audit jobs recorded yet. Upload a video in the Studio to start.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-100 flex items-center gap-2">
                      <FileVideo className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span className="truncate max-w-xs">{job.original_filename}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-[11px] font-mono font-bold px-2.5 py-1 rounded-full ${
                        job.status === 'DONE' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                        job.status === 'FAILED' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                        'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 animate-pulse'
                      }`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">{job.model_used}</td>
                    <td className="px-6 py-4 font-mono text-xs">{job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : '-'}</td>
                    <td className="px-6 py-4 font-mono font-bold text-indigo-400">
                      {job.overall_score !== null && job.overall_score !== undefined ? `${job.overall_score.toFixed(1)}/10` : '-'}
                    </td>
                    <td className="px-6 py-4 font-mono text-emerald-400">${job.cost_usd.toFixed(4)}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(job.submitted_at).toLocaleString()}</td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Link
                        to={job.status === 'DONE' ? `/jobs/${job.id}/report` : `/jobs/${job.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 px-3 py-1.5 rounded-lg border border-indigo-500/30 transition-colors"
                      >
                        <span>{job.status === 'DONE' ? 'Report' : 'Status'}</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                      <button
                        onClick={(e) => handleDelete(job.id, e)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-950/30 transition-colors"
                        title="Delete job"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

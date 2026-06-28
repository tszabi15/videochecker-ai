import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ShieldCheck, ShieldAlert, Download, Filter, CheckCircle, AlertOctagon,
  AlertTriangle, Info, Volume2, FileText, DollarSign,
} from 'lucide-react';
import { IssueReport, IssueItem, SeverityType, JobStatusResponse } from '../types';
import { api } from '../services/api';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { ScoreCard } from '../components/ui/ScoreCard';

export const ReportPage: React.FC = () => {
  const { job_id } = useParams<{ job_id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<IssueReport | null>(null);
  const [markdownReport, setMarkdownReport] = useState<string>('');
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [whisperOnly, setWhisperOnly] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    if (!job_id) return;
    setLoading(true);
    setError(null);
    try {
      const [repData, jobData] = await Promise.all([
        api.getJobReport(job_id),
        api.getJobStatus(job_id),
      ]);
      setReport(repData.json_report);
      setMarkdownReport(repData.markdown_report);
      setJob(jobData);
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  }, [job_id]);

  useEffect(() => { loadData(); }, [loadData]);

  const filteredIssues = useMemo(() => {
    if (!report) return [];
    return report.issues.filter(issue => {
      if (severityFilter !== 'ALL' && issue.severity !== severityFilter) return false;
      if (categoryFilter !== 'ALL' && issue.category !== categoryFilter) return false;
      if (whisperOnly && !issue.whisper_confirmed) return false;
      return true;
    });
  }, [report, severityFilter, categoryFilter, whisperOnly]);

  const categories = useMemo(() => {
    if (!report) return [];
    return Array.from(new Set(report.issues.map(i => i.category)));
  }, [report]);

  const downloadFile = useCallback((content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    // Revoke to prevent memory leak
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, []);

  const downloadJSON = () => {
    if (report) downloadFile(JSON.stringify(report, null, 2), `report_${job_id}.json`, 'application/json');
  };

  const downloadMarkdown = () => {
    if (markdownReport) downloadFile(markdownReport, `report_${job_id}.md`, 'text/markdown');
  };

  if (error) {
    return (
      <div className="max-w-xl mx-auto my-20 px-4 space-y-4 animate-fade-in">
        <ErrorBanner message={error} onRetry={loadData} />
        <div className="text-center">
          <button onClick={() => navigate('/jobs')} className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium">
            Back to Jobs History
          </button>
        </div>
      </div>
    );
  }

  if (loading || !report || !job) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center animate-fade-in">
        <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400">Loading analysis report dashboard...</p>
      </div>
    );
  }

  const { summary } = report;

  const getSeverityBadge = (sev: SeverityType) => {
    switch (sev) {
      case 'CRITICAL':
        return <span className="bg-red-500/20 text-red-300 border border-red-500/30 text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1.5"><AlertOctagon className="w-3.5 h-3.5" /> CRITICAL</span>;
      case 'MAJOR':
        return <span className="bg-orange-500/20 text-orange-300 border border-orange-500/30 text-xs px-2.5 py-1 rounded-full font-semibold flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> MAJOR</span>;
      case 'MINOR':
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full flex items-center gap-1.5"><Info className="w-3.5 h-3.5" /> MINOR</span>;
      default:
        return <span className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs px-2.5 py-1 rounded-full">INFO</span>;
    }
  };

  const CATEGORY_LABELS: Record<string, string> = {
    TECHNICAL_ERROR: 'Technical Error',
    CONTENT_ERROR: 'Content & Delivery Error',
    AUDIO_VISUAL_ERROR: 'Audio/Visual Error',
    GENERAL_OBSERVATION: 'General Observation',
  };

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'TECHNICAL_ERROR':
        return <span className="bg-red-500/20 text-red-300 border border-red-500/30 text-xs px-2.5 py-1 rounded-lg font-semibold">Technical Error</span>;
      case 'CONTENT_ERROR':
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs px-2.5 py-1 rounded-lg font-semibold">Content & Delivery Error</span>;
      case 'AUDIO_VISUAL_ERROR':
        return <span className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs px-2.5 py-1 rounded-lg font-semibold">Audio/Visual Error</span>;
      case 'GENERAL_OBSERVATION':
      default:
        return <span className="bg-slate-700/40 text-slate-300 border border-slate-600/30 text-xs px-2.5 py-1 rounded-lg font-semibold">General Observation</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 space-y-8 animate-fade-in">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono text-indigo-400 font-bold uppercase tracking-wider">Audit Dashboard</span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs font-mono text-slate-400 truncate max-w-[200px] sm:max-w-none">{job.original_filename}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Quality Analysis Executive Report</h1>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <button onClick={downloadJSON} className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-colors">
            <Download className="w-4 h-4 text-indigo-400" /> JSON
          </button>
          <button onClick={downloadMarkdown} className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-colors">
            <FileText className="w-4 h-4" /> Markdown
          </button>
        </div>
      </div>

      {/* Scorecard Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <ScoreCard label="Overall Score" value={summary.overall_score} sublabel="Out of 10.0" colorClass="text-indigo-400" large />
        <ScoreCard label="Audit Status" sublabel="Benchmark Check" value="">
          {summary.passed ? (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold text-sm">
              <ShieldCheck className="w-4 h-4" /> PASSED
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/30 font-bold text-sm">
              <ShieldAlert className="w-4 h-4" /> FAILED
            </div>
          )}
        </ScoreCard>
        <ScoreCard label="Audio Score" value={summary.audio_quality_score} sublabel="Voice & Noise" colorClass="text-cyan-400" />
        <ScoreCard label="Visual Score" value={summary.visual_quality_score} sublabel="Screen & Clarity" colorClass="text-purple-400" />
        <ScoreCard label="Coherence" value={summary.content_coherence_score} sublabel="Structure & Flow" colorClass="text-pink-400" />
        <ScoreCard label="Tech Accuracy" value={summary.technical_accuracy_score} sublabel="Code & Commands" colorClass="text-amber-400" />
      </div>

      {/* Main Grid: Issues + Side Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Issues Column */}
        <div className="lg:col-span-3 space-y-6">
          {/* Filters */}
          <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold text-slate-200">Filter Issues</span>
              <span className="text-xs font-mono text-slate-500">({filteredIssues.length}/{report.issues.length})</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none">
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical Only</option>
                <option value="MAJOR">Major Only</option>
                <option value="MINOR">Minor Only</option>
                <option value="INFO">Info Only</option>
              </select>
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none">
                <option value="ALL">All Categories</option>
                {categories.map(c => (<option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>))}
              </select>
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input type="checkbox" checked={whisperOnly} onChange={(e) => setWhisperOnly(e.target.checked)} className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0" />
                <span>Audio Verified</span>
              </label>
            </div>
          </div>

          {/* Issue Cards */}
          {filteredIssues.length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center text-slate-400">
              <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
              <p className="font-semibold text-slate-200">No issues matching active filters.</p>
            </div>
          ) : (
            filteredIssues.map((issue) => (
              <div key={issue.id} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 hover:border-slate-700 transition-all">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                      {issue.timestamp_start}s - {issue.timestamp_end}s
                    </span>
                    {getSeverityBadge(issue.severity)}
                    {getCategoryBadge(issue.category)}
                  </div>
                  <div className="flex items-center gap-3">
                    {issue.whisper_confirmed && (
                      <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                        <Volume2 className="w-3 h-3" /> Audio Verified
                      </span>
                    )}
                    <div className="text-right">
                      <span className="text-[10px] text-slate-500 block">Confidence</span>
                      <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden mt-1">
                        <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${issue.confidence * 100}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100 mb-1">{issue.title}</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">{issue.description}</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-2 font-mono">
                  <div>
                    <span className="text-indigo-400 font-bold uppercase tracking-wider block mb-0.5">Observed Evidence</span>
                    <span className="text-slate-300 italic">"{issue.evidence}"</span>
                  </div>
                  <div className="pt-2 border-t border-slate-900">
                    <span className="text-emerald-400 font-bold uppercase tracking-wider block mb-0.5">Recommendation</span>
                    <span className="text-slate-300 font-sans">{issue.suggestion}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Cost Side Panel */}
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <DollarSign className="w-5 h-5 text-emerald-400" /> Cost & Resource Telemetry
            </h3>
            <div className="space-y-4 text-xs font-mono">
              <div className="flex justify-between items-center py-2 border-b border-slate-900">
                <span className="text-slate-400">Actual USD Cost</span>
                <span className="text-base font-bold text-emerald-400">${(job.actual_cost_usd || report.cost_usd).toFixed(4)}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-900">
                <span className="text-slate-400">Model Engine</span>
                <span className="text-slate-200">{report.processing_model}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-900">
                <span className="text-slate-400">Execution Mode</span>
                <span className="text-slate-200 uppercase">{job.mode}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-900">
                <span className="text-slate-400">Video Duration</span>
                <span className="text-slate-200">{report.video_duration_seconds.toFixed(1)}s</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-slate-400">Long Context Tier</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">Standard (&lt;200k)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

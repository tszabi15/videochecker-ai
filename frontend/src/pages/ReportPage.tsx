import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ShieldCheck, ShieldAlert, Download, Filter, CheckCircle, AlertOctagon, 
  AlertTriangle, Info, Volume2, Video, FileText, Cpu, DollarSign, ExternalLink 
} from 'lucide-react';
import { IssueReport, IssueItem, SeverityType, JobStatusResponse } from '../types';
import { api } from '../services/api';

export const ReportPage: React.FC = () => {
  const { job_id } = useParams<{ job_id: string }>();
  const [report, setReport] = useState<IssueReport | null>(null);
  const [markdownReport, setMarkdownReport] = useState<string>('');
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [whisperOnly, setWhisperOnly] = useState<boolean>(false);

  useEffect(() => {
    if (!job_id) return;
    const loadData = async () => {
      try {
        const [repData, jobData] = await Promise.all([
          api.getJobReport(job_id),
          api.getJobStatus(job_id)
        ]);
        setReport(repData.json_report);
        setMarkdownReport(repData.markdown_report);
        setJob(jobData);
      } catch (err) {
        console.error('Failed to load report:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [job_id]);

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

  const downloadJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${job_id}.json`;
    a.click();
  };

  const downloadMarkdown = () => {
    if (!markdownReport) return;
    const blob = new Blob([markdownReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${job_id}.md`;
    a.click();
  };

  if (loading || !report || !job) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
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
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full text-xs flex items-center gap-1.5"><Info className="w-3.5 h-3.5" /> MINOR</span>;
      default:
        return <span className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs px-2.5 py-1 rounded-full text-xs">INFO</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 space-y-8">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono text-indigo-400 font-bold uppercase tracking-wider">Audit Dashboard</span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs font-mono text-slate-400">{job.original_filename}</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white">Quality Analysis Executive Report</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={downloadJSON}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <Download className="w-4 h-4 text-indigo-400" /> JSON Report
          </button>
          <button
            onClick={downloadMarkdown}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-colors"
          >
            <FileText className="w-4 h-4" /> Markdown Report
          </button>
        </div>
      </div>

      {/* 6 Scorecard Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Overall Score */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Overall Score</span>
          <div className="text-4xl font-extrabold font-mono text-indigo-400 my-2">{summary.overall_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Out of 10.0</span>
        </div>

        {/* Quality Status Badge */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Audit Status</span>
          <div className="my-2 flex justify-center">
            {summary.passed ? (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold text-sm">
                <ShieldCheck className="w-4 h-4" /> PASSED
              </div>
            ) : (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/30 font-bold text-sm">
                <ShieldAlert className="w-4 h-4" /> FAILED
              </div>
            )}
          </div>
          <span className="text-[10px] text-slate-500">Benchmark Check</span>
        </div>

        {/* Audio Quality */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Audio Score</span>
          <div className="text-3xl font-bold font-mono text-cyan-400 my-2">{summary.audio_quality_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Voice & Noise</span>
        </div>

        {/* Visual Quality */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Visual Score</span>
          <div className="text-3xl font-bold font-mono text-purple-400 my-2">{summary.visual_quality_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Screen & Clarity</span>
        </div>

        {/* Content Coherence */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Coherence</span>
          <div className="text-3xl font-bold font-mono text-pink-400 my-2">{summary.content_coherence_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Structure & Flow</span>
        </div>

        {/* Technical Accuracy */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 text-center flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase">Tech Accuracy</span>
          <div className="text-3xl font-bold font-mono text-amber-400 my-2">{summary.technical_accuracy_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Code & Commands</span>
        </div>
      </div>

      {/* Main Grid: Issues List + Cost Breakdown Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Issues List Column (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Filters Bar */}
          <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold text-slate-200">Filter Issues</span>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Severity Filter */}
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical Only</option>
                <option value="MAJOR">Major Only</option>
                <option value="MINOR">Minor Only</option>
                <option value="INFO">Info Only</option>
              </select>

              {/* Category Filter */}
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none"
              >
                <option value="ALL">All Categories</option>
                {categories.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>

              {/* Whisper Confirmed Toggle */}
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={whisperOnly}
                  onChange={(e) => setWhisperOnly(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                />
                <span>Whisper Confirmed</span>
              </label>
            </div>
          </div>

          {/* Issues Cards */}
          {filteredIssues.length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center text-slate-400">
              <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
              <p className="font-semibold text-slate-200">No issues matching active filters.</p>
            </div>
          ) : (
            filteredIssues.map((issue) => (
              <div key={issue.id} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 hover:border-slate-700 transition-all">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                      {issue.timestamp_start}s - {issue.timestamp_end}s
                    </span>
                    {getSeverityBadge(issue.severity)}
                    <span className="text-xs font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800">
                      {issue.category}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    {issue.whisper_confirmed && (
                      <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                        <Volume2 className="w-3 h-3" /> Whisper Confirmed
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

        {/* Cost Breakdown Side Panel (1 col) */}
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              Cost & Resource Telemetry
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
                <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                  Standard (&lt;200k)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

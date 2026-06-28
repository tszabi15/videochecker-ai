/**
 * Frontend TypeScript type definitions for VideoChecker AI.
 */

export type ModelType = 'gemini-3.1-pro' | 'gemini-3.5-flash' | 'gemini-2.5-flash';
export type ModeType = 'realtime' | 'batch';
export type JobStatus = 'QUEUED' | 'PREPROCESSING' | 'TRANSCRIBING' | 'ANALYZING' | 'VALIDATING' | 'FINALIZING' | 'DONE' | 'FAILED';
export type SeverityType = 'CRITICAL' | 'MAJOR' | 'MINOR' | 'INFO';
export type CategoryType = 'TECHNICAL_ERROR' | 'CONTENT_ERROR' | 'AUDIO_VISUAL_ERROR' | 'GENERAL_OBSERVATION';

export interface IssueItem {
  id: string;
  timestamp_start: number;
  timestamp_end: number;
  category: CategoryType;
  severity: SeverityType;
  title: string;
  description: string;
  evidence: string;
  suggestion: string;
  whisper_confirmed: boolean;
  confidence: number;
}

export interface ReportSummary {
  total_issues: number;
  critical_issues: number;
  major_issues: number;
  minor_issues: number;
  audio_quality_score: number;
  visual_quality_score: number;
  content_coherence_score: number;
  technical_accuracy_score: number;
  overall_score: number;
  passed: boolean;
}

export interface IssueReport {
  video_id: string;
  analysis_timestamp: string;
  video_duration_seconds: number;
  processing_model: string;
  cost_usd: number;
  summary: ReportSummary;
  issues: IssueItem[];
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  original_filename: string;
  model_used: string;
  mode: ModeType;
  video_language?: string;
  report_language?: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  estimated_cost_usd: number;
  actual_cost_usd?: number;
  duration_seconds?: number;
  is_quota_limited?: boolean;
  retry_after_seconds?: number;
}

export interface JobListItem {
  id: string;
  original_filename: string;
  duration_seconds?: number;
  submitted_at: string;
  status: JobStatus;
  model_used: string;
  overall_score?: number;
  cost_usd: number;
}

export interface CostStatsResponse {
  total_jobs: number;
  completed_jobs: number;
  total_spend_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_whisper_minutes: number;
  spend_by_model: Record<string, number>;
}

/** Response from the report endpoint */
export interface ReportResponse {
  json_report: IssueReport;
  markdown_report: string;
}

/** Response from the upload/create job endpoint */
export interface UploadJobResponse {
  job_id: string;
  status: string;
  estimated_cost_usd: number;
}

/** Structured API error for user-facing display */
export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly detail: string;

  constructor(statusCode: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

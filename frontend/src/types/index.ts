export type ModelType = 'gemini-3.1-pro' | 'gemini-3.5-flash' | 'gemini-2.5-flash';
export type ModeType = 'realtime' | 'batch';
export type JobStatus = 'QUEUED' | 'PREPROCESSING' | 'TRANSCRIBING' | 'ANALYZING' | 'DONE' | 'FAILED';
export type SeverityType = 'CRITICAL' | 'MAJOR' | 'MINOR' | 'INFO';

export interface IssueItem {
  id: str;
  timestamp_start: number;
  timestamp_end: number;
  category: string;
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
  created_at: string;
  updated_at: string;
  error_message?: string;
  estimated_cost_usd: number;
  actual_cost_usd?: number;
  duration_seconds?: number;
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

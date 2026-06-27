import { JobListItem, JobStatusResponse, ModelType, ModeType, CostStatsResponse, IssueReport } from '../types';

const API_BASE = '/api/v1';

export const api = {
  async uploadJob(file: File, prompt: string, model: ModelType, mode: ModeType, videoLanguage: string = 'hu', reportLanguage: string = 'hu') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prompt', prompt);
    formData.append('model', model);
    formData.append('mode', mode);
    formData.append('video_language', videoLanguage);
    formData.append('report_language', reportLanguage);

    const res = await fetch(`${API_BASE}/jobs`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Failed to upload video');
    }

    return res.json() as Promise<{ job_id: string; status: string; estimated_cost_usd: number }>;
  },

  async getJobStatus(jobId: string) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to fetch job status');
    return res.json() as Promise<JobStatusResponse>;
  },

  async getJobReport(jobId: string) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/report`);
    if (!res.ok) throw new Error('Report not available');
    return res.json() as Promise<{ json_report: IssueReport; markdown_report: string }>;
  },

  async listJobs() {
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) throw new Error('Failed to fetch jobs history');
    return res.json() as Promise<JobListItem[]>;
  },

  async deleteJob(jobId: string) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete job');
  },

  async getCostStats() {
    const res = await fetch(`${API_BASE}/stats/costs`);
    if (!res.ok) throw new Error('Failed to fetch cost stats');
    return res.json() as Promise<CostStatsResponse>;
  }
};

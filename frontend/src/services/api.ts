/**
 * API service layer for VideoChecker AI.
 *
 * Provides typed fetch wrappers with structured error handling,
 * timeout support, and consistent error extraction.
 */

import {
  JobListItem, JobStatusResponse, ModelType, ModeType,
  CostStatsResponse, ReportResponse, UploadJobResponse, ApiError,
} from '../types';

const API_BASE = '/api/v1';
const DEFAULT_TIMEOUT_MS = 30_000;

/**
 * Shared fetch wrapper with timeout and structured error extraction.
 */
async function fetchApi<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { ...options, signal: controller.signal });

    if (!res.ok) {
      let detail = `Request failed with status ${res.status}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {
        // Response body wasn't JSON — use status text
        detail = res.statusText || detail;
      }
      throw new ApiError(res.status, detail);
    }

    // For 204 No Content responses
    if (res.status === 204) return undefined as unknown as T;

    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, 'Request timed out. Please check your connection and try again.');
    }
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new ApiError(0, 'Network error. Unable to reach the server.');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  async uploadJob(
    file: File, prompt: string, model: ModelType, mode: ModeType,
    videoLanguage: string = 'hu', reportLanguage: string = 'hu',
  ): Promise<UploadJobResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prompt', prompt);
    formData.append('model', model);
    formData.append('mode', mode);
    formData.append('video_language', videoLanguage);
    formData.append('report_language', reportLanguage);

    // Longer timeout for large file uploads
    return fetchApi<UploadJobResponse>(
      `${API_BASE}/jobs`,
      { method: 'POST', body: formData },
      120_000,
    );
  },

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return fetchApi<JobStatusResponse>(`${API_BASE}/jobs/${jobId}`);
  },

  async getJobReport(jobId: string): Promise<ReportResponse> {
    return fetchApi<ReportResponse>(`${API_BASE}/jobs/${jobId}/report`);
  },

  async listJobs(): Promise<JobListItem[]> {
    return fetchApi<JobListItem[]>(`${API_BASE}/jobs`);
  },

  async deleteJob(jobId: string): Promise<void> {
    return fetchApi<void>(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
  },

  async getCostStats(): Promise<CostStatsResponse> {
    return fetchApi<CostStatsResponse>(`${API_BASE}/stats/costs`);
  },
};

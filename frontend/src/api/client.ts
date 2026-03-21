/**
 * API client for communicating with the FastAPI backend.
 *
 * Provides type-safe wrappers around fetch for all API endpoints.
 */

import type { Report, Article, SystemStatus } from '../types/api';

// API base URL - can be overridden via environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors.
 */
export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(
    message: string,
    status: number,
    data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new ApiError(
        errorData?.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network errors or other exceptions
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

/**
 * Get list of all reports.
 *
 * @returns Promise<Report[]>
 * @throws ApiError
 */
export async function getReports(): Promise<Report[]> {
  return fetchApi<Report[]>('/api/reports');
}

/**
 * Get specific report by ID.
 *
 * @param id - Report ID
 * @returns Promise<Report>
 * @throws ApiError
 */
export async function getReport(id: string): Promise<Report> {
  return fetchApi<Report>(`/api/reports/${encodeURIComponent(id)}`);
}

/**
 * Search reports by keyword.
 *
 * @param keyword - Search keyword
 * @returns Promise<Report[]>
 * @throws ApiError
 */
export async function searchReports(keyword: string): Promise<Report[]> {
  const encodedKeyword = encodeURIComponent(keyword);
  return fetchApi<Report[]>(`/api/reports/search?q=${encodedKeyword}`);
}

/**
 * Get list of recent articles.
 *
 * @param limit - Maximum number of articles (default 100)
 * @returns Promise<Article[]>
 * @throws ApiError
 */
export async function getArticles(limit = 100): Promise<Article[]> {
  return fetchApi<Article[]>(`/api/articles?limit=${limit}`);
}

/**
 * Get system status.
 *
 * @returns Promise<SystemStatus>
 * @throws ApiError
 */
export async function getStatus(): Promise<SystemStatus> {
  return fetchApi<SystemStatus>('/api/status');
}

/**
 * Trigger manual collection.
 *
 * @returns Promise<{ status: string }>
 * @throws ApiError
 */
export async function triggerCollection(): Promise<{ status: string }> {
  return fetchApi('/api/collect', { method: 'POST' });
}

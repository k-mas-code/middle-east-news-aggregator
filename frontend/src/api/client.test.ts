/**
 * Tests for API client.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getReports,
  getReport,
  searchReports,
  getArticles,
  getStatus,
  triggerCollection,
  ApiError,
} from './client';
import type { Report, SystemStatus } from '../types/api';

// Mock fetch globally
global.fetch = vi.fn();

describe('API Client', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('getReports', () => {
    it('should fetch reports successfully', async () => {
      const mockReports: Report[] = [
        {
          id: 'report-1',
          cluster: {
            id: 'cluster-1',
            topic_name: 'Test Topic',
            articles: [],
            media_names: ['aljazeera'],
            created_at: '2024-01-15T00:00:00Z',
          },
          comparison: {
            media_bias_scores: {},
            unique_entities_by_media: {},
            common_entities: [],
            bias_diff: 0,
          },
          generated_at: '2024-01-15T00:00:00Z',
          summary: 'Test summary',
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReports,
      });

      const result = await getReports();

      expect(result).toEqual(mockReports);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/reports',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should throw ApiError on HTTP error', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Database error' }),
      });

      await expect(getReports()).rejects.toThrow(ApiError);
      await expect(getReports()).rejects.toThrow('Database error');
    });

    it('should throw ApiError on network error', async () => {
      (global.fetch as any).mockRejectedValue(new Error('Network failed'));

      await expect(getReports()).rejects.toThrow(ApiError);
      await expect(getReports()).rejects.toThrow('Network failed');
    });
  });

  describe('getReport', () => {
    it('should fetch report by ID', async () => {
      const mockReport: Report = {
        id: 'report-123',
        cluster: {
          id: 'cluster-1',
          topic_name: 'Test Topic',
          articles: [],
          media_names: ['aljazeera'],
          created_at: '2024-01-15T00:00:00Z',
        },
        comparison: {
          media_bias_scores: {},
          unique_entities_by_media: {},
          common_entities: [],
          bias_diff: 0,
        },
        generated_at: '2024-01-15T00:00:00Z',
        summary: 'Test summary',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReport,
      });

      const result = await getReport('report-123');

      expect(result).toEqual(mockReport);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/reports/report-123',
        expect.any(Object)
      );
    });

    it('should encode special characters in ID', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await getReport('report/with/slashes');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/reports/report%2Fwith%2Fslashes',
        expect.any(Object)
      );
    });
  });

  describe('searchReports', () => {
    it('should search reports by keyword', async () => {
      const mockReports: Report[] = [];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReports,
      });

      const result = await searchReports('Gaza');

      expect(result).toEqual(mockReports);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/reports/search?q=Gaza',
        expect.any(Object)
      );
    });

    it('should encode special characters in keyword', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await searchReports('Israel & Palestine');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/reports/search?q=Israel%20%26%20Palestine',
        expect.any(Object)
      );
    });
  });

  describe('getArticles', () => {
    it('should fetch articles with default limit', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await getArticles();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/articles?limit=100',
        expect.any(Object)
      );
    });

    it('should fetch articles with custom limit', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await getArticles(50);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/articles?limit=50',
        expect.any(Object)
      );
    });
  });

  describe('getStatus', () => {
    it('should fetch system status', async () => {
      const mockStatus: SystemStatus = {
        status: 'ok',
        last_collection: '2024-01-15T00:00:00Z',
        total_articles: 100,
        total_reports: 20,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      });

      const result = await getStatus();

      expect(result).toEqual(mockStatus);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/status',
        expect.any(Object)
      );
    });
  });

  describe('triggerCollection', () => {
    it('should trigger manual collection', async () => {
      const mockResponse = { status: 'success' };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await triggerCollection();

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/collect',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('ApiError', () => {
    it('should create ApiError with status and message', () => {
      const error = new ApiError('Not found', 404);

      expect(error.name).toBe('ApiError');
      expect(error.message).toBe('Not found');
      expect(error.status).toBe(404);
    });

    it('should create ApiError with additional data', () => {
      const error = new ApiError('Validation error', 422, {
        field: 'email',
      });

      expect(error.data).toEqual({ field: 'email' });
    });
  });
});

// Checked AGENTS.md - Test suite for API client
// Tests network handling, error cases, and data formatting
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api } from '../api';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('DiagnosticAPI', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('healthCheck', () => {
    it('should return health status on success', async () => {
      const mockResponse = { status: 'online', message: 'Server running' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.healthCheck();
      expect(result).toEqual(mockResponse);
    });

    it('should throw error when backend is offline', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(api.healthCheck()).rejects.toThrow('Backend offline');
    });

    it('should throw error on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.healthCheck()).rejects.toThrow('Network error');
    });
  });

  describe('searchComplaints', () => {
    it('should return search results with valid query', async () => {
      const mockResponse = {
        query: 'transmission',
        sanitized_query: 'transmission',
        results: [
          { make: 'FORD', model: 'F-150', year: 2018, component: 'Transmission', summary: 'Shudder issue' }
        ],
        source: 'NHTSA'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.searchComplaints('transmission', 20);
      expect(result.results).toHaveLength(1);
      expect(result.results[0].make).toBe('FORD');
    });

    it('should handle empty results', async () => {
      const mockResponse = {
        query: 'nonexistent',
        sanitized_query: 'nonexistent',
        results: [],
        source: 'NHTSA'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.searchComplaints('nonexistent');
      expect(result.results).toHaveLength(0);
    });

    it('should throw error on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Server error'),
      });

      await expect(api.searchComplaints('test')).rejects.toThrow('API Error (500)');
    });
  });

  describe('searchTSBs', () => {
    it('should return TSB results with valid query', async () => {
      const mockResponse = {
        query: 'airbag',
        sanitized_query: 'airbag',
        results: [
          { nhtsa_id: 'TSB123', make: 'FORD', model: 'F-150', year: 2018, component: 'Airbag', summary: 'Recall' }
        ],
        source: 'TSB'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.searchTSBs('airbag');
      expect(result.results).toHaveLength(1);
      expect(result.results[0].nhtsa_id).toBe('TSB123');
    });
  });

  describe('formatResults', () => {
    it('should format results with data', () => {
      const response = {
        query: 'test',
        sanitized_query: 'test',
        results: [
          { make: 'FORD', model: 'F-150', year: 2018, component: 'Engine', summary: 'Test issue' }
        ],
        source: 'NHTSA'
      };

      const formatted = api.formatResults(response);
      expect(formatted).toContain('[SEARCH COMPLETE]');
      expect(formatted).toContain('FORD');
      expect(formatted).toContain('F-150');
      expect(formatted).toContain('Engine');
    });

    it('should format empty results', () => {
      const response = {
        query: 'empty',
        sanitized_query: 'empty',
        results: [],
        source: 'NHTSA'
      };

      const formatted = api.formatResults(response);
      expect(formatted).toContain('No matches found');
    });
  });

  describe('formatError', () => {
    it('should format error messages', () => {
      const error = new Error('Connection failed');
      const formatted = api.formatError(error);
      expect(formatted).toContain('SYSTEM ERROR');
      expect(formatted).toContain('Connection failed');
      expect(formatted).toContain('Troubleshooting');
    });
  });

  describe('diagnose', () => {
    const mockRequest = {
      vehicle: { make: 'FORD', model: 'F-150', year: 2018 },
      symptoms: 'Engine knocking',
      dtc_codes: ['P0301'],
    };
    const mockDiagnoseResponse = {
      vehicle: { make: 'FORD', model: 'F-150', year: 2018 },
      symptoms: 'Engine knocking',
      dtc_codes: ['P0301'],
      candidates: [
        {
          component: 'Engine', complaint_count: 10, confidence: 0.85, confidence_sufficient: true,
          safety_alert: null, trend: 'Increasing', tsbs: [], samples: [],
        },
      ],
      warnings: [],
      data_sources: {},
    };

    it('should return DiagnoseResponse on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDiagnoseResponse),
      });

      const result = await api.diagnose(mockRequest);
      expect(result).toEqual(mockDiagnoseResponse);
    });

    it('should POST to /api/diagnose with correct body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDiagnoseResponse),
      });

      await api.diagnose(mockRequest);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/diagnose'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(mockRequest),
        })
      );
    });

    it('should work without dtc_codes (optional field)', async () => {
      const requestNoDtc = {
        vehicle: { make: 'FORD', model: 'F-150', year: 2018 },
        symptoms: 'Brakes squealing',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ ...mockDiagnoseResponse, dtc_codes: [] }),
      });

      const result = await api.diagnose(requestNoDtc);
      expect(result.dtc_codes).toEqual([]);
    });

    it('should throw on API error 500', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Server error'),
      });

      await expect(api.diagnose(mockRequest)).rejects.toThrow('API Error (500)');
    });

    it('should propagate network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.diagnose(mockRequest)).rejects.toThrow('Network error');
    });
  });

  describe('formatDiagnosis', () => {
    const baseVehicle = { make: 'FORD', model: 'F-150', year: 2018 };
    const baseSymptoms = 'Engine shaking at idle';

    const makeCandidate = (overrides = {}) => ({
      component: 'Engine',
      complaint_count: 10,
      confidence: 0.80,
      confidence_sufficient: true,
      safety_alert: null,
      trend: 'Stable',
      tsbs: [],
      samples: [],
      ...overrides,
    });

    it('should show no-candidates message when candidates is empty', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [], warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('[DIAGNOSIS COMPLETE]');
      expect(out).toContain('No diagnostic candidates found');
      expect(out).not.toContain('Candidates Found:');
    });

    it('should format candidate header and confidence when confidence_sufficient=true', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate({ component: 'Fuel Injector', confidence: 0.90, confidence_sufficient: true })],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('Candidates Found: 1');
      expect(out).toContain('━━━ #1: FUEL INJECTOR ━━━');
      expect(out).toContain('Confidence: ✓');
      expect(out).toContain('90%');
    });

    it('should show ⚠ status symbol when confidence_sufficient=false', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate({ confidence: 0.45, confidence_sufficient: false })],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('Confidence: ⚠');
      expect(out).toContain('45%');
    });

    it('should show 🚨 for CRITICAL safety_alert', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate({
          component: 'Brake System',
          safety_alert: { level: 'CRITICAL', component: 'Brake System', message: 'Brake failure imminent' },
        })],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('🚨 SAFETY CRITICAL: Brake failure imminent');
    });

    it('should show ⚠️ for HIGH safety_alert', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate({
          safety_alert: { level: 'HIGH', component: 'Steering', message: 'Steering assist reduced' },
        })],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('⚠️ SAFETY HIGH: Steering assist reduced');
    });

    it('should include WARNINGS section when warnings array is non-empty', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate()],
        warnings: ['Confidence below threshold', 'Limited data'],
        data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('⚠️  WARNINGS:');
      expect(out).toContain('Confidence below threshold');
      expect(out).toContain('Limited data');
    });

    it('should show TSBs count when tsbs is non-empty', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [makeCandidate({ tsbs: [{}, {}] })],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('TSBs: 2 relevant bulletin(s) found');
    });

    it('should index multiple candidates correctly', () => {
      const response = {
        vehicle: baseVehicle, symptoms: baseSymptoms, dtc_codes: [],
        candidates: [
          makeCandidate({ component: 'Battery' }),
          makeCandidate({ component: 'Alternator' }),
        ],
        warnings: [], data_sources: {},
      };
      const out = api.formatDiagnosis(response);
      expect(out).toContain('Candidates Found: 2');
      expect(out).toContain('━━━ #1: BATTERY ━━━');
      expect(out).toContain('━━━ #2: ALTERNATOR ━━━');
    });
  });
});

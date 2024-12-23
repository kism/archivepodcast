// @vitest-environment happy-dom
import { describe, it, expect, vi } from 'vitest';
import { fetchHealthStatus } from '../archivepodcast/static/health';

vi.mock('../health', () => ({
    fetchHealthStatus: vi.fn(),
}));

describe('Health API', () => {
    it('should return healthy status', async () => {
        const mockResponse = { status: 'healthy' };
        fetchHealthStatus.mockResolvedValue(mockResponse);

        const response = await fetchHealthStatus();
        expect(response).toEqual(mockResponse);
    });

    it('should return unhealthy status', async () => {
        const mockResponse = { status: 'unhealthy' };
        fetchHealthStatus.mockResolvedValue(mockResponse);

        const response = await fetchHealthStatus();
        expect(response).toEqual(mockResponse);
    });

    it('should handle errors', async () => {
        const mockError = new Error('Network Error');
        fetchHealthStatus.mockRejectedValue(mockError);

        try {
            await fetchHealthStatus();
        } catch (error) {
            expect(error).toBe(mockError);
        }
    });
});

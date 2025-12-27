import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export const apiClient = {
  // Drift monitoring
  getDriftReport: async (hours = 1) => {
    const response = await api.get(`/api/v1/monitoring/drift/latest?hours=${hours}`);
    return response.data;
  },

  // Metrics
  getMetricsTimeseries: async (start, end, interval = '1h') => {
    const params = new URLSearchParams();
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    params.append('interval', interval);
    
    const response = await api.get(`/api/v1/monitoring/metrics/timeseries?${params}`);
    return response.data;
  },

  // Model info
  getModelInfo: async () => {
    const response = await api.get('/api/v1/model/info');
    return response.data;
  },

  // Health check
  getHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;


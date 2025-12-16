import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_URL = `${BACKEND_URL}/api`;

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  signup: (data) => api.post('/auth/signup', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return api.post('/auth/logout');
  },
};

// Upload API
export const uploadAPI = {
  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Creator API
export const creatorAPI = {
  createProfile: (data) => api.post('/creator/profile', data),
  getProfile: () => api.get('/creator/profile'),
  getRequests: () => api.get('/creator/requests'),
};

// Business API
export const businessAPI = {
  createProfile: (data) => api.post('/business/profile', data),
  getProfile: () => api.get('/business/profile'),
};

// Marketplace API
export const marketplaceAPI = {
  getCreators: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.niche) params.append('niche', filters.niche);
    if (filters.minFollowers) params.append('minFollowers', filters.minFollowers);
    if (filters.maxFollowers) params.append('maxFollowers', filters.maxFollowers);
    if (filters.location) params.append('location', filters.location);
    if (filters.openToBarter !== undefined) params.append('openToBarter', filters.openToBarter);
    return api.get(`/creators?${params.toString()}`);
  },
  getCreatorById: (id) => api.get(`/creators/${id}`),
  getBusinessById: (id) => api.get(`/businesses/${id}`),
};

// Requests API
export const requestsAPI = {
  create: (data) => api.post('/requests/', data),
  getSent: () => api.get('/requests/sent'),
  getById: (id) => api.get(`/requests/${id}`),
  updateStatus: (id, status) => api.patch(`/requests/${id}/status?status=${status}`),
};

// Messages API
export const messagesAPI = {
  getMessages: (requestId) => api.get(`/messages/${requestId}`),
  sendMessage: (requestId, text) => api.post(`/messages/${requestId}`, { text }),
};

// Seed API
export const seedAPI = {
  seed: () => api.post('/seed'),
};

export default api;

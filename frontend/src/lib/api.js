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
  getUnlockCredits: () => api.get('/business/unlock-credits'),
};

// Marketplace API (Gated)
export const marketplaceAPI = {
  // Layer 1: Discovery (Free)
  discoverCreators: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.niche) params.append('niche', filters.niche);
    if (filters.minFollowers) params.append('minFollowers', filters.minFollowers);
    if (filters.maxFollowers) params.append('maxFollowers', filters.maxFollowers);
    if (filters.location) params.append('location', filters.location);
    if (filters.openToBarter !== undefined) params.append('openToBarter', filters.openToBarter);
    return api.get(`/creators/discover?${params.toString()}`);
  },
  
  // Layer 2: Unlocked (After ₹200)
  getUnlockedCreator: (id) => api.get(`/creators/${id}/unlocked`),
  
  // Layer 3: Full Access (After Escrow)
  getFullCreator: (id) => api.get(`/creators/${id}/full`),
  
  // Unlock a creator
  unlockCreator: (id) => api.post(`/creators/${id}/unlock`),
  
  // Legacy (redirects to discover)
  getCreators: (filters = {}) => marketplaceAPI.discoverCreators(filters),
  getCreatorById: (id) => api.get(`/creators/${id}/unlocked`),
  getBusinessById: (id) => api.get(`/businesses/${id}`),
};

// Campaigns API (Replaces Requests)
export const campaignsAPI = {
  create: (data) => api.post('/campaigns', data),
  getSent: () => api.get('/campaigns/sent'),
  getById: (id) => api.get(`/campaigns/${id}`),
  updateStatus: (id, status) => api.patch(`/campaigns/${id}/status?status=${status}`),
};

// Legacy Requests API (for compatibility)
export const requestsAPI = {
  create: (data) => campaignsAPI.create(data),
  getSent: () => campaignsAPI.getSent(),
  getById: (id) => campaignsAPI.getById(id),
  updateStatus: (id, status) => campaignsAPI.updateStatus(id, status),
};

// Messages API
export const messagesAPI = {
  getMessages: (campaignId) => api.get(`/messages/${campaignId}`),
  sendMessage: (campaignId, text) => api.post(`/messages/${campaignId}`, { text }),
};

// Payments API
export const paymentsAPI = {
  createUnlockOrder: () => api.post('/payments/create-unlock-order'),
  verifyUnlockPayment: (data) => api.post('/payments/verify-unlock-payment', data),
  createEscrowOrder: (campaignId) => api.post(`/payments/create-escrow-order?campaign_id=${campaignId}`),
  verifyEscrowPayment: (campaignId, data) => api.post(`/payments/verify-escrow-payment?campaign_id=${campaignId}`, data),
};

// Admin API
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getBypassAttempts: () => api.get('/admin/bypass-attempts'),
  banUser: (userId) => api.post(`/admin/users/${userId}/ban`),
  unbanUser: (userId) => api.post(`/admin/users/${userId}/unban`),
  revokeCredits: (brandId) => api.delete(`/admin/unlock-credits/${brandId}`),
};

// Seed API
export const seedAPI = {
  seed: () => api.post('/seed'),
};

export default api;

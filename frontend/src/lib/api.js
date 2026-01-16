import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_URL = `${BACKEND_URL}/api`;

// Utility function to extract error message string from API errors
export const getErrorMessage = (error, defaultMessage = "Something went wrong") => {
  const errorData = error.response?.data;
  
  if (!errorData) return error.message || defaultMessage;
  if (typeof errorData === 'string') return errorData;
  
  // Handle FastAPI validation errors (array of {type, loc, msg, input, url})
  if (errorData.detail) {
    if (typeof errorData.detail === 'string') return errorData.detail;
    if (Array.isArray(errorData.detail)) {
      return errorData.detail.map(e => e.msg || String(e)).join(', ');
    }
    // If detail is an object, try to get msg
    if (typeof errorData.detail === 'object' && errorData.detail.msg) {
      return errorData.detail.msg;
    }
  }
  
  if (errorData.message) {
    return typeof errorData.message === 'string' ? errorData.message : defaultMessage;
  }
  
  return defaultMessage;
};

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
  getRequests: () => requestsAPI.getIncoming(),
};

// Business API
export const businessAPI = {
  createProfile: (data) => api.post('/business/profile', data),
  getProfile: () => api.get('/business/profile'),
  getUnlockCredits: () => paymentsAPI.getCredits(),
};

// Instagram Verification (Simulated)
export const instagramAPI = {
  verify: (username) => api.post('/instagram/verify', { instagramUsername: username }),
};

// Marketplace API (Gated - Two-Way)
export const marketplaceAPI = {
  // Layer 1: Discovery (Free) - Brands see creators
  discoverCreators: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.niche) params.append('niche', filters.niche);
    if (filters.minFollowers) params.append('minFollowers', filters.minFollowers);
    if (filters.maxFollowers) params.append('maxFollowers', filters.maxFollowers);
    if (filters.location) params.append('location', filters.location);
    if (filters.openToBarter !== undefined) params.append('openToBarter', filters.openToBarter);
    return api.get(`/marketplace/creators?${params.toString()}`);
  },
  
  // Layer 1: Discovery (Free) - Creators see brands
  discoverBrands: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.industry) params.append('industry', filters.industry);
    if (filters.location) params.append('location', filters.location);
    if (filters.openToBarter !== undefined) params.append('openToBarter', filters.openToBarter);
    return api.get(`/marketplace/brands?${params.toString()}`);
  },
  
  // Layer 2: Unlocked (After Credit)
  getUnlockedCreator: (id) => api.get(`/marketplace/creators/${id}/unlocked`),
  getUnlockedBrand: (id) => api.get(`/marketplace/brands/${id}/unlocked`),
  
  // Layer 3: Full Access (After Escrow) - handled via campaign
  getFullCreator: (id) => api.get(`/marketplace/creators/${id}/unlocked`),
  
  // Unlock a profile (costs 1 credit)
  unlockCreator: (id) => api.post(`/marketplace/creator/${id}/unlock`),
  unlockBrand: (id) => api.post(`/marketplace/brand/${id}/unlock`),
  
  // Legacy compatibility
  getCreators: (filters = {}) => marketplaceAPI.discoverCreators(filters),
  getCreatorById: (id) => api.get(`/marketplace/creators/${id}/unlocked`),
  getBusinessById: (id) => api.get(`/marketplace/brands/${id}/unlocked`),
};

// Two-Way Request API
export const requestsAPI = {
  // Send a collab request (works both ways)
  create: (data) => api.post('/requests', data),
  getIncoming: () => api.get('/requests/incoming'),
  getOutgoing: () => api.get('/requests/outgoing'),
  respond: (id, action) => api.patch(`/requests/${id}/respond?action=${action}`),
};

// Campaigns API (After request acceptance)
export const campaignsAPI = {
  create: (data) => api.post('/campaigns', data),
  getMyCampaigns: () => api.get('/campaigns/my/list'),
  getById: (id) => api.get(`/campaigns/${id}`),
  confirm: (id) => api.patch(`/campaigns/${id}/confirm`),
  // Legacy
  getSent: () => api.get('/campaigns/my/list'),
  updateStatus: (id, status) => api.patch(`/campaigns/${id}/confirm`),
};

// Messages API
export const messagesAPI = {
  getMessages: (campaignId) => api.get(`/messages/${campaignId}`),
  sendMessage: (campaignId, text) => api.post(`/messages/${campaignId}`, { text }),
};

// Payments API
export const paymentsAPI = {
  // Credits
  getCredits: () => api.get('/payments/credits'),
  createUnlockOrder: () => api.post('/payments/unlock-pack/order'),
  verifyUnlockPayment: (data) => api.post('/payments/unlock-pack/verify', data),
  addDemoCredits: () => api.post('/payments/unlock-pack/demo'),
  // Escrow
  createEscrowOrder: (campaignId) => api.post(`/payments/escrow/${campaignId}/order`),
  verifyEscrowPayment: (campaignId, data) => api.post(`/payments/escrow/${campaignId}/verify`, data),
  demoEscrowPayment: (campaignId) => api.post(`/payments/escrow/${campaignId}/demo`),
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

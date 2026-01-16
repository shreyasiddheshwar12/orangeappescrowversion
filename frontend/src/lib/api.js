import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_URL = `${BACKEND_URL}/api`;

// Utility function to extract error message string from API errors
export const getErrorMessage = (error, defaultMessage = "Something went wrong") => {
  const errorData = error.response?.data;
  
  if (!errorData) return error.message || defaultMessage;
  if (typeof errorData === 'string') return errorData;
  
  if (errorData.detail) {
    if (typeof errorData.detail === 'string') return errorData.detail;
    if (Array.isArray(errorData.detail)) {
      return errorData.detail.map(e => e.msg || String(e)).join(', ');
    }
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
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  verifyInstagram: (username) => api.post('/auth/instagram/verify', { instagramUsername: username }),
};

// Creator API
export const creatorAPI = {
  createProfile: (data) => api.post('/creator/profile', data),
  getProfile: () => api.get('/creator/profile'),
};

// Business/Brand API
export const businessAPI = {
  createProfile: (data) => api.post('/business/profile', data),
  getProfile: () => api.get('/business/profile'),
};

// FREE Marketplace Discovery API
export const marketplaceAPI = {
  // Discover creators - FREE, partial data
  discoverCreators: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.niche) params.append('niche', filters.niche);
    if (filters.language) params.append('language', filters.language);
    if (filters.contentType) params.append('contentType', filters.contentType);
    if (filters.minPrice) params.append('minPrice', filters.minPrice);
    if (filters.maxPrice) params.append('maxPrice', filters.maxPrice);
    if (filters.barterOnly) params.append('barterOnly', filters.barterOnly);
    return api.get(`/marketplace/creators?${params.toString()}`);
  },
  
  // Discover brands - FREE, partial data
  discoverBrands: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.industry) params.append('industry', filters.industry);
    if (filters.location) params.append('location', filters.location);
    if (filters.barterOnly) params.append('barterOnly', filters.barterOnly);
    return api.get(`/marketplace/brands?${params.toString()}`);
  },
};

// Campaign API - Core collaboration flow
export const campaignAPI = {
  // Send campaign request
  create: (data) => api.post('/campaigns/', data),
  
  // Get incoming campaigns (where user is receiver)
  getIncoming: () => api.get('/campaigns/incoming'),
  
  // Get outgoing campaigns (where user is sender)
  getOutgoing: () => api.get('/campaigns/outgoing'),
  
  // Get single campaign
  getById: (id) => api.get(`/campaigns/${id}`),
  
  // Accept/Reject campaign
  respond: (id, action) => api.patch(`/campaigns/${id}/respond?action=${action}`),
  
  // Pay for campaign (unlocks identity + chat)
  pay: (id) => api.post(`/campaigns/${id}/pay`),
  
  // Add shipping details (barter)
  addShipping: (id, details) => api.post(`/campaigns/${id}/shipping?shippingDetails=${encodeURIComponent(details)}`),
  
  // Confirm product received (barter)
  confirmReceipt: (id) => api.post(`/campaigns/${id}/product-received`),
  
  // Submit content link
  submitContent: (id, link) => api.post(`/campaigns/${id}/submit-content?contentLink=${encodeURIComponent(link)}`),
  
  // Approve content (releases escrow)
  approveContent: (id) => api.post(`/campaigns/${id}/approve`),
  
  // Report issue
  report: (id, reason) => api.post(`/campaigns/${id}/report?reason=${encodeURIComponent(reason)}`),
};

// Messages API - Chat (only after payment)
export const messagesAPI = {
  getMessages: (campaignId) => api.get(`/messages/${campaignId}`),
  sendMessage: (campaignId, content) => api.post(`/messages/${campaignId}`, { content }),
};

// Admin API
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getReports: () => api.get('/admin/reports'),
  blacklistUser: (userId, reason) => api.post(`/admin/blacklist/${userId}?reason=${encodeURIComponent(reason)}`),
};

// Seed API (for testing)
export const seedAPI = {
  seed: () => api.post('/seed'),
};

export default api;

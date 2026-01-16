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
  // Instagram verification (simulated)
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
// Returns PARTIAL data only - no identity (name, Instagram) revealed
export const marketplaceAPI = {
  // Discover creators - FREE, partial data (no name, no Instagram)
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
  
  // Discover brands - FREE, partial data (no brand name, no Instagram)
  discoverBrands: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.industry) params.append('industry', filters.industry);
    if (filters.location) params.append('location', filters.location);
    if (filters.barterOnly) params.append('barterOnly', filters.barterOnly);
    return api.get(`/marketplace/brands?${params.toString()}`);
  },
};

// Campaign API - Core collaboration flow
// Flow: Create Request -> Accept/Reject -> Pay -> Unlock Identity + Chat -> Submit Content -> Approve -> Complete
export const campaignAPI = {
  // Create a new campaign request (sender initiates)
  create: (data) => api.post('/campaigns/', data),
  
  // Get campaigns where current user is the RECEIVER (incoming requests)
  getIncoming: () => api.get('/campaigns/incoming'),
  
  // Get campaigns where current user is the SENDER (sent requests)
  getOutgoing: () => api.get('/campaigns/outgoing'),
  
  // Get single campaign details
  getById: (id) => api.get(`/campaigns/${id}`),
  
  // Respond to a campaign request (receiver accepts or rejects)
  respond: (id, action) => api.patch(`/campaigns/${id}/respond?action=${action}`),
  
  // Pay for campaign (unlocks identity + chat)
  // - Paid collab: Full escrow amount
  // - Barter collab: Facilitation fee (₹149)
  pay: (id) => api.post(`/campaigns/${id}/pay`),
  
  // Add shipping details for barter collab (brand provides)
  addShipping: (id, details) => api.post(`/campaigns/${id}/shipping?shippingDetails=${encodeURIComponent(details)}`),
  
  // Creator confirms product received (barter collab)
  confirmReceipt: (id) => api.post(`/campaigns/${id}/product-received`),
  
  // Creator submits content link for review
  submitContent: (id, link) => api.post(`/campaigns/${id}/submit-content?contentLink=${encodeURIComponent(link)}`),
  
  // Brand approves content (releases escrow for paid collabs)
  approveContent: (id) => api.post(`/campaigns/${id}/approve`),
  
  // Report an issue with a campaign
  report: (id, reason) => api.post(`/campaigns/${id}/report?reason=${encodeURIComponent(reason)}`),
};

// Messages API - Chat (ONLY available after payment unlocks chat)
export const messagesAPI = {
  // Get messages for a campaign
  getMessages: (campaignId) => api.get(`/messages/${campaignId}`),
  // Send a message
  sendMessage: (campaignId, content) => api.post(`/messages/${campaignId}`, { content }),
};

// Admin API
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getReports: () => api.get('/admin/reports'),
  blacklistUser: (userId, reason) => api.post(`/admin/blacklist/${userId}?reason=${encodeURIComponent(reason)}`),
};

// Seed API (for testing/development)
export const seedAPI = {
  seed: () => api.post('/seed'),
};

export default api;

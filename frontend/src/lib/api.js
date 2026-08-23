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

// Instagram Verification API (simulated)
export const instagramAPI = {
  verify: (username) => api.post('/auth/instagram/verify', { instagramUsername: username }),
};

// Upload API (placeholder - not implemented in MVP)
export const uploadAPI = {
  uploadFile: async (file) => {
    // For MVP, we don't have real file upload - just return a placeholder URL
    return { data: { url: '' } };
  },
};

// Creator-specific API
export const creatorAPI = {
  createProfile: (data) => api.post('/creator/profile', data),
  getProfile: () => api.get('/creator/profile'),
  // Toggle visibility in marketplace (₹50/month subscription - MOCKED for MVP)
  toggleVisibility: (visible) => api.post(`/creator/subscription/toggle?visible=${visible}`),
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
// Flow: Create Request -> Accept/Reject -> Pay -> (Submit Link -> Verify Link) -> Complete -> Rate
export const campaignAPI = {
  // Create a new campaign request (sender initiates)
  // campaignType: 'paid' | 'barter_product' | 'barter_service'
  create: (data) => api.post('/campaigns/', data),
  
  // Get campaigns where current user is the RECEIVER (incoming requests)
  getIncoming: () => api.get('/campaigns/incoming'),
  
  // Get campaigns where current user is the SENDER (sent requests)
  getOutgoing: () => api.get('/campaigns/outgoing'),
  
  // Get single campaign details
  getById: (id) => api.get(`/campaigns/${id}`),
  
  // Respond to a campaign request (receiver accepts or rejects)
  respond: (id, action) => api.patch(`/campaigns/${id}/respond?action=${action}`),
  
  // Pay for campaign
  // - Paid collab: Full escrow amount -> identity unlocks immediately
  // - Barter collab: 10% fee -> identity unlocks after link verification
  pay: (id) => api.post(`/campaigns/${id}/pay`),
  
  // Add shipping details for barter collab (brand provides)
  addShipping: (id, details) => api.post(`/campaigns/${id}/shipping?shippingDetails=${encodeURIComponent(details)}`),
  
  // Creator confirms product received (barter collab)
  confirmReceipt: (id) => api.post(`/campaigns/${id}/product-received`),
  
  // Creator submits reel/story link (MANDATORY for all collabs)
  submitLink: (id, link) => api.post(`/campaigns/${id}/submit-link?contentLink=${encodeURIComponent(link)}`),
  
  // Brand verifies link (for barter: this unlocks identity)
  verifyLink: (id) => api.post(`/campaigns/${id}/verify-link`),
  
  // Brand marks campaign as complete (releases escrow for paid collabs)
  complete: (id) => api.post(`/campaigns/${id}/complete`),
  
  // Submit rating and feedback (after completion)
  rate: (id, rating, feedback) => api.post(`/campaigns/${id}/rate?rating=${rating}&feedback=${encodeURIComponent(feedback)}`),
  
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

// Legacy APIs for backward compatibility
export const paymentsAPI = {
  // Placeholder - payments now handled via campaignAPI.pay()
  createOrder: () => Promise.resolve({ data: {} }),
};

export const requestsAPI = {
  // Legacy - use campaignAPI instead
  respond: (id, action) => api.patch(`/campaigns/${id}/respond?action=${action}`),
};

export default api;

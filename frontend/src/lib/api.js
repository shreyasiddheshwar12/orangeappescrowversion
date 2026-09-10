import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_URL = `${BACKEND_URL}/api`;

export const getErrorMessage = (error, defaultMessage = 'Something went wrong') => {
  const data = error.response?.data;
  if (!data) return error.message || defaultMessage;
  if (typeof data === 'string') return data;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((e) => e.msg || String(e)).join(', ');
  if (data.detail?.msg) return data.detail.msg;
  return typeof data.message === 'string' ? data.message : defaultMessage;
};

const api = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
  return Promise.reject(error);
});

export const authAPI = {
  signup: (data) => api.post('/auth/signup', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  verifyInstagram: (username) => api.post('/auth/instagram/verify', { instagramUsername: username }),
};
export const instagramAPI = {
  connect: () => api.get('/auth/instagram/connect'),
  status: () => api.get('/auth/instagram/status'),
  disconnect: () => api.post('/auth/instagram/disconnect'),
};
export const uploadAPI = { uploadFile: async () => ({ data: { url: '' } }) };
export const creatorAPI = {
  createProfile: (data) => api.post('/creator/profile', data),
  getProfile: () => api.get('/creator/profile'),
  toggleVisibility: (visible) => api.post(`/creator/subscription/toggle?visible=${visible}`),
};
export const businessAPI = {
  createProfile: (data) => api.post('/business/profile', data),
  getProfile: () => api.get('/business/profile'),
};
export const marketplaceAPI = {
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
  discoverBrands: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.industry) params.append('industry', filters.industry);
    if (filters.location) params.append('location', filters.location);
    if (filters.barterOnly) params.append('barterOnly', filters.barterOnly);
    return api.get(`/marketplace/brands?${params.toString()}`);
  },
};

export const campaignAPI = {
  create: (data) => api.post('/campaigns/', data),
  getIncoming: () => api.get('/campaigns/incoming'),
  getOutgoing: () => api.get('/campaigns/outgoing'),
  getById: (id) => api.get(`/campaigns/${id}`),
  respond: (id, action) => api.patch(`/campaigns/${id}/respond?action=${action}`),
  // Creates a real Razorpay Order. The frontend must launch Checkout and then call verifyPayment.
  pay: (id) => api.post(`/payments/campaigns/${id}/order`),
  verifyPayment: (id, data) => api.post(`/payments/campaigns/${id}/verify`, data),
  addShipping: (id, details) => api.post(`/campaigns/${id}/shipping?shippingDetails=${encodeURIComponent(details)}`),
  confirmReceipt: (id) => api.post(`/campaigns/${id}/product-received`),
  submitLink: (id, link) => api.post(`/campaigns/${id}/submit-link?contentLink=${encodeURIComponent(link)}`),
  verifyLink: (id) => api.post(`/campaigns/${id}/verify-link`),
  complete: (id) => api.post(`/campaigns/${id}/complete`),
  rate: (id, rating, feedback) => api.post(`/campaigns/${id}/rate?rating=${rating}&feedback=${encodeURIComponent(feedback)}`),
  report: (id, reason) => api.post(`/campaigns/${id}/report?reason=${encodeURIComponent(reason)}`),
};
export const messagesAPI = {
  getMessages: (campaignId) => api.get(`/messages/${campaignId}`),
  sendMessage: (campaignId, content) => api.post(`/messages/${campaignId}`, { content }),
};
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getReports: () => api.get('/admin/reports'),
  blacklistUser: (userId, reason) => api.post(`/admin/blacklist/${userId}?reason=${encodeURIComponent(reason)}`),
};
export const seedAPI = { seed: () => api.post('/seed') };
export const paymentsAPI = {
  createOrder: (campaignId) => campaignAPI.pay(campaignId),
  verifyPayment: (campaignId, data) => campaignAPI.verifyPayment(campaignId, data),
};
export const requestsAPI = { respond: (id, action) => campaignAPI.respond(id, action) };
export default api;

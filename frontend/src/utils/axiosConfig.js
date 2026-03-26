import axios from 'axios';

// Create a custom axios instance
const api = axios.create({
  baseURL: 'http://localhost:8081/api',
});

// Configure token injection
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// Configure 401 redirect globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token
      sessionStorage.removeItem('jwt_token');
      // Redirect to login if we are not already there
      if (window.location.pathname !== '/admin/login') {
        window.location.href = '/admin/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

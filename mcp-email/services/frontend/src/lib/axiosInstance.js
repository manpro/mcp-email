/**
 * Centralized Axios Instance Configuration
 *
 * This file creates a single axios instance that all API calls should use.
 * It ensures consistent configuration across the app and handles:
 * - Base URL from environment variables
 * - Default headers
 * - Request/response interceptors for error handling
 * - Timeout configuration
 */

import axios from 'axios';

// Get the API URL from environment variable, with fallback
// In production, this should point to your actual backend server
// For browser access, use empty string to rely on Vite proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// BROWSER FIX: If we're in browser and have Docker backend URL, use empty string for proxy
const isDevelopment = import.meta.env.DEV;
const isDockerBackendUrl = API_BASE_URL && API_BASE_URL.includes('email-backend');
const RESOLVED_API_BASE_URL = (isDevelopment && isDockerBackendUrl) ? '' : API_BASE_URL;

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: RESOLVED_API_BASE_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  // Important: This ensures cookies are sent with requests if needed
  withCredentials: false, // Set to true if you need cookies/auth
});

// Request interceptor - runs before every request
axiosInstance.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    // const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }

    // Log the request for debugging (remove in production)
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      data: config.data,
    });

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor - runs after every response
axiosInstance.interceptors.response.use(
  (response) => {
    // Log successful responses for debugging
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  (error) => {
    // Enhanced error logging
    if (error.response) {
      // Server responded with error status
      console.error('[API Response Error]', {
        url: error.config?.url,
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        headers: error.response.headers,
      });

      // You can handle specific status codes here
      if (error.response.status === 401) {
        // Handle unauthorized - maybe redirect to login
        console.log('Unauthorized - user needs to login');
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('[API Network Error]', {
        url: error.config?.url,
        message: 'No response from server',
        baseURL: error.config?.baseURL,
        fullURL: `${error.config?.baseURL}${error.config?.url}`,
      });

      // This is typically a network error or CORS issue
      if (error.message === 'Network Error') {
        console.error('Network Error - Possible causes:');
        console.error('1. Backend server is not running');
        console.error('2. CORS is blocking the request');
        console.error('3. Wrong URL or port');
        console.error(`4. Check if backend is accessible at: ${RESOLVED_API_BASE_URL}`);
      }
    } else {
      // Error in request configuration
      console.error('[API Config Error]', error.message);
    }

    return Promise.reject(error);
  }
);

// Export both the instance and the base URL for reference
export default axiosInstance;
export { API_BASE_URL };

// Helper function to test API connection
export const testAPIConnection = async () => {
  try {
    console.log(`Testing API connection to: ${RESOLVED_API_BASE_URL}`);
    const response = await axiosInstance.get('/health');
    console.log('API connection successful:', response.data);
    return true;
  } catch (error) {
    console.error('API connection failed:', error.message);
    return false;
  }
};
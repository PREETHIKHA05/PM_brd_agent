import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add token to headers
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor to handle token expiration
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            const errorDetail = error.response?.data?.detail;
            if (errorDetail && (errorDetail.includes('expired') || errorDetail.includes('Invalid'))) {
                // Clear local storage
                localStorage.removeItem('token');
                localStorage.removeItem('user');

                // Redirect to login page
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export const register = (username, email, password) =>
    api.post('/auth/register', { username, email, password });

export const login = (username, password) =>
    api.post('/auth/login', { username, password });

export const uploadBRD = (text) =>
    api.post('/brd/upload', { text });

export const getRiskReview = (riskReviewId) =>
    api.get(`/risk-review/${riskReviewId}`);

export const finalizeRiskReview = (riskReviewId, suggestions) =>
    api.post(`/risk-review/${riskReviewId}/finalize`, suggestions);

export const generateQuestions = (riskReviewId) =>
    api.post(`/questions/generate/${riskReviewId}`);

export const generateStories = (runId, answers) =>
    api.post(`/stories/generate/${runId}`, { answers });

export const getRun = (runId) =>
    api.get(`/run/${runId}`);

export default api;

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

export const getDashboardStats = async () => {
  const response = await api.get('/dashboard/stats');
  return response.data;
};

export const getMaterials = async () => {
  const response = await api.get('/materials');
  return response.data;
};

export const uploadMaterial = async (formData) => {
  const response = await api.post('/materials/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getConcepts = async () => {
  const response = await api.get('/concepts');
  return response.data;
};

export const getStudyPath = async () => {
  const response = await api.get('/study-path');
  return response.data;
};

export const getAdaptiveQuestion = async (excludeIds = []) => {
  const response = await api.get('/assessment/adaptive', {
    params: { exclude_ids: excludeIds.join(',') },
  });
  return response.data;
};

export const submitAssessment = async (attempts) => {
  const response = await api.post('/assessment/submit', { attempts });
  return response.data;
};

export const getRecommendedResources = async (conceptName) => {
  const response = await api.get('/resources/recommend', {
    params: { concept_name: conceptName },
  });
  return response.data;
};

export const submitResourceFeedback = async (id, rating, helpful) => {
  const response = await api.post(`/resources/${id}/feedback`, { rating, helpful });
  return response.data;
};

export const completeResource = async (id) => {
  const response = await api.post(`/resources/${id}/complete`);
  return response.data;
};

export const trackResourceClick = async (id) => {
  const response = await api.post(`/resources/${id}/click`);
  return response.data;
};

export const getGamificationProfile = async () => {
  const response = await api.get('/gamification');
  return response.data;
};

export const runDemoSeeder = async () => {
  const response = await api.post('/demo/load');
  return response.data;
};

export default api;

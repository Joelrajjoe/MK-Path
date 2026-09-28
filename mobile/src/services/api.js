import axios from 'axios';

// Resolve API base URL strictly from environment with local fallback
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete client.defaults.headers.common['Authorization'];
  }
};

// Centralized error interceptor
client.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'Network connection failure. Please verify backend connectivity.';
    let status = 0;

    if (error.response) {
      status = error.response.status;
      const data = error.response.data;
      if (typeof data === 'string') {
        message = data;
      } else if (data && data.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data && data.message) {
        message = data.message;
      } else {
        message = `API Error (${status})`;
      }
    } else if (error.request) {
      message = 'No response from server. Check that FastAPI is running on port 8000.';
    }

    return Promise.reject({
      status,
      message,
      originalError: error,
    });
  }
);

// --- Core API Methods ---

// 1. Dashboard & Learner Intelligence
export const getDashboardSummary = async () => {
  const res = await client.get('/dashboard/summary');
  return res.data;
};

export const getDashboardStats = async () => {
  const res = await client.get('/dashboard/stats');
  return res.data;
};

// 2. Goals & Skill Gaps
export const getGoals = async () => {
  const res = await client.get('/goals');
  return res.data;
};

export const getGoalDetail = async (goalId) => {
  const res = await client.get(`/goals/${goalId}`);
  return res.data;
};

export const createGoal = async (goalData) => {
  const res = await client.post('/goals', goalData);
  return res.data;
};

export const getGoalSkillGaps = async (goalId) => {
  const res = await client.get(`/goals/${goalId}/skill-gaps`);
  return res.data;
};

export const deleteGoal = async (goalId) => {
  const res = await client.delete(`/goals/${goalId}`);
  return res.data;
};

// 3. Next-Best-Learning-Action (NBA) Engine
export const getNextBestAction = async () => {
  const res = await client.get('/next-best-action');
  return res.data;
};

// 4. Misconception & Prerequisite Diagnosis
export const getDiagnoses = async () => {
  const res = await client.get('/diagnosis');
  return res.data;
};

export const evaluateDiagnosis = async () => {
  const res = await client.post('/diagnosis/evaluate');
  return res.data;
};

// 5. What-If Counterfactual Simulator
export const runWhatIfSimulation = async (simulatedMasteries) => {
  const res = await client.post('/simulator/what-if', { simulated_masteries: simulatedMasteries });
  return res.data;
};

// 6. Materials Management
export const getMaterials = async () => {
  const res = await client.get('/materials');
  return res.data;
};

export const getMaterialDetail = async (materialId) => {
  const res = await client.get(`/materials/${materialId}`);
  return res.data;
};

export const uploadMaterial = async (formData) => {
  const res = await client.post('/materials/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const extractConcepts = async (materialId) => {
  const res = await client.post(`/materials/${materialId}/extract-concepts`);
  return res.data;
};

export const reprocessMaterial = async (materialId) => {
  const res = await client.post(`/materials/${materialId}/reprocess`);
  return res.data;
};

export const deleteMaterial = async (materialId) => {
  const res = await client.delete(`/materials/${materialId}`);
  return res.data;
};

// 7. Concepts & Knowledge Graph
export const getConcepts = async () => {
  const res = await client.get('/concepts');
  return res.data;
};

export const getConceptDetail = async (conceptId) => {
  const res = await client.get(`/concepts/${conceptId}`);
  return res.data;
};

export const getKnowledgeGraph = async () => {
  const res = await client.get('/graph');
  return res.data;
};

export const getMasteryEvidence = async (conceptId) => {
  const res = await client.get(`/mastery/evidence/${conceptId}`);
  return res.data;
};

// 8. Adaptive Assessments
export const getAssessmentQuestions = async (limit = 5) => {
  const res = await client.get(`/assessment?limit=${limit}`);
  return res.data;
};

export const getAdaptiveQuestion = async (excludeIds = []) => {
  const res = await client.get('/assessment/adaptive', {
    params: { exclude_ids: excludeIds.join(',') },
  });
  return res.data;
};

export const submitAssessmentAttempt = async (attemptData) => {
  const res = await client.post('/assessment/submit', {
    attempts: Array.isArray(attemptData) ? attemptData : [attemptData],
  });
  return res.data;
};

// 9. Adaptive Study Path
export const getStudyPath = async () => {
  const res = await client.get('/study-path');
  return res.data;
};

// 10. Intelligent Assignments
export const getAssignments = async () => {
  const res = await client.get('/assignments');
  return res.data;
};

export const getAssignmentDetail = async (assignmentId) => {
  const res = await client.get(`/assignments/${assignmentId}`);
  return res.data;
};

export const generateAssignment = async (data = {}) => {
  const res = await client.post('/assignments/generate', data);
  return res.data;
};

export const saveAssignmentDraft = async (assignmentId, answers) => {
  const res = await client.post(`/assignments/${assignmentId}/save-draft`, { answers });
  return res.data;
};

export const submitAssignment = async (assignmentId, answers) => {
  const res = await client.post(`/assignments/${assignmentId}/submit`, { answers });
  return res.data;
};

// 11. Profile & Preferences
export const getUserProfile = async () => {
  const res = await client.get('/user/profile');
  return res.data;
};

export const getUserPreferences = async () => {
  const res = await client.get('/user/preferences');
  return res.data;
};

export const updateUserPreferences = async (preferences) => {
  const res = await client.put('/user/preferences', preferences);
  return res.data;
};

// 12. Resources & Gamification
export const getResources = async () => {
  const res = await client.get('/resources');
  return res.data;
};

export const getGamification = async () => {
  const res = await client.get('/gamification');
  return res.data;
};

export default client;

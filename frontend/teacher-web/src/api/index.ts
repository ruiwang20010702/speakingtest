import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
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

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  sendCode: (email: string) =>
    api.post('/auth/send-code', { email }),

  login: (email: string, code: string) =>
    api.post<{ access_token: string; token_type: string; user_id: number; role: string; name: string }>('/auth/login', { email, code }),
};

// Students API
export const studentsApi = {
  list: () =>
    api.get<StudentListItem[]>('/students'),

  import: (studentId: number) =>
    api.post('/students/import', { student_id: studentId }),

  generateToken: (studentId: number, level?: string, unit?: string) =>
    api.post(`/students/${studentId}/token`, null, { params: { level, unit } }),

  getTests: (studentId: number) =>
    api.get(`/students/${studentId}/tests`),
};

// Tests API
export const testsApi = {
  getReport: (testId: number) =>
    api.get(`/tests/${testId}/report`),

  getInterpretation: (testId: number) =>
    api.get(`/tests/${testId}/interpretation`),

  generateShareLink: (testId: number) =>
    api.post(`/tests/${testId}/share`),
};

// Admin API
export const adminApi = {
  getOverview: () => api.get<OverviewStats>('/admin/stats/overview'),
  getFunnel: () => api.get<FunnelStats>('/admin/stats/funnel'),
  getCost: () => api.get<CostStats>('/admin/stats/cost'),
};

// Types
export interface OverviewStats {
  total_students: number;
  total_tests: number;
  total_shares: number;
  total_opens: number;
}

export interface FunnelStats {
  scanned: number;
  completed: number;
  shared: number;
  opened: number;
}

export interface CostStats {
  total_tests: number;
  estimated_cost_cny: number;
}

export interface StudentListItem {
  user_id: number;
  external_user_id?: string;
  student_name: string;
  cur_age?: number;
  cur_grade?: string;
  cur_level_desc?: string;
  main_last_buy_unit_name?: string;
  teacher_name?: string;
  ss_crm_name?: string;
}

export interface EntryResponse {
  access_token: string;
  token_type: string;
  student_id: number;
  student_name: string;
  level: string;
  unit: string;
  test_id: number;
}

export interface TestSummary {
  id: number;
  level: string;
  unit: string;
  status: string;
  total_score?: number;
  part1_score?: number;
  part2_score?: number;
  star_level?: number;
  created_at: string;
  completed_at?: string;
  entry_url?: string;
}

export interface TestReport {
  test_id: number;
  status: string;
  student_name?: string;
  level: string;
  unit: string;
  total_score?: number;
  star_level?: number;
  part1_score?: number;
  part1_fluency?: number;
  part1_pronunciation?: number;
  part2_score?: number;
  part2_transcript?: string;
  part2_items: TestItem[];
  part2_suggestions: string[];
  created_at?: string;
  completed_at?: string;
}

export interface TestItem {
  question_no: number;
  score: number;
  feedback?: string;
  evidence?: string;
}

export interface Interpretation {
  highlights: string[];
  weaknesses: string[];
  evidence: string[];
  suggestions: string[];
  parent_script: string;
}

// Questions API
export interface Question {
  id: number;
  level: string;
  unit: string;
  part: number;
  question_no: number;
  question: string;
  translation?: string;
  image_url?: string;
  reference_answer?: string;
  is_active: boolean;
}

export interface QuestionCreate {
  level: string;
  unit: string;
  part: number;
  question_no: number;
  question: string;
  translation?: string;
  image_url?: string;
  reference_answer?: string;
}

export interface QuestionUpdate {
  question?: string;
  translation?: string;
  image_url?: string;
  reference_answer?: string;
  is_active?: boolean;
}

export const questionsApi = {
  list: (level?: string, unit?: string) =>
    api.get<Question[]>('/questions', { params: { level, unit } }),

  getByLevelUnit: (level: string, unit: string) =>
    api.get<Question[]>(`/questions/${level}/${encodeURIComponent(unit)}`),

  create: (data: QuestionCreate) =>
    api.post<Question>('/questions', data),

  update: (id: number, data: QuestionUpdate) =>
    api.put<Question>(`/questions/${id}`, data),

  delete: (id: number) =>
    api.delete(`/questions/${id}`),

  uploadImage: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<{ success: boolean; image_url: string }>(`/questions/${id}/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
};

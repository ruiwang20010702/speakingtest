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
    api.get<TestReport>(`/tests/${testId}`),

  getInterpretation: (testId: number) =>
    api.get<Interpretation>(`/tests/${testId}/interpretation`),

  generateInterpretation: (testId: number) =>
    api.post<Interpretation>(`/tests/${testId}/interpretation`),

  generateShareLink: (testId: number) =>
    api.post<{ token: string; share_url: string; message: string }>(`/tests/${testId}/share`),

  updateReport: (testId: number, data: ReportOverrideRequest) =>
    api.patch<UpdateReportResponse>(`/tests/${testId}/report`, data),

  getReportOverride: (testId: number) =>
    api.get<GetReportOverrideResponse>(`/tests/${testId}/report/override`),

  resetReportOverride: (testId: number) =>
    api.delete<UpdateReportResponse>(`/tests/${testId}/report/override`),
};

// Admin API
export const adminApi = {
  // Stats
  getOverview: () => api.get<OverviewStats>('/admin/stats/overview'),
  getFunnel: () => api.get<FunnelStats>('/admin/stats/funnel'),
  getCost: () => api.get<CostStats>('/admin/stats/cost'),

  // Teacher Management
  getTeachers: () => api.get<TeacherSummary[]>('/admin/teachers'),
  getTeacherDetail: (teacherId: number) => api.get<TeacherDetail>(`/admin/teachers/${teacherId}`),

  // Audit Logs
  getAuditLogs: (params?: { action?: string; operator_id?: number; page?: number; limit?: number }) =>
    api.get<AuditLogResponse>('/admin/audit-logs', { params }),

  // Failed Tasks
  getFailedTasks: (maxRetry?: number) =>
    api.get<FailedTasksResponse>('/admin/failed-tasks', { params: maxRetry !== undefined ? { max_retry: maxRetry } : {} }),
  retryTask: (testId: number) =>
    api.post<RetryTaskResponse>(`/admin/failed-tasks/${testId}/retry`),

  // Regenerate Report (手动重新生成报告)
  regenerateReport: (testId: number, referenceText?: string) =>
    api.post<RegenerateReportResponse>(`/admin/tests/${testId}/regenerate`, 
      referenceText ? { reference_text: referenceText } : {}
    ),
};

// System API
export interface AIStatusResponse {
  status: 'online' | 'offline' | 'checking';
  model: string;
  message: string;
}

export const systemApi = {
  getAiStatus: () => api.get<AIStatusResponse>('/system/ai-status'),
};

// Types
export interface OverviewStats {
  total_students: number;
  total_tests: number;
  total_shares: number;
  total_opens: number;
  pending_followups: number;
  failed_tasks: number;
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

// Teacher Management Types
export interface TeacherSummary {
  user_id: number;
  email: string;
  ss_crm_name?: string;
  ss_dept4_name?: string;
  student_count: number;
  test_count: number;
  share_count: number;
}

export interface TeacherDetail {
  user_id: number;
  email: string;
  ss_crm_name?: string;
  ss_name?: string;
  ss_sm_name?: string;
  ss_dept4_name?: string;
  ss_group?: string;
  student_count: number;
  test_count: number;
  completed_tests: number;
  share_count: number;
  students: Array<{
    user_id: number;
    student_name: string;
    test_count: number;
  }>;
}

// Audit Log Types
export interface AuditLogItem {
  id: number;
  operator_id: number;
  operator_email?: string;
  action: string;
  target_type?: string;
  target_id?: number;
  details?: Record<string, unknown>;
  client_ip?: string;
  created_at: string;
}

export interface AuditLogResponse {
  total: number;
  page: number;
  limit: number;
  items: AuditLogItem[];
}

// Failed Tasks Types
export interface FailedTaskItem {
  test_id: number;
  student_name?: string;
  student_id: number;
  level: string;
  unit: string;
  status: string;
  failure_reason?: string;
  retry_count: number;
  created_at: string;
  updated_at?: string;
}

export interface FailedTasksResponse {
  total: number;
  items: FailedTaskItem[];
}

export interface RetryTaskResponse {
  success: boolean;
  message: string;
  test_id: number;
}

export interface RegenerateReportResponse {
  success: boolean;
  message: string;
  test_id: number;
  part1_queued: boolean;
  part2_queued: boolean;
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
  is_interpreted: boolean;  // 是否已生成报告解读
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

// Report Override Types (Full Edit)
export interface RadarScoreOverride {
  fluency?: number;         // 流利度 0-100
  pronunciation?: number;   // 发音 0-100
  confidence?: number;      // 自信度 0-100
  vocabulary?: number;      // 词汇 0-100
  sentence?: number;        // 整句输出 0-100
}

export interface Part1WordOverride {
  text: string;             // 单词文本
  status: 'perfect' | 'unclear' | 'failed';
  score?: number;           // 分数 0-100
}

export interface Part2ItemOverride {
  question_no: number;      // 题号
  score: number;            // 0/1/2
  feedback?: string;        // 反馈
  evidence?: string;        // 学生回答
}

export interface SuggestionOverride {
  highlights?: string[];    // 亮点
  weaknesses?: string[];    // 短板
  suggestions?: string[];   // 建议
  parent_script?: string;   // 家长话术
}

export interface ReportOverrideRequest {
  // 基础信息
  student_name?: string;
  level?: string;
  unit?: string;
  
  // 分数
  part1_score?: number;
  part2_score?: number;
  total_score?: number;
  star_level?: number;
  
  // 五维雷达图
  radar?: RadarScoreOverride;
  
  // Part1 词汇详情
  part1_words?: Part1WordOverride[];
  
  // Part2 对话详情
  part2_items?: Part2ItemOverride[];
  
  // 学习建议
  suggestion?: SuggestionOverride;
}

export interface UpdateReportResponse {
  success: boolean;
  message: string;
  override_keys?: string[];
}

export interface OriginalReportData {
  student_name: string;
  level: string;
  unit: string;
  part1_score?: number;
  part2_score?: number;
  total_score?: number;
  star_level?: number;
  radar?: RadarScoreOverride;
  part1_words?: Part1WordOverride[];
  part2_items?: Part2ItemOverride[];
  suggestion?: SuggestionOverride;
}

export interface GetReportOverrideResponse {
  has_override: boolean;
  override?: ReportOverrideRequest;
  original?: OriginalReportData;  // 原始数据用于初始化
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

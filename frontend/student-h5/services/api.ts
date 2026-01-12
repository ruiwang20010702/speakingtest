import { Level, Question, FullReportResponse } from '../types';
import axios from 'axios';

// API 实例
const api = axios.create({
  baseURL: '/api/v1',
});

// 从后端获取题目
export const getQuestions = async (level: Level, unit: string): Promise<Question[]> => {
  const response = await api.get(`/questions/${level}/${encodeURIComponent(unit)}`);
  const data = response.data;

  // 转换后端数据格式为前端格式
  return data.map((q: any) => ({
    id: q.id.toString(),
    type: q.part === 1 ? 'word' : 'qa',
    text: q.question,
    translation: q.translation,
    image: q.image_url,
    referenceAnswer: q.reference_answer,
  }));
};


// ============================================
// Real Backend API Functions
// ============================================

// 添加 token 到请求头
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 提交 Part 1 音频进行评测 (讯飞)
 */
export const submitPart1 = async (
  testId: number,
  audioBlob: Blob,
  text: string
): Promise<{
  success: boolean;
  score?: number;
  message?: string;
}> => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'part1.wav');
  formData.append('reference_text', text);

  const response = await api.post(`/tests/${testId}/part1`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};


/**
 * 上传音频到 OSS
 */
export const uploadAudio = async (
  testId: number,
  part: 'part1' | 'part2',
  audioBlob: Blob
): Promise<{ success: boolean; url: string; key: string; message: string }> => {
  const formData = new FormData();
  formData.append('test_id', testId.toString());
  formData.append('part', part);
  formData.append('audio', audioBlob, `${part}.wav`);

  const response = await api.post('/upload/audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

/**
 * 提交 Part 2 音频进行评测 (Qwen)
 * 1. 上传音频到 OSS
 * 2. 提交评测任务
 */
export const submitPart2 = async (
  testId: number,
  audioBlob: Blob
): Promise<{
  success: boolean;
  message?: string;
  task_id?: string;
}> => {
  try {
    // 1. 上传音频
    const uploadRes = await uploadAudio(testId, 'part2', audioBlob);
    if (!uploadRes.success || !uploadRes.url) {
      throw new Error(uploadRes.message || '音频上传失败');
    }

    // 2. 提交评测 (发送 URL)
    const response = await api.post(`/tests/${testId}/part2`, {
      audio_url: uploadRes.url
    });
    return response.data;
  } catch (error: any) {
    console.error('Part 2 提交失败:', error);
    return {
      success: false,
      message: error.response?.data?.detail?.message || error.message || '提交失败'
    };
  }
};

/**
 * 获取完整测评报告
 */
export const getTestReport = async (testId: number): Promise<FullReportResponse> => {
  const response = await api.get(`/tests/${testId}/report`);
  return response.data;
};


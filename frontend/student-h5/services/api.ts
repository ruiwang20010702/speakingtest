import { Level, Question, FullReportResponse } from '../types';
import axios from 'axios';
import { shouldUseMockData, getMockQuestions, mockReport } from './mockData';

// Check if we're in development mode
const isDev = import.meta.env.DEV;

// API 实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 5000, // 5秒超时
  // 启用 Cookie 认证（httpOnly Cookie 更安全，防止 XSS 窃取 token）
  withCredentials: true,
});

// 从后端获取题目（如果后端不可用，使用模拟数据）
export const getQuestions = async (level: Level, unit: string): Promise<Question[]> => {
  // 如果启用模拟数据模式，直接返回模拟数据
  if (shouldUseMockData()) {
    if (isDev) console.log('[Mock Mode] 使用模拟数据');
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(getMockQuestions(level, unit));
      }, 500); // 模拟网络延迟
    });
  }

  try {
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
  } catch (error: any) {
    // 如果后端不可用，自动切换到模拟数据模式（仅开发环境）
    if (isDev && (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED' || error.response?.status >= 500)) {
      console.warn('[API Error] 后端不可用，自动切换到模拟数据模式');
      return getMockQuestions(level, unit);
    }
    // 生产环境：抛出错误
    throw error;
  }
};


// ============================================
// Real Backend API Functions
// ============================================

// Token 已通过 httpOnly Cookie 自动携带，无需手动添加请求头

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
    if (isDev) console.error('Part 2 提交失败:', error);
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
  // 如果启用模拟数据模式，返回模拟报告（仅开发环境）
  if (isDev && shouldUseMockData()) {
    console.log('[Mock Mode] 使用模拟报告数据');
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          part1_score: 85,
          part2_score: 78,
          total_score: 82,
          star_level: 4,
          part2_suggestions: [
            '建议多练习日常对话，提高流利度',
            '注意单词发音的准确性',
            '可以尝试用更完整的句子回答问题'
          ]
        } as FullReportResponse);
      }, 500);
    });
  }

  try {
    const response = await api.get(`/tests/${testId}/report`);
    return response.data;
  } catch (error: any) {
    // 开发环境：如果后端不可用，返回模拟数据
    if (isDev && (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED' || error.response?.status >= 500)) {
      console.warn('[API Error] 后端不可用，使用模拟报告数据');
      return {
        part1_score: 85,
        part2_score: 78,
        total_score: 82,
        star_level: 4,
        part2_suggestions: [
          '建议多练习日常对话，提高流利度',
          '注意单词发音的准确性',
          '可以尝试用更完整的句子回答问题'
        ]
      } as FullReportResponse;
    }
    // 生产环境：抛出错误
    throw error;
  }
};


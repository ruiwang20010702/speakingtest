/**
 * API 客户端
 */
import axios from 'axios';
import type { QuestionData, TestResult, Level } from '../types';

// 生产环境使用环境变量配置的后端地址，开发环境使用代理
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

/**
 * 获取可用级别列表
 */
export const getLevels = async (): Promise<{ levels: Level[] }> => {
    const response = await api.get('/questions/levels');
    return response.data;
};

/**
 * 获取题目数据
 */
export const getQuestions = async (level: string, unit: string): Promise<QuestionData> => {
    const response = await api.get(`/questions/${level}/${unit}`);
    return response.data;
};

/**
 * 上传音频文件
 */
export const uploadAudio = async (file: File): Promise<{ filename: string; filepath: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/audio/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
    return response.data;
};

/**
 * 提交测试评分
 */
export const evaluateTest = async (
    studentName: string,
    level: string,
    unit: string,
    part1Audio: File,
    part2Audio: File,
    part3Audios: File[]  // 修改为File数组
): Promise<TestResult> => {
    const formData = new FormData();
    formData.append('student_name', studentName);
    formData.append('level', level);
    formData.append('unit', unit);
    formData.append('part1_audio', part1Audio);
    formData.append('part2_audio', part2Audio);

    // 添加Part 3的多个音频文件
    part3Audios.forEach((file, index) => {
        formData.append(`part3_audio_${index + 1}`, file);
    });

    const response = await api.post('/scoring/evaluate', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
    return response.data;
};

/**
 * 获取历史记录
 * 如果提供学生姓名则获取该学生的记录，否则获取所有记录
 */
export const getHistory = async (studentName?: string): Promise<TestResult[]> => {
    const url = studentName
        ? `/scoring/history/${studentName}`
        : '/scoring/history';
    const response = await api.get(url);
    return response.data;
};

/**
 * 根据 ID 获取单个测试结果
 */
export const getResultById = async (id: number): Promise<TestResult> => {
    const response = await api.get(`/scoring/result/${id}`);
    return response.data;
};

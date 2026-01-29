/**
 * API Client for Parent H5 Report
 * 
 * Security:
 * - No sensitive data logging in production
 * - Uses relative paths or HTTPS in production
 */

import { ParentReportData } from '../types';

// Check if we're in development mode
const isDev = import.meta.env.DEV;

// API Base URL - configurable via environment variable
function getApiBaseUrl(): string {
  // 优先使用环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  
  // 生产环境：使用相对路径，由 nginx 代理
  // 这样可以避免 mixed content 问题
  if (!isDev) {
    return '/api/v1';
  }
  
  // 开发环境：支持手机测试
  const hostname = window.location.hostname;
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    const protocol = window.location.protocol;
    return `${protocol}//${hostname}:8000/api/v1`;
  }
  
  return 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

// Only log in development
if (isDev) {
  console.log('[API] Base URL:', API_BASE_URL);
}

/**
 * Fetch parent report data by share token.
 * 
 * @param token - Share token from URL
 * @returns ParentReportData
 * @throws Error if fetch fails
 */
export async function fetchParentReport(token: string): Promise<ParentReportData> {
  const url = `${API_BASE_URL}/reports/${token}/h5`;
  
  // Only log URL in development (no token in log for security)
  if (isDev) {
    console.log('[API] Fetching report...');
  }
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: '网络请求失败' }));
    if (isDev) {
      console.error('[API] Request failed:', response.status);
    }
    throw new Error(errorData.detail || `请求失败: ${response.status}`);
  }
  
  const data = await response.json();
  
  // NEVER log report data (contains student info) - even in dev, only log success
  if (isDev) {
    console.log('[API] Report fetched successfully');
  }
  
  return data;
}

/**
 * Get token from URL path.
 * Supports: /p/{token}, /p/p/{token}, /s/p/{token}, /t/p/{token} etc.
 * Takes the segment after the last "p" in path as token.
 *
 * @returns token string or null if not found
 */
export function getTokenFromUrl(): string | null {
  const path = window.location.pathname;
  const segments = path.split('/').filter(Boolean);

  const lastPIndex = segments.lastIndexOf('p');
  if (lastPIndex !== -1 && segments[lastPIndex + 1]) {
    return segments[lastPIndex + 1];
  }

  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  return token || null;
}

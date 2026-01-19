/**
 * API Client for Parent H5 Report
 */

import { ParentReportData } from '../types';

// API Base URL - configurable via environment variable
// 自动检测：如果在手机上访问（非localhost），使用当前主机的IP
function getApiBaseUrl(): string {
  // 优先使用环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  
  // 如果在手机上访问（hostname 不是 localhost），使用当前主机的 IP
  const hostname = window.location.hostname;
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    // 使用当前访问的前端地址，替换端口为后端端口
    const protocol = window.location.protocol;
    return `${protocol}//${hostname}:8000/api/v1`;
  }
  
  // 默认本地开发地址
  return 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

// 开发环境下打印 API 地址
if (import.meta.env.DEV) {
  console.log('[API] Base URL:', API_BASE_URL);
  console.log('[API] Current hostname:', window.location.hostname);
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
  console.log('[API] Fetching report from:', url);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: '网络请求失败' }));
    console.error('[API] Request failed:', response.status, errorData);
    throw new Error(errorData.detail || `请求失败: ${response.status}`);
  }
  
  const data = await response.json();
  console.log('[API] Report data received:', data);
  return data;
}

/**
 * Get token from URL path.
 * Expects URL format: /p/{token} or ?token={token}
 * 
 * @returns token string or null if not found
 */
export function getTokenFromUrl(): string | null {
  // Check URL path: /p/{token}
  const pathMatch = window.location.pathname.match(/\/p\/([^/]+)/);
  if (pathMatch) {
    return pathMatch[1];
  }
  
  // Check query parameter: ?token={token}
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  if (token) {
    return token;
  }
  
  return null;
}

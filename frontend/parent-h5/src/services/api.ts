/**
 * API Client for Parent H5 Report
 */

import { ParentReportData } from '../types';

// API Base URL - configurable via environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Fetch parent report data by share token.
 * 
 * @param token - Share token from URL
 * @returns ParentReportData
 * @throws Error if fetch fails
 */
export async function fetchParentReport(token: string): Promise<ParentReportData> {
  const response = await fetch(`${API_BASE_URL}/reports/${token}/h5`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: '网络请求失败' }));
    throw new Error(errorData.detail || `请求失败: ${response.status}`);
  }
  
  return response.json();
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

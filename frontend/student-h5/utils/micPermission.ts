/**
 * 麦克风权限检测工具
 */

export type PermissionState = 'prompt' | 'granted' | 'denied' | 'unknown';

export type PermissionError = 'denied' | 'not-found' | 'not-supported' | 'unknown';

/**
 * 检查麦克风权限状态
 * @returns 权限状态: prompt(待授权), granted(已允许), denied(已拒绝), unknown(未知)
 */
export async function checkMicPermission(): Promise<PermissionState> {
  try {
    // 某些浏览器不支持 permissions.query
    if (!navigator.permissions || !navigator.permissions.query) {
      return 'unknown';
    }
    
    const result = await navigator.permissions.query({ 
      name: 'microphone' as PermissionName 
    });
    return result.state as PermissionState;
  } catch {
    // 浏览器不支持查询麦克风权限
    return 'unknown';
  }
}

/**
 * 请求麦克风权限并获取媒体流
 * @returns 成功返回 stream，失败返回错误类型
 */
export async function requestMicPermission(): Promise<{
  success: boolean;
  stream?: MediaStream;
  error?: PermissionError;
  errorMessage?: string;
}> {
  try {
    // 检查是否支持 getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return { 
        success: false, 
        error: 'not-supported',
        errorMessage: '当前浏览器不支持录音功能'
      };
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return { success: true, stream };
  } catch (err: any) {
    // 根据错误类型返回不同的错误码
    const errorMap: Record<string, PermissionError> = {
      'NotAllowedError': 'denied',
      'PermissionDeniedError': 'denied',
      'NotFoundError': 'not-found',
      'DevicesNotFoundError': 'not-found',
      'NotSupportedError': 'not-supported',
      'NotReadableError': 'not-found', // 设备被占用
      'OverconstrainedError': 'not-found',
    };
    
    const error = errorMap[err.name] || 'unknown';
    
    return { 
      success: false, 
      error,
      errorMessage: err.message || '获取麦克风权限失败'
    };
  }
}

/**
 * 获取权限错误的用户友好描述
 */
export function getPermissionErrorMessage(error: PermissionError): string {
  const messages: Record<PermissionError, string> = {
    'denied': '麦克风权限被拒绝',
    'not-found': '未检测到麦克风设备',
    'not-supported': '当前浏览器不支持录音',
    'unknown': '无法访问麦克风',
  };
  return messages[error];
}

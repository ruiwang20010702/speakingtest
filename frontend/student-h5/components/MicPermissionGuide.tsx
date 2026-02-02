/**
 * 麦克风权限引导弹窗
 * 根据不同的权限错误类型，显示对应的操作指引
 */
import React from 'react';
import type { PermissionError } from '../utils/micPermission';

interface MicPermissionGuideProps {
  isOpen: boolean;
  type: PermissionError;
  onClose: () => void;
  onRetry: () => void;
}

// 不同错误类型的引导内容
const guideContent: Record<PermissionError, { 
  icon: string; 
  title: string; 
  steps: string[];
  showRefreshTip?: boolean;
}> = {
  denied: {
    icon: '🔒',
    title: '麦克风权限被拒绝',
    steps: [
      '点击地址栏左边的 🔒 图标',
      '点击「网站设置」或「权限」',
      '找到「麦克风」，改为「允许」',
      '刷新页面后重试',
    ],
    showRefreshTip: true,
  },
  'not-found': {
    icon: '🎤',
    title: '未检测到麦克风',
    steps: [
      '请检查设备是否有麦克风',
      '如果使用蓝牙耳机，请确保已连接',
      '尝试关闭其他使用麦克风的应用',
      '重启浏览器后重试',
    ],
  },
  'not-supported': {
    icon: '⚠️',
    title: '浏览器不支持录音',
    steps: [
      '请使用 Chrome、Safari 或 Edge 浏览器',
      '确保浏览器是最新版本',
      '避免使用 App 内置浏览器',
    ],
  },
  unknown: {
    icon: '❓',
    title: '无法访问麦克风',
    steps: [
      '请检查系统是否允许浏览器使用麦克风',
      '尝试刷新页面重试',
      '如问题持续，请更换浏览器或设备',
    ],
  },
};

const MicPermissionGuide: React.FC<MicPermissionGuideProps> = ({ 
  isOpen, 
  type, 
  onClose, 
  onRetry 
}) => {
  if (!isOpen) return null;

  const content = guideContent[type] || guideContent.unknown;
  const { icon, title, steps, showRefreshTip } = content;

  const handleRefresh = () => {
    window.location.reload();
  };

  const handleRetry = () => {
    onClose();
    // 延迟一下再重试，让弹窗关闭动画完成
    setTimeout(() => {
      onRetry();
    }, 100);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-2xl animate-in zoom-in-95 fade-in duration-200">
        {/* 标题区域 */}
        <div className="text-center mb-5">
          <div className="text-5xl mb-3">{icon}</div>
          <h2 className="text-xl font-bold text-gray-800">{title}</h2>
        </div>

        {/* 操作步骤 */}
        <ol className="space-y-3 mb-6">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="w-6 h-6 bg-[#1CB0F6] text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span className="text-gray-700 text-sm">{step}</span>
            </li>
          ))}
        </ol>

        {/* 按钮区域 */}
        <div className="flex gap-3">
          {showRefreshTip ? (
            // 权限被拒绝时，显示"刷新页面"按钮
            <>
              <button
                onClick={onClose}
                className="flex-1 py-3 border border-gray-300 text-gray-600 font-bold rounded-xl hover:bg-gray-50 transition-colors"
              >
                关闭
              </button>
              <button
                onClick={handleRefresh}
                className="flex-1 py-3 bg-[#1CB0F6] text-white font-bold rounded-xl shadow-[0_4px_0_#1899D6] active:shadow-none active:translate-y-[4px] transition-all"
              >
                刷新页面
              </button>
            </>
          ) : (
            // 其他情况，显示"重试"按钮
            <>
              <button
                onClick={onClose}
                className="flex-1 py-3 border border-gray-300 text-gray-600 font-bold rounded-xl hover:bg-gray-50 transition-colors"
              >
                关闭
              </button>
              <button
                onClick={handleRetry}
                className="flex-1 py-3 bg-[#1CB0F6] text-white font-bold rounded-xl shadow-[0_4px_0_#1899D6] active:shadow-none active:translate-y-[4px] transition-all"
              >
                重试
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MicPermissionGuide;

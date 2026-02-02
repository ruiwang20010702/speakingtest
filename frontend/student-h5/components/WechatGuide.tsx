/**
 * 微信跳转引导蒙层
 * 在微信内置浏览器中显示，引导用户使用外部浏览器打开
 */
import React, { useState } from 'react';

interface WechatGuideProps {
  isOpen: boolean;
}

const WechatGuide: React.FC<WechatGuideProps> = ({ isOpen }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const copyLink = async () => {
    const url = window.location.href;
    
    try {
      // 现代浏览器 API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        return;
      }
    } catch {
      // clipboard API 失败，使用 fallback
    }

    // Fallback: 使用 execCommand
    try {
      const input = document.createElement('input');
      input.value = url;
      input.style.position = 'fixed';
      input.style.opacity = '0';
      document.body.appendChild(input);
      input.select();
      input.setSelectionRange(0, url.length);
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 复制失败，提示用户手动复制
      alert('复制失败，请长按链接手动复制');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 z-[9999]">
      {/* 右上角箭头指示 */}
      <div className="absolute top-3 right-3 flex flex-col items-end">
        <div className="text-5xl animate-bounce">
          👆
        </div>
        <div className="mt-2 bg-white rounded-lg px-3 py-1.5 text-sm font-bold text-gray-800 shadow-lg">
          点击这里
        </div>
      </div>

      {/* 引导内容卡片 */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[88%] max-w-[320px]">
        <div className="bg-white rounded-2xl p-6 shadow-2xl">
          {/* 标题区域 */}
          <div className="text-center mb-5">
            <div className="text-5xl mb-3">📱</div>
            <h2 className="text-xl font-black text-gray-800">
              请在浏览器中打开
            </h2>
            <p className="text-gray-500 text-sm mt-1">
              微信内无法使用麦克风录音
            </p>
          </div>

          {/* 操作步骤 */}
          <div className="space-y-3 mb-5">
            <div className="flex items-center gap-3 bg-blue-50 rounded-xl p-3">
              <span className="w-7 h-7 bg-[#1CB0F6] text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                1
              </span>
              <span className="text-gray-700 font-medium text-sm">
                点击右上角 <span className="font-mono bg-gray-200 px-1.5 py-0.5 rounded text-xs">···</span> 按钮
              </span>
            </div>
            <div className="flex items-center gap-3 bg-blue-50 rounded-xl p-3">
              <span className="w-7 h-7 bg-[#1CB0F6] text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                2
              </span>
              <span className="text-gray-700 font-medium text-sm">
                选择「在浏览器中打开」
              </span>
            </div>
          </div>

          {/* 分隔线 */}
          <div className="border-t border-gray-200 my-4"></div>

          {/* 复制链接按钮 */}
          <button
            onClick={copyLink}
            className={`w-full py-3 font-bold rounded-xl transition-all ${
              copied 
                ? 'bg-green-500 text-white' 
                : 'bg-[#1CB0F6] hover:bg-[#1899D6] text-white shadow-[0_4px_0_#1899D6] active:shadow-none active:translate-y-[4px]'
            }`}
          >
            {copied ? '✅ 链接已复制' : '📋 复制链接'}
          </button>
          <p className="text-center text-gray-400 text-xs mt-2">
            也可以复制链接到浏览器打开
          </p>
        </div>

        {/* 底部提示 */}
        <div className="mt-4 text-center">
          <p className="text-white/70 text-sm">
            🎤 本测评需要录音功能
          </p>
        </div>
      </div>
    </div>
  );
};

export default WechatGuide;

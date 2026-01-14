import React from 'react';
import { Loader2 } from 'lucide-react';

interface PhoneMockupProps {
  src?: string;
  loading?: boolean;
  title?: string;
}

export const PhoneMockup: React.FC<PhoneMockupProps> = ({ 
  src, 
  loading = false,
  title = '家长端 H5 预览'
}) => {
  return (
    <div className="flex flex-col items-center">
      {/* Phone Frame */}
      <div className="relative">
        {/* Outer frame with shadow */}
        <div 
          className="relative bg-gray-900 rounded-[3rem] p-3 shadow-2xl"
          style={{ 
            width: '390px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35), inset 0 1px 1px rgba(255,255,255,0.1)'
          }}
        >
          {/* Notch / Dynamic Island */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-7 bg-gray-900 rounded-b-3xl z-10 flex items-center justify-center">
            <div className="w-20 h-5 bg-black rounded-full"></div>
          </div>
          
          {/* Screen bezel */}
          <div className="bg-black rounded-[2.25rem] overflow-hidden">
            {/* Status bar placeholder */}
            <div className="h-12 bg-gradient-to-b from-gray-900/50 to-transparent absolute top-3 left-3 right-3 z-20 rounded-t-[2.25rem]"></div>
            
            {/* Screen content */}
            <div 
              className="bg-white relative"
              style={{ 
                width: '364px', 
                height: '788px',
                borderRadius: '2.25rem'
              }}
            >
              {loading ? (
                <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50">
                  <Loader2 className="animate-spin text-primary mb-4" size={48} />
                  <p className="text-text-sub text-sm">正在加载预览...</p>
                </div>
              ) : src ? (
                <iframe
                  src={src}
                  className="w-full h-full border-0"
                  style={{ borderRadius: '2.25rem' }}
                  title={title}
                  allow="autoplay; fullscreen"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50">
                  <div className="text-6xl mb-4">📱</div>
                  <p className="text-text-sub text-sm">等待加载...</p>
                </div>
              )}
            </div>
          </div>
          
          {/* Home indicator */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-gray-600 rounded-full"></div>
        </div>
        
        {/* Side buttons - Volume */}
        <div className="absolute left-0 top-28 -translate-x-1 w-1 h-8 bg-gray-700 rounded-l"></div>
        <div className="absolute left-0 top-40 -translate-x-1 w-1 h-12 bg-gray-700 rounded-l"></div>
        <div className="absolute left-0 top-56 -translate-x-1 w-1 h-12 bg-gray-700 rounded-l"></div>
        
        {/* Side button - Power */}
        <div className="absolute right-0 top-36 translate-x-1 w-1 h-16 bg-gray-700 rounded-r"></div>
      </div>
      
      {/* Label */}
      <div className="mt-6 text-center">
        <p className="text-text-sub text-sm">
          {title}
        </p>
        <p className="text-text-sub/60 text-xs mt-1">
          左右滑动可切换页面
        </p>
      </div>
    </div>
  );
};

export default PhoneMockup;


import React from 'react';

interface ProgressBarProps {
  current: number;
  total: number;
}

const MonkeyCharacter = () => (
  <svg width="32" height="32" viewBox="0 0 100 100" className="drop-shadow-sm">
    <circle cx="50" cy="50" r="45" fill="#8B4513" />
    <circle cx="50" cy="55" r="35" fill="#FFE4B5" />
    <circle cx="15" cy="45" r="12" fill="#8B4513" />
    <circle cx="85" cy="45" r="12" fill="#8B4513" />
    <circle cx="15" cy="45" r="7" fill="#FFE4B5" />
    <circle cx="85" cy="45" r="7" fill="#FFE4B5" />
    <circle cx="38" cy="45" r="4" fill="#000" />
    <circle cx="62" cy="45" r="4" fill="#000" />
    <path d="M 35 65 Q 50 75 65 65" stroke="#000" strokeWidth="2" fill="none" strokeLinecap="round" />
    <path d="M 15 45 Q 15 10 50 10 Q 85 10 85 45" stroke="#1CB0F6" strokeWidth="8" fill="none" />
    <rect x="5" y="40" width="15" height="20" rx="5" fill="#FFD200" />
    <rect x="80" y="40" width="15" height="20" rx="5" fill="#FFD200" />
  </svg>
);

const ProgressBar: React.FC<ProgressBarProps> = ({ current, total }) => {
  const percentage = Math.min(100, Math.max(0, (current / total) * 100));

  return (
    <div className="w-full relative py-2">
      <div className="w-full bg-white/30 backdrop-blur-sm h-10 rounded-full overflow-hidden relative border-2 border-white/50">
        <div 
          className="bg-[#ACE7FF] h-full rounded-full transition-all duration-700 ease-in-out relative flex items-center justify-end shadow-inner" 
          style={{ width: `${percentage}%` }}
        >
          <div className="absolute top-1 left-4 right-4 h-1.5 bg-white/40 rounded-full"></div>
          <div className="mr-1 pointer-events-none transition-transform duration-700">
            <div className="animate-bounce-subtle flex items-center justify-center">
               <MonkeyCharacter />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressBar;


import React from 'react';

interface ProgressBarProps {
  current: number;
  total: number;
}

const MonkeyCharacter = () => (
  <img 
    src={`${import.meta.env.BASE_URL}Dynamic materials/progress bar.gif`} 
    alt="Monkey" 
    className="w-20 h-20 object-contain drop-shadow-sm"
  />
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

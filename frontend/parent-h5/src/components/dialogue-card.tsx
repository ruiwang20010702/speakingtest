import React from 'react';
import { motion } from 'framer-motion';
import { ThumbsUp, ThumbsDown, Star, Target } from 'lucide-react';

interface DialogueCardProps {
  type: 'best' | 'worst';
  score: number;
  children: React.ReactNode;
  delay?: number;
}

export const DialogueCard: React.FC<DialogueCardProps> = ({ 
  type, 
  score, 
  children, 
  delay = 0 
}) => {
  const isBest = type === 'best';
  const Icon = isBest ? ThumbsUp : ThumbsDown;
  const BadgeIcon = isBest ? Star : Target;
  
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className={`
        bg-white border-2 border-black rounded-lg shadow-[2px_2px_0px_rgba(0,0,0,1)] overflow-hidden
        ${isBest ? 'bg-green-50' : 'bg-red-50'}
      `}
    >
      {/* Header */}
      <header className={`
        border-b-2 border-black px-2 py-1 flex items-center space-x-1.5 shrink-0
        ${isBest ? 'bg-green-500' : 'bg-red-500'}
      `}>
        <Icon size={10} className="text-white" />
        <span className="text-[7px] font-black text-white uppercase flex-1">
          {isBest ? '最佳表现' : '需要改进'}
        </span>
        <div 
          className="px-1.5 py-0.5 rounded border border-black flex items-center space-x-0.5"
          style={{ 
            backgroundColor: isBest ? '#10B981' : '#EF4444'
          }}
        >
          <BadgeIcon size={8} className="text-white fill-white" />
          <span className="text-[10px] font-black text-white">{score}</span>
        </div>
      </header>
      
      {/* Content */}
      <div className="p-1.5 space-y-1 flex-1 min-h-0 flex flex-col">
        {children}
      </div>
    </motion.article>
  );
};


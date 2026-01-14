import React from 'react';
import { motion } from 'framer-motion';

interface AdviceCardProps {
  number: number;
  title: string;
  content: string;
  color: 'green' | 'blue' | 'yellow';
  delay?: number;
}

export const AdviceCard: React.FC<AdviceCardProps> = ({ 
  number, 
  title, 
  content, 
  color,
  delay = 0 
}) => {
  const colorMap = {
    green: {
      bg: 'bg-green-50',
      border: 'border-green-300',
      number: 'bg-green-500',
      text: 'text-green-800',
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-300',
      number: 'bg-blue-500',
      text: 'text-blue-800',
    },
    yellow: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-300',
      number: 'bg-yellow-500',
      text: 'text-yellow-800',
    },
  };

  const colors = colorMap[color];

  return (
    <motion.article
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, type: "spring", stiffness: 200, damping: 15 }}
      className={`
        ${colors.bg} border ${colors.border} rounded-lg p-2
        flex items-start gap-2
      `}
    >
      <motion.div
        className={`${colors.number} w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0`}
        whileHover={{ scale: 1.1, rotate: 5 }}
        transition={{ type: "spring", stiffness: 400 }}
      >
        <span className="text-[10px] font-black text-white">{number}</span>
      </motion.div>
      <div className="flex-1 min-w-0">
        <h4 className={`text-[10px] font-black ${colors.text} uppercase mb-0.5`}>
          {title}
        </h4>
        <p className={`text-xs font-bold ${colors.text} leading-tight`}>
          {content}
        </p>
      </div>
    </motion.article>
  );
};


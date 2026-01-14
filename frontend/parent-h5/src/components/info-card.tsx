import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface InfoCardProps {
  icon: LucideIcon;
  title: string;
  content: string;
  delay?: number;
}

export const InfoCard: React.FC<InfoCardProps> = ({ 
  icon: Icon, 
  title, 
  content,
  delay = 0 
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, type: "spring", stiffness: 200 }}
      className="bg-white/50 border border-black/10 rounded-lg p-2"
    >
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={11} className="text-klein" />
        <span className="text-[9px] font-black text-klein uppercase">{title}</span>
      </div>
      <p className="text-[9px] font-bold text-klein leading-tight ml-4">
        {content}
      </p>
    </motion.div>
  );
};


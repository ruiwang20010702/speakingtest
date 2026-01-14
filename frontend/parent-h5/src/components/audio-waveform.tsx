import React from 'react';
import { motion } from 'framer-motion';

interface AudioWaveformProps {
  label?: string;
  className?: string;
  color?: string;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({ 
  label, 
  className = '',
  color = '#FFF59D' 
}) => {
  // Generate random waveform bars
  const bars = Array.from({ length: 40 }).map((_, i) => ({
    id: i,
    height: Math.random() * 60 + 20, // Random height between 20-80
    delay: i * 0.05,
  }));

  return (
    <div className={`flex flex-col items-center ${className}`}>
      {label && (
        <div className="mb-2 text-[8px] font-black text-white/80 uppercase tracking-wider">
          {label}
        </div>
      )}
      <div className="flex items-end justify-center space-x-[2px] h-16">
        {bars.map((bar) => (
          <motion.div
            key={bar.id}
            initial={{ height: 10 }}
            animate={{ 
              height: [10, bar.height, 10],
            }}
            transition={{
              duration: 1.5,
              delay: bar.delay,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{
              backgroundColor: color,
              width: '3px',
              minHeight: '4px',
              borderRadius: '2px',
            }}
          />
        ))}
      </div>
    </div>
  );
};


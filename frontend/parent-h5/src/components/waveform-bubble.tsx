import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

interface WaveformBubbleProps {
  sender: 'ai' | 'user';
  onClick?: () => void;
  seed?: number;
}

export const WaveformBubble: React.FC<WaveformBubbleProps> = ({ 
  sender, 
  onClick,
  seed = 0
}) => {
  const isAI = sender === 'ai';
  
  // Natural waveform with physics-based variation
  const waveform = useMemo(() => {
    const seedValue = seed || (isAI ? 100 : 200);
    const random = (offset: number) => {
      const x = Math.sin(seedValue + offset) * 10000;
      return x - Math.floor(x);
    };
    
    // Create organic waveform with natural variation
    return Array.from({ length: 20 }).map((_, i) => {
      const base = 6 + random(i) * 10;
      const wave = Math.sin(i * 0.4) * 4;
      const noise = (random(i + 10) - 0.5) * 2;
      return {
        id: i,
        height: Math.max(4, Math.min(18, base + wave + noise)),
        delay: i * 0.015,
        width: 2 + random(i + 20) * 1,
      };
    });
  }, [isAI, seed]);

  return (
    <div className={`flex flex-col ${isAI ? 'items-start' : 'items-end'}`}>
      <motion.div
        onClick={onClick}
        className={`
          rounded-2xl px-3 py-2 max-w-[75%] relative
          ${isAI ? 'bg-blue-500' : 'bg-baby'}
          ${onClick ? 'cursor-pointer hover:opacity-90 transition-opacity' : ''}
        `}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={onClick ? { scale: 1.02 } : {}}
        whileTap={onClick ? { scale: 0.98 } : {}}
      >
        <div className="flex items-center gap-2">
          <div className="flex items-end justify-center space-x-[1.5px] h-6 flex-1">
            {waveform.map((bar) => (
              <motion.div
                key={bar.id}
                initial={{ height: 4 }}
                animate={{ 
                  height: [4, bar.height, 4],
                }}
                transition={{
                  duration: 0.8,
                  delay: bar.delay,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                className={`
                  rounded-full
                  ${isAI ? 'bg-white' : 'bg-klein'}
                `}
                style={{
                  width: '2px',
                  minHeight: '4px',
                }}
              />
            ))}
          </div>
          
          {onClick && (
            <div className="flex items-center gap-1 text-[8px] font-bold text-klein/70">
              <Sparkles size={9} />
              <span className="uppercase">点击查看</span>
            </div>
          )}
        </div>
      </motion.div>
      <div className={`mt-1 text-[10px] ${isAI ? 'text-white/60' : 'text-white/60'}`}>
        {isAI ? 'Q: AI老师' : 'A: 你'}
      </div>
    </div>
  );
};


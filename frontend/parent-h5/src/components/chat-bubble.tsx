import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

interface ChatBubbleProps {
  text?: string;
  sender: 'ai' | 'user';
  isWaveform?: boolean;
  onClick?: () => void;
  className?: string;
  seed?: number;
  showHint?: boolean;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ 
  text, 
  sender, 
  isWaveform = false,
  onClick,
  className = '',
  seed = 0,
  showHint = false
}) => {
  const isAI = sender === 'ai';
  
  // Generate smoother waveform with better visual appeal
  const bars = useMemo(() => {
    const seedValue = seed || (isAI ? 100 : 200);
    const random = (offset: number) => {
      const x = Math.sin(seedValue + offset) * 10000;
      return x - Math.floor(x);
    };
    
    // Create a more natural waveform pattern
    return Array.from({ length: 24 }).map((_, i) => {
      const baseHeight = 6 + random(i) * 12; // Base height 6-18
      const variation = Math.sin(i * 0.5) * 3; // Smooth variation
      return {
        id: i,
        height: Math.max(4, Math.min(20, baseHeight + variation)),
        delay: i * 0.02,
      };
    });
  }, [isAI, seed]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col ${isAI ? 'items-start' : 'items-end'} ${className}`}
    >
      <motion.div
        onClick={onClick}
        className={`
          relative max-w-[80%] group
          ${onClick ? 'cursor-pointer' : ''}
        `}
        whileTap={onClick ? { scale: 0.98 } : {}}
      >
        {/* Decorative corner elements */}
        {!isAI && onClick && (
          <>
            <div className="absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 border-baby/50 rounded-tr-lg" />
            <div className="absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 border-baby/50 rounded-bl-lg" />
          </>
        )}
        
        <div className={`
          px-4 py-3 relative overflow-hidden
          ${isAI 
            ? 'bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700' 
            : 'bg-gradient-to-br from-baby via-yellow-200 to-baby'
          }
          ${onClick ? 'hover:shadow-[0_0_20px_rgba(255,245,157,0.4)]' : ''}
          transition-all duration-300
        `}
        style={{
          clipPath: isAI 
            ? 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)'
            : 'polygon(12px 0, 100% 0, 100% 100%, 0 100%, 0 12px)',
        }}>
          {/* Animated background pattern */}
          <motion.div
            className={`absolute inset-0 opacity-10 ${
              isAI ? 'bg-[radial-gradient(circle_at_30%_50%,white_1px,transparent_1px)]' 
              : 'bg-[radial-gradient(circle_at_70%_50%,#002FA7_1px,transparent_1px)]'
            }`}
            style={{
              backgroundSize: '8px 8px',
            }}
            animate={{
              x: [0, 8, 0],
              y: [0, 4, 0],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: "linear",
            }}
          />
          
          {isWaveform ? (
            <div className="flex items-center gap-3 relative z-10">
              <div className="flex items-end justify-center space-x-[1.5px] h-7 flex-1">
                {bars.map((bar, index) => (
                  <motion.div
                    key={bar.id}
                    initial={{ height: 4 }}
                    animate={{ 
                      height: [4, bar.height, 4],
                    }}
                    transition={{
                      duration: 0.6,
                      delay: bar.delay,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                    className={`rounded-full ${
                      isAI 
                        ? 'bg-white shadow-[0_0_4px_rgba(255,255,255,0.6)]' 
                        : 'bg-klein shadow-[0_0_4px_rgba(0,47,167,0.4)]'
                    }`}
                    style={{
                      width: index % 3 === 0 ? '3px' : '2px',
                      minHeight: '4px',
                    }}
                  />
                ))}
              </div>
              {showHint && onClick && (
                <motion.div
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-1.5 text-[8px] font-black uppercase tracking-wider text-klein/80 group-hover:text-klein transition-colors"
                >
                  <Sparkles size={10} className="animate-pulse" />
                  <span className="relative">
                    TAP
                    <motion.span
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="absolute -right-1 top-0"
                    >
                      _
                    </motion.span>
                  </span>
                </motion.div>
              )}
            </div>
          ) : (
            <p className={`text-sm font-bold relative z-10 ${isAI ? 'text-white' : 'text-klein'}`}>
              {text}
            </p>
          )}
        </div>
      </motion.div>
      <motion.div 
        className={`mt-2 text-[8px] font-black uppercase tracking-widest ${
          isAI ? 'text-blue-300/60' : 'text-baby/60'
        }`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {isAI ? 'Q: AI老师' : 'A: 你'}
      </motion.div>
    </motion.div>
  );
};


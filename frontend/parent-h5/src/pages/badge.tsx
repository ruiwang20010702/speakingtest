import React from 'react';
import { motion } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { useReport } from '@/context/ReportContext';
import { Star } from 'lucide-react';

const getBadgeTitle = (starLevel: number): string => {
  if (starLevel >= 5) return '口语小达人';
  if (starLevel >= 4) return '语言之星';
  if (starLevel >= 3) return '进步之星';
  if (starLevel >= 2) return '勤学小将';
  return '成长新星';
};

const getBadgeMessage = (starLevel: number): string => {
  if (starLevel >= 5) return '你是天生的演说家！';
  if (starLevel >= 4) return '表现非常出色！';
  if (starLevel >= 3) return '继续加油，更上一层楼！';
  if (starLevel >= 2) return '有进步，继续努力！';
  return '迈出了第一步，棒棒哒！';
};

export const BadgePage: React.FC = () => {
  const { data, isLoading } = useReport();
  
  const starLevel = data?.overall?.star_level || 0;
  const studentName = data?.student?.name || '学生';

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-6 relative overflow-hidden pointer-events-auto">
      
      {/* Background Burst */}
      <motion.div 
        className="absolute inset-0 z-0 flex items-center justify-center opacity-20"
        animate={{ rotate: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
      >
         <div className="w-[150vmax] h-[150vmax] relative">
            {Array.from({ length: 12 }).map((_, i) => (
              <div 
                key={i}
                className="absolute top-1/2 left-1/2 w-full h-12 bg-white origin-left"
                style={{ transform: `translateY(-50%) rotate(${i * 30}deg)` }}
              />
            ))}
         </div>
      </motion.div>

      {/* Confetti */}
      {Array.from({ length: 20 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute z-10 w-3 h-3 bg-baby rounded-sm"
          style={{
             top: `${Math.random() * 100}%`,
             left: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, 100],
            rotate: [0, 360],
            opacity: [1, 0]
          }}
          transition={{
            duration: 2 + Math.random() * 2,
            repeat: Infinity,
            ease: "linear",
            delay: Math.random() * 2
          }}
        />
      ))}

      {/* Main Badge */}
      <motion.div 
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
        className="relative z-20 flex flex-col items-center"
      >
        <div className="relative">
          {/* Badge Shape */}
          <div className="w-64 h-64 bg-baby rounded-full border-4 border-white flex items-center justify-center shadow-[0px_0px_40px_rgba(255,245,157,0.4)]">
             <div className="w-56 h-56 rounded-full flex items-center justify-center overflow-hidden">
                <Monkey variant="winner" layoutId="monkey" className="w-48 h-48 mt-8" imageSrc="/5.gif" />
             </div>
          </div>
          
          {/* Ribbon */}
          <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 w-64 bg-klein border-2 border-baby py-2 text-center shadow-lg transform skew-x-[-10deg]">
             <span className="text-baby font-black text-lg tracking-wider block transform skew-x-[10deg]">{getBadgeTitle(starLevel)}</span>
          </div>
        </div>

        <div className="mt-12 text-center space-y-2">
          <h2 className="text-3xl font-black text-white">恭喜 {studentName}!</h2>
          <p className="text-white/80">{getBadgeMessage(starLevel)}</p>
        </div>

        {/* CTA Button */}
        <motion.button
          whileHover={{ scale: 1.05, x: 4, y: 4 }}
          whileTap={{ scale: 0.95 }}
          className="mt-8 px-8 py-3 bg-baby text-klein font-black text-lg rounded-full border-2 border-white shadow-[4px_4px_0px_rgba(255,255,255,1)] hover:shadow-none transition-all"
          onPointerDown={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
        >
          分享荣耀
        </motion.button>

        {/* Star Rating */}
        <div className="flex mt-6 space-x-2">
           {[1,2,3,4,5].map((s) => (
             <motion.div
               key={s}
               initial={{ scale: 0 }}
               animate={{ scale: 1 }}
               transition={{ delay: 0.5 + s * 0.1 }}
             >
               <Star className={`w-6 h-6 ${s <= starLevel ? 'text-baby fill-baby' : 'text-white/30'}`} />
             </motion.div>
           ))}
        </div>

      </motion.div>
    </div>
  );
};

import React from 'react';
import { motion } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { useReport } from '@/context/ReportContext';
import { ArrowUpRight } from 'lucide-react';

export const Cover: React.FC = () => {
  const { data, isLoading } = useReport();
  
  // Extract student name or use default
  const studentName = data?.student?.name || '学生';
  const level = data?.student?.level || 'L0';
  const starLevel = data?.overall?.star_level || 0;
  
  // Split name for display (support both Chinese and English)
  const displayName = studentName.length > 6 
    ? studentName.slice(0, 6) 
    : studentName;

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative bg-klein overflow-hidden flex flex-col items-center">
      
      {/* 1. The Masthead (Behind Monkey) */}
      <div className="absolute top-[8%] w-full flex justify-center z-0">
         <motion.h1 
           initial={{ y: -100, opacity: 0 }}
           animate={{ y: 0, opacity: 1 }}
           transition={{ duration: 0.8, ease: "circOut" }}
           className="text-[18vw] font-black text-white leading-[0.85] tracking-tighter select-none opacity-20 text-center"
         >
           TEST<br/>REPORT
         </motion.h1>
      </div>

      {/* 2. Top Meta Data (Issue No, Date) */}
      <div className="absolute top-0 w-full p-6 flex justify-between items-end z-20 mix-blend-overlay">
         <div className="flex flex-col">
            <span className="text-[10px] font-bold tracking-widest text-white border-b border-white pb-1 mb-1">测评日期 TEST DATE</span>
            <span className="text-xl font-bold text-white">{new Date().getFullYear()}</span>
         </div>
         <div className="flex flex-col text-right">
            <span className="text-[10px] font-bold tracking-widest text-white border-b border-white pb-1 mb-1">等级 LEVEL</span>
            <span className="text-xl font-bold text-white">{level}</span>
         </div>
      </div>

      {/* 3. The Hero (Monkey) */}
      <motion.div 
        initial={{ scale: 0.8, opacity: 0, y: 50 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
        className="absolute top-[12%] z-10 w-full flex justify-center"
      >
        <div className="relative">
           {/* Abstract Circle Halo behind monkey */}
           <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[80vw] h-[80vw] max-w-[720px] max-h-[720px] bg-baby rounded-full blur-[60px] opacity-20" />
           
           <Monkey variant="winner" layoutId="monkey" className="w-[700px] h-[700px] drop-shadow-2xl" imageSrc={`${import.meta.env.BASE_URL}gif/1.gif`} />
           
           {/* Floating Star Badge */}
           <motion.div 
             initial={{ scale: 0 }}
             animate={{ scale: 1 }}
             transition={{ delay: 1.2, type: "spring" }}
             className="absolute bottom-4 right-4 md:right-0 bg-baby text-klein w-24 h-24 rounded-full flex flex-col items-center justify-center border-4 border-white shadow-xl rotate-12 hover:rotate-0 transition-transform cursor-pointer"
           >
              <span className="text-xs font-bold">星级</span>
              <div className="flex items-center">
                <span className="text-4xl font-black leading-none">{starLevel}</span>
                <span className="text-lg font-bold ml-0.5">★</span>
              </div>
           </motion.div>
        </div>
      </motion.div>

      {/* 4. The Headlines (Foreground Text) */}
      <div className="absolute bottom-0 w-full h-[35%] z-20 flex flex-col justify-end p-6 pb-12">
         
         {/* Teaser Line */}
         <motion.div 
           initial={{ x: -50, opacity: 0 }}
           animate={{ x: 0, opacity: 1 }}
           transition={{ delay: 0.6 }}
           className="flex items-center space-x-2 mb-4"
         >
            <div className="bg-baby text-klein text-[10px] font-bold px-2 py-0.5">口语测评报告 ORAL TEST</div>
         </motion.div>

         {/* Main Name Headline */}
         <motion.div
           initial={{ y: 50, opacity: 0 }}
           animate={{ y: 0, opacity: 1 }}
           transition={{ delay: 0.8 }}
         >
            <h2 className="text-5xl md:text-8xl font-black text-white leading-[0.9] tracking-tighter mb-2">
               <span className="text-baby">{displayName}</span>
            </h2>
            <p className="text-white/60 text-sm font-bold">的口语能力分析报告</p>
         </motion.div>

         {/* Bottom Footer / Barcode Area - 添加 flex-wrap 支持换行 */}
         <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="w-full border-t border-white/30 mt-6 pt-4 flex flex-wrap justify-between items-end gap-3"
         >
            <div className="flex items-center text-white/60 space-x-3 min-w-0 flex-shrink">
               <ArrowUpRight className="w-5 h-5 flex-shrink-0" />
               <span className="text-[11px] leading-tight">
                  深度解析语言潜力，<br/>见证每一次发声的蜕变。
               </span>
            </div>

            {/* Total Score */}
            <motion.div 
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 1.8, type: "spring" }}
              className="flex flex-col items-end flex-shrink-0"
            >
               <span className="text-[7px] font-bold text-white/40 uppercase tracking-widest">总分 SCORE</span>
               <div className="flex items-baseline">
                 <span className="text-3xl font-black text-baby">{Math.round(data?.overall?.total_score || 0)}</span>
                 <span className="text-base font-bold text-white/40 ml-1">/100</span>
               </div>
            </motion.div>
         </motion.div>

      </div>
      
      {/* Decorative vertical lines */}
      <div className="absolute top-0 bottom-0 left-6 w-px bg-white/10 z-0"></div>
      <div className="absolute top-0 bottom-0 right-6 w-px bg-white/10 z-0"></div>

    </div>
  );
};

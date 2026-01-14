import React from 'react';
import { motion } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { useReport } from '@/context/ReportContext';
import { MessageCircle, Zap, Star, AlertCircle, CheckCircle2, Trophy, Info, Mic2, HelpCircle } from 'lucide-react';

const BubbleBackground: React.FC = () => {
  const bubbles = Array.from({ length: 20 });
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {bubbles.map((_, i) => {
        const size = Math.random() * 60 + 20;
        const initialX = Math.random() * 100;
        const duration = 10 + Math.random() * 15;
        const delay = Math.random() * 10;
        
        return (
          <motion.div
            key={i}
            initial={{ 
              y: '110%', 
              x: `${initialX}%`, 
              opacity: 0,
              scale: Math.random() * 0.5 + 0.5 
            }}
            animate={{ 
              y: '-20%', 
              opacity: [0, 0.4, 0.4, 0],
              x: [`${initialX}%`, `${initialX + (Math.random() * 10 - 5)}%`],
            }}
            transition={{
              duration: duration,
              repeat: Infinity,
              delay: delay,
              ease: "linear"
            }}
            className="absolute rounded-full border-2 border-white/20 bg-white/5 backdrop-blur-[1px]"
            style={{
              width: `${size}px`,
              height: `${size}px`,
            }}
          />
        );
      })}
    </div>
  );
};

const Waveform: React.FC<{ color: string; speed: number; count: number; jitter: boolean }> = ({ color, speed, count, jitter }) => {
  const bars = Array.from({ length: count });
  return (
    <div className="flex items-end justify-center space-x-[1.5px] h-8 w-full px-2">
      {bars.map((_, i) => (
        <motion.div
          key={i}
          initial={{ height: 4 }}
          animate={{ 
            height: [4, jitter ? (Math.random() * 18 + 4) : (Math.random() * 28 + 8), 4] 
          }}
          transition={{
            duration: speed + (jitter ? Math.random() * 0.4 : 0),
            repeat: Infinity,
            delay: i * 0.02,
            ease: "easeInOut"
          }}
          className="w-1 rounded-full"
          style={{ backgroundColor: color }}
        />
      ))}
    </div>
  );
};

const PerformanceCard: React.FC<{
  type: 'best' | 'needs-work';
  title: string;
  question: string;
  studentAnswer: string;
  score: string;
  comment: string;
  index: number;
}> = ({ type, title, question, studentAnswer, score, comment, index }) => {
  const isBest = type === 'best';
  
  return (
    <motion.div
      initial={{ x: isBest ? -30 : 30, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: 0.2 + index * 0.2, type: 'spring' }}
      className={`relative w-full border-2 border-black rounded-2xl p-3 shadow-[4px_4px_0px_#000] overflow-hidden z-20 ${isBest ? 'bg-white' : 'bg-white/95'}`}
    >
      <div className={`absolute top-0 left-0 px-3 py-0.5 rounded-br-xl border-b border-r border-black font-black text-[9px] uppercase tracking-tighter z-30 ${isBest ? 'bg-green-400 text-black' : 'bg-orange-400 text-black'}`}>
        {isBest ? '✦ 最佳表现' : '⚠ 待加强项'}
      </div>

      <motion.div 
        initial={{ scale: 0, rotate: -20 }}
        animate={{ scale: 1, rotate: 12 }}
        transition={{ delay: 0.6 + index * 0.2, type: "spring" }}
        className={`absolute top-1 right-2 w-10 h-10 rounded-full border-2 border-black flex items-center justify-center shadow-md z-30 ${isBest ? 'bg-baby' : 'bg-white'}`}
      >
        <span className="text-lg font-black text-klein italic leading-none">{score}</span>
      </motion.div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center space-x-1.5">
          {isBest ? <Trophy size={12} className="text-yellow-600" /> : <Info size={12} className="text-orange-600" />}
          <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">{title}</span>
        </div>
        
        <div className="space-y-1.5">
          <div className="flex items-start space-x-1.5 bg-klein/5 p-1.5 rounded-lg border border-dashed border-klein/10">
            <HelpCircle size={10} className="text-klein/40 mt-0.5 shrink-0" />
            <p className="text-[9px] font-bold text-klein/60 leading-tight">
              <span className="opacity-50 uppercase mr-1 text-[7px]">Q:</span>{question}
            </p>
          </div>
          
          <div className="flex items-start space-x-1.5 bg-baby/20 p-1.5 rounded-lg border border-black/5">
            <Mic2 size={10} className="text-klein mt-0.5 shrink-0" />
            <p className="text-[10px] font-black text-klein leading-tight italic">
              <span className="opacity-40 uppercase mr-1 text-[7px]">A:</span>"{studentAnswer}"
            </p>
          </div>
        </div>

        <div className="relative py-1 bg-gray-50/50 rounded-xl border border-black/5">
          <Waveform 
            color={isBest ? '#002FA7' : '#E67E22'} 
            speed={isBest ? 0.8 : 1.2} 
            count={36} 
            jitter={!isBest} 
          />
        </div>

        <div className="flex items-start space-x-1.5 pt-0.5 border-t border-black/5">
           {isBest ? <CheckCircle2 size={12} className="text-green-500 mt-0.5 shrink-0" /> : <AlertCircle size={12} className="text-orange-500 mt-0.5 shrink-0" />}
           <p className={`text-[9px] font-bold leading-tight ${isBest ? 'text-green-700' : 'text-orange-700'}`}>
             {comment}
           </p>
        </div>
      </div>
    </motion.div>
  );
};

export const DialoguePage: React.FC = () => {
  const { data, isLoading } = useReport();

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  const bestSample = data?.part2?.best_sample;
  const weakSample = data?.part2?.weak_sample;

  return (
    <div className="w-full h-full flex flex-col relative bg-klein overflow-hidden select-none px-5 pt-8 pb-4">
      
      <BubbleBackground />

      <div className="absolute inset-0 opacity-10 pointer-events-none z-0">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(#fff_1.2px,transparent_1.2px)] bg-[length:20px_20px]" />
      </div>

      <div className="relative z-30 mb-4">
        <motion.div 
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="inline-flex items-center space-x-1.5 bg-baby px-2 py-0.5 rounded-sm border-[1.5px] border-black shadow-[2px_2px_0px_#000]"
        >
          <MessageCircle size={10} className="text-klein fill-klein" />
          <span className="text-[8px] font-black text-klein uppercase tracking-widest">语音实录对比</span>
        </motion.div>
        <motion.h2 
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-3xl font-black text-white italic tracking-tighter mt-2 leading-none"
        >
          对话<span className="text-baby">能力表现</span>
        </motion.h2>
      </div>

      <div className="flex-1 flex flex-col justify-center space-y-4 relative z-20">
        {bestSample ? (
          <PerformanceCard 
            type="best"
            index={0}
            title={`最佳样本 #${String(bestSample.question_no).padStart(2, '0')}`}
            question={bestSample.question}
            studentAnswer={bestSample.answer || "未录入"}
            score={bestSample.score}
            comment={bestSample.feedback}
          />
        ) : (
          <PerformanceCard 
            type="best"
            index={0}
            title="最佳样本"
            question="暂无数据"
            studentAnswer="暂无数据"
            score="-"
            comment="暂无最佳表现样本"
          />
        )}

        <div className="flex justify-center -my-2 relative z-30">
           <div className="bg-baby border-[1.5px] border-black px-3 py-1 rounded-full shadow-[2px_2px_0px_#000] flex items-center space-x-1.5 scale-90">
              <Zap size={10} className="text-klein fill-klein" />
              <span className="text-[8px] font-black text-klein uppercase tracking-widest">VS 对比分析</span>
           </div>
        </div>

        {weakSample ? (
          <PerformanceCard 
            type="needs-work"
            index={1}
            title={`提升样本 #${String(weakSample.question_no).padStart(2, '0')}`}
            question={weakSample.question}
            studentAnswer={weakSample.answer || "未录入"}
            score={weakSample.score}
            comment={weakSample.feedback}
          />
        ) : (
          <PerformanceCard 
            type="needs-work"
            index={1}
            title="提升样本"
            question="暂无数据"
            studentAnswer="暂无数据"
            score="-"
            comment="暂无待提升样本"
          />
        )}
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="absolute bottom-[-2%] right-[-5%] pointer-events-none z-[60]"
      >
        <div className="relative">
          <Monkey variant="glasses" layoutId="monkey" className="w-56 h-56 drop-shadow-[0_10px_10px_rgba(0,0,0,0.3)]" />
        </div>
      </motion.div>

      <div className="mt-4 flex items-center justify-between opacity-30 px-2 shrink-0 relative z-10">
         <div className="h-[1px] flex-1 bg-white" />
         <div className="flex space-x-1 px-3">
           {[1,2,3].map(i => <Star key={i} size={6} className="text-white fill-white" />)}
         </div>
         <span className="text-[7px] font-mono tracking-[0.2em] text-white whitespace-nowrap uppercase">Voice Intelligence v2.0</span>
         <div className="flex space-x-1 px-3">
           {[1,2,3].map(i => <Star key={i} size={6} className="text-white fill-white" />)}
         </div>
         <div className="h-[1px] flex-1 bg-white" />
      </div>
    </div>
  );
};

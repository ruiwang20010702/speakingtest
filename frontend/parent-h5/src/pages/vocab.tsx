import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { useReport } from '@/context/ReportContext';
import { Star, Flame, Activity, ShieldCheck } from 'lucide-react';

interface ExtendedVocabWord {
  text: string;
  status: 'perfect' | 'unclear' | 'failed';
  statusText: string;
}

const getStatusText = (status: 'perfect' | 'unclear' | 'failed'): string => {
  switch (status) {
    case 'perfect': return '完美';
    case 'unclear': return '模糊';
    case 'failed': return '未学';
    default: return '完美';
  }
};

const getStatusColor = (status: 'perfect' | 'unclear' | 'failed') => {
  switch (status) {
    case 'perfect': return '#2ECC71';
    case 'unclear': return '#F39C12';
    case 'failed': return '#E74C3C';
    default: return '#fff';
  }
};

// 单词卡片周围的气泡组件
const WordBubbles: React.FC = () => {
  const bubbles = Array.from({ length: 8 });
  return (
    <div className="absolute inset-0 pointer-events-none overflow-visible">
      {bubbles.map((_, i) => {
        const angle = (i / bubbles.length) * Math.PI * 2;
        const radius = 40 + Math.random() * 20;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const size = 4 + Math.random() * 6;
        const delay = Math.random() * 2;
        const duration = 2 + Math.random() * 2;
        
        return (
          <motion.div
            key={i}
            initial={{ 
              x: 0, 
              y: 0, 
              opacity: 0,
              scale: 0
            }}
            animate={{ 
              x: x + (Math.random() - 0.5) * 10,
              y: y + (Math.random() - 0.5) * 10,
              opacity: [0, 0.6, 0.6, 0],
              scale: [0, 1, 1, 0]
            }}
            transition={{
              duration: duration,
              repeat: Infinity,
              delay: delay,
              ease: "easeInOut"
            }}
            className="absolute rounded-full border border-white/40 bg-white/20"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              left: '50%',
              top: '50%',
            }}
          />
        );
      })}
    </div>
  );
};

const WordCard: React.FC<{ word: ExtendedVocabWord; index: number }> = ({ word, index }) => {
  const statusBg = getStatusColor(word.status);
  
  // 固定的初始位置参数（确保每次刷新都一致）
  const rotationPattern = [-5, 3, -2, 4, -3, 2, -4, 1, -1, 5, -3, 2, -5, 4, -2, 3, -4, 1];
  const scalePattern = [1.05, 0.95, 1.0, 0.98, 1.03, 0.97];
  const xOffsetPattern = [5, -8, 3, -5, 7, -3, 9, -7, 4, -6, 8, -4, 6, -9, 2, -2, 10, -10];
  
  const fixedRotation = rotationPattern[index % rotationPattern.length];
  const fixedScale = scalePattern[index % scalePattern.length];
  
  // 计算固定的水平位置
  let fixedXOffset = 0;
  if (index === 18 || index === 19) {
    fixedXOffset = 50; // 最后一排向右移动50px
  } else if (index < xOffsetPattern.length) {
    fixedXOffset = xOffsetPattern[index];
  }
  
  return (
    <motion.div
      drag
      dragConstraints={{ left: -100, right: 100, top: -100, bottom: 100 }}
      dragElastic={0.1}
      initial={{ opacity: 0, scale: 0.5, y: 20, rotate: 0, x: 0 }}
      animate={{ opacity: 1, scale: fixedScale, y: 0, rotate: fixedRotation, x: fixedXOffset }}
      transition={{ 
        type: "spring",
        stiffness: 260,
        damping: 20,
        delay: index * 0.04 
      }}
      whileHover={{ scale: fixedScale * 1.05, rotate: fixedRotation + (index % 2 === 0 ? 2 : -2) }}
      whileDrag={{ scale: fixedScale * 1.1, rotate: 0, cursor: 'grabbing' }}
      className={`relative h-full w-[calc(100%-30px)] mx-auto cursor-grab ${word.status === 'failed' ? 'opacity-50' : 'opacity-100'}`}
    >
      <div className="bg-white border-[1.5px] border-black rounded-lg shadow-[3px_3px_0px_rgba(0,0,0,1)] flex flex-col items-center justify-center h-full relative overflow-visible px-1 group pt-2">
        {/* 单词卡片周围的气泡 */}
        <WordBubbles />
        
        <div 
          className="absolute top-0 right-0 px-0.5 py-0.5 rounded-bl-md border-l border-b border-black/10 z-10"
          style={{ backgroundColor: statusBg }}
        >
          <span className="text-[5px] font-black text-white leading-none whitespace-nowrap">
            {word.statusText}
          </span>
        </div>
        <span className="text-klein font-black italic tracking-tighter text-[12px] leading-tight text-center break-words w-full relative z-10">
          {word.text}
        </span>
      </div>
    </motion.div>
  );
};

export const VocabPage: React.FC = () => {
  const { data, isLoading } = useReport();
  
  // Transform data from API to display format
  const words: ExtendedVocabWord[] = useMemo(() => {
    if (!data?.part1?.words) return [];
    return data.part1.words.map(w => ({
      text: w.text,
      status: w.status,
      statusText: getStatusText(w.status)
    }));
  }, [data?.part1?.words]);
  
  // Calculate stats
  const stats = useMemo(() => {
    if (!words.length) return { masteryRate: 0, starLevel: 0 };
    const perfectCount = words.filter(w => w.status === 'perfect').length;
    const masteryRate = Math.round((perfectCount / words.length) * 100);
    const starLevel = masteryRate >= 90 ? 5 : masteryRate >= 75 ? 4 : masteryRate >= 60 ? 3 : masteryRate >= 40 ? 2 : 1;
    return { masteryRate, starLevel };
  }, [words]);

  // 计算需要多少行（每行3列）
  const rows = Math.ceil(words.length / 3);

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col relative bg-klein overflow-hidden select-none px-4 pt-6 pb-6">
      
      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 z-0 opacity-5 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(#fff_1px,transparent_1px)] bg-[length:20px_20px]" />
      </div>

      <div className="relative z-20 flex justify-between items-start mb-2 px-2">
        <div className="space-y-0">
          <motion.div 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="inline-flex items-center space-x-1.5 bg-baby px-2 py-0.5 rounded border border-black shadow-[1px_1px_0px_rgba(0,0,0,1)]"
          >
            <Flame size={10} className="text-klein fill-klein" />
            <span className="text-[9px] font-black text-klein uppercase tracking-widest">词汇能量</span>
          </motion.div>
          <motion.h2 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-4xl font-black text-white italic tracking-tighter leading-tight"
          >
            能量词汇站
          </motion.h2>
          <motion.p 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-[10px] font-bold text-baby/80 tracking-wide mt-0.5"
          >
            让每一个单词都充满成长的能量
          </motion.p>
        </div>

        <motion.div
          initial={{ y: -50, opacity: 0, rotate: 10 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          transition={{ type: "spring", delay: 0.3 }}
          className="relative -mt-4"
        >
          <Monkey variant="glasses" layoutId="monkey" className="w-20 h-20 drop-shadow-2xl" imageSrc="/3.gif" />
        </motion.div>
      </div>

      <div className="relative z-10 flex-1 overflow-visible mt-[60px] mb-3 h-[500px]">
        <div className="grid grid-cols-3 gap-2.5 auto-rows-[50px]">
          {words.map((word, i) => (
            <WordCard key={i} word={word} index={i} />
          ))}
        </div>
      </div>

      <div className="relative z-20 mt-4">
        <div className="w-full h-px bg-white/20 mb-4" />
        
        <div className="flex items-end justify-between">
          <div className="flex flex-col space-y-3">
            <div className="flex items-center space-x-4">
              <div className="flex flex-col">
                <div className="flex items-center space-x-1 text-baby/60 mb-0.5">
                   <Activity size={10} />
                   <span className="text-[8px] font-black uppercase tracking-widest">出现频率</span>
                </div>
                <span className="text-lg font-black text-white italic leading-none">{words.length}<span className="text-baby/40 text-xs ml-1 font-mono">次</span></span>
              </div>
              <div className="w-px h-8 bg-white/10" />
              <div className="flex flex-col">
                <div className="flex items-center space-x-1 text-baby/60 mb-0.5">
                   <ShieldCheck size={10} />
                   <span className="text-[8px] font-black uppercase tracking-widest">发音质量</span>
                </div>
                <span className="text-lg font-black text-white italic leading-none">
                  {stats.masteryRate >= 80 ? '优秀' : stats.masteryRate >= 60 ? '良好' : '加油'}
                </span>
              </div>
            </div>
            
            <div className="flex space-x-1">
               {Array.from({ length: 5 }).map((_, i) => (
                 <div key={i} className={`h-1 rounded-full ${i < Math.round(stats.masteryRate / 20) ? 'w-4 bg-baby' : 'w-1 bg-white/10'}`} />
               ))}
            </div>
          </div>

          <motion.div 
            initial={{ scale: 0, rotate: -5 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", delay: 1.2 }}
            className="bg-white border-2 border-black p-1 rounded-2xl shadow-[6px_6px_0px_#FFF59D] flex items-stretch"
          >
            <div className="bg-klein text-white px-4 py-2 rounded-xl flex flex-col justify-center items-center">
              <span className="text-[8px] font-black text-white/40 uppercase leading-none mb-1">词汇掌握率</span>
              <div className="flex items-baseline leading-none">
                <span className="text-3xl font-black italic tracking-tighter">{stats.masteryRate}</span>
                <span className="text-xs font-black ml-0.5 opacity-50">%</span>
              </div>
            </div>
            <div className="px-3 flex flex-col justify-center space-y-1">
              <div className="flex space-x-0.5">
                {[1, 2, 3, 4, 5].map(i => (
                  <Star key={i} size={12} className={i <= stats.starLevel ? "text-klein fill-klein" : "text-klein/10"} strokeWidth={3} />
                ))}
              </div>
              <span className="text-[7px] font-black text-klein/40 text-center uppercase tracking-tighter">
                {stats.starLevel >= 4 ? '黄金等级' : stats.starLevel >= 3 ? '白银等级' : '青铜等级'}
              </span>
            </div>
          </motion.div>
        </div>

        <div className="mt-6 flex justify-between items-center opacity-20">
           <div className="h-[2px] w-12 bg-white" />
           <span className="text-[8px] font-mono tracking-[0.5em] text-white">声航核心技术版本 v2.5</span>
           <div className="h-[2px] w-12 bg-white" />
        </div>
      </div>
    </div>
  );
};

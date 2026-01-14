import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { WordStatus as WordStatusType } from '@/types';
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
const WordBubbles: React.FC<{ index: number }> = ({ index }) => {
  const seed = index * 1000;
  const random = (offset: number) => {
    const x = Math.sin(seed + offset) * 10000;
    return x - Math.floor(x);
  };
  
  const bubbleCount = 2 + Math.floor(random(1) * 2);
  const bubbles = Array.from({ length: bubbleCount }, (_, i) => ({
    id: `${index}-${i}`,
    startX: (random(i * 10) - 0.5) * 150,
    endX: (random(i * 10 + 5) - 0.5) * 150,
    startY: random(i * 10 + 1) * 80 + 10,
    size: random(i * 10 + 2) * 12 + 6,
    duration: 4 + random(i * 10 + 3) * 6,
    delay: random(i * 10 + 4) * 2,
  }));

  return (
    <>
      {bubbles.map((bubble) => (
        <motion.div
          key={bubble.id}
          initial={{ 
            bottom: `${bubble.startY}px`,
            left: `50%`,
            x: `${bubble.startX}px`,
            opacity: 0 
          }}
          animate={{ 
            bottom: `${bubble.startY + 100}px`,
            opacity: [0, 0.5, 0.5, 0],
            x: `${bubble.endX}px`
          }}
          transition={{
            duration: bubble.duration,
            repeat: Infinity,
            delay: bubble.delay,
            ease: "easeOut"
          }}
          className="absolute rounded-full border border-white/40 bg-white/15 pointer-events-none"
          style={{
            width: `${bubble.size}px`,
            height: `${bubble.size}px`,
            transform: 'translateX(-50%)',
          }}
        />
      ))}
    </>
  );
};

type CardSize = 'small' | 'medium' | 'large';

interface CardPosition {
  left: string;
  top: string;
  rotate: number;
  scale: number;
  size: CardSize;
  width: string;
  height: string;
}

const generateCardPositions = (total: number): CardPosition[] => {
  const positions: CardPosition[] = [];
  const usedAreas: Array<{ x: number; y: number; width: number; height: number }> = [];
  
  const random = (index: number, offset: number) => {
    const seed = index * 137.508 + offset;
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };
  
  const checkOverlap = (x: number, y: number, width: number, height: number): boolean => {
    const padding = 1.5;
    for (const area of usedAreas) {
      if (
        x < area.x + area.width + padding &&
        x + width + padding > area.x &&
        y < area.y + area.height + padding &&
        y + height + padding > area.y
      ) {
        return true;
      }
    }
    return false;
  };
  
  for (let i = 0; i < total; i++) {
    const sizeType: CardSize = 'medium';
    const scale = 1.0;
    const baseWidth = 22;
    const baseHeight = 9;
    
    const col = i % 3;
    const row = Math.floor(i / 3);
    const totalRows = Math.ceil(total / 3);
    
    const gridWidth = 98;
    const gridLeft = -8;
    const gridTop = -1;
    const gridBottom = 1;
    const availableHeight = 100 - gridTop - gridBottom;
    
    const colOffset = (random(i, 500) - 0.5) * 5;
    let baseX = gridLeft + (col + 0.5) * (gridWidth / 3) + colOffset;
    const rowSpacing = availableHeight / totalRows;
    let baseY = gridTop + row * rowSpacing + rowSpacing * 0.5;
    
    let finalX = baseX;
    let finalY = baseY;
    let attempts = 0;
    const maxAttempts = 60;
    
    const leftMargin = -8;
    const topMargin = -3;
    const rightMargin = 0.5;
    const bottomMargin = 0.5;
    
    let foundPosition = false;
    
    while (attempts < maxAttempts && !foundPosition) {
      const offsetRangeX = 12;
      const offsetRangeY = 10;
      
      const offsetX = (random(i, attempts * 2) - 0.5) * offsetRangeX;
      const offsetY = (random(i, attempts * 2 + 1) - 0.5) * offsetRangeY;
      
      const testX = baseX + offsetX;
      const testY = baseY + offsetY;
      
      const cardLeft = testX - baseWidth / 2;
      const cardTop = testY - baseHeight / 2;
      
      if (
        cardLeft >= leftMargin &&
        cardLeft + baseWidth <= 100 - rightMargin &&
        cardTop >= topMargin &&
        cardTop + baseHeight <= 100 - bottomMargin
      ) {
        if (!checkOverlap(cardLeft, cardTop, baseWidth, baseHeight)) {
          finalX = testX;
          finalY = testY;
          foundPosition = true;
        }
      }
      attempts++;
    }
    
    if (!foundPosition) {
      finalX = baseX;
      finalY = baseY;
    }
    
    const rotationRange = 15;
    const rotation = (random(i, 100) - 0.5) * rotationRange;
    
    usedAreas.push({
      x: finalX - baseWidth / 2,
      y: finalY - baseHeight / 2,
      width: baseWidth,
      height: baseHeight,
    });
    
    positions.push({
      left: `${finalX}%`,
      top: `${finalY}%`,
      rotate: rotation,
      scale: scale,
      size: sizeType,
      width: `${baseWidth}%`,
      height: `${baseHeight}%`,
    });
  }
  
  return positions;
};

const WordCard: React.FC<{ word: ExtendedVocabWord; index: number; positions: CardPosition[] }> = ({ word, index, positions }) => {
  const statusBg = getStatusColor(word.status);
  const position = positions[index];
  
  if (!position) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5, y: 20 }}
      animate={{ 
        opacity: 1, 
        scale: position.scale,
        y: 0,
        rotate: position.rotate,
      }}
      transition={{ 
        type: "spring",
        stiffness: 260,
        damping: 20,
        delay: index * 0.04 
      }}
      whileHover={{ scale: position.scale * 1.1, rotate: position.rotate + (index % 2 === 0 ? 2 : -2) }}
      className={`absolute ${word.status === 'failed' ? 'opacity-50' : 'opacity-100'}`}
      style={{
        left: position.left,
        top: position.top,
        transform: 'translate(-50%, -50%)',
        width: position.width,
        height: position.height,
      }}
    >
      <WordBubbles index={index} />
      
      <div className="bg-white border-[1.5px] border-black rounded-lg shadow-[3px_3px_0px_rgba(0,0,0,1)] flex flex-col items-center justify-center h-full relative overflow-hidden px-1 group">
        <div 
          className="absolute top-0 right-0 px-0.5 py-0.25 rounded-bl-sm border-l border-b border-black/10 z-10"
          style={{ backgroundColor: statusBg }}
        >
          <span className="text-[5px] font-black text-white leading-none whitespace-nowrap">
            {word.statusText}
          </span>
        </div>
        <span className="text-klein font-black italic tracking-tighter text-[13px] leading-tight text-center break-words w-full mt-1 pr-2">
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
  
  // Generate positions based on actual word count
  const cardPositions = useMemo(() => generateCardPositions(words.length), [words.length]);
  
  // Calculate stats
  const stats = useMemo(() => {
    if (!words.length) return { masteryRate: 0, starLevel: 0 };
    const perfectCount = words.filter(w => w.status === 'perfect').length;
    const masteryRate = Math.round((perfectCount / words.length) * 100);
    const starLevel = masteryRate >= 90 ? 5 : masteryRate >= 75 ? 4 : masteryRate >= 60 ? 3 : masteryRate >= 40 ? 2 : 1;
    return { masteryRate, starLevel };
  }, [words]);

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
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="relative -mt-4"
        >
          <Monkey variant="glasses" layoutId="monkey" className="w-20 h-20 drop-shadow-2xl" />
        </motion.div>
      </div>

      <div className="relative z-10 flex-1 overflow-hidden my-3">
        <div className="relative w-full h-full">
          {words.map((word, i) => (
            <WordCard key={i} word={word} index={i} positions={cardPositions} />
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
                   <span className="text-[8px] font-black uppercase tracking-widest">单词数量</span>
                </div>
                <span className="text-lg font-black text-white italic leading-none">{words.length}<span className="text-baby/40 text-xs ml-1 font-mono">个</span></span>
              </div>
              <div className="w-px h-8 bg-white/10" />
              <div className="flex flex-col">
                <div className="flex items-center space-x-1 text-baby/60 mb-0.5">
                   <ShieldCheck size={10} />
                   <span className="text-[8px] font-black uppercase tracking-widest">发音质量</span>
                </div>
                <span className="text-lg font-black text-white italic leading-none">{stats.masteryRate >= 80 ? '优秀' : stats.masteryRate >= 60 ? '良好' : '加油'}</span>
              </div>
            </div>
            
            <div className="flex space-x-1">
               {Array.from({ length: 12 }).map((_, i) => (
                 <div key={i} className={`h-1 rounded-full ${i < Math.round(stats.masteryRate / 10) ? 'w-4 bg-baby' : 'w-1 bg-white/10'}`} />
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
      </div>
    </div>
  );
};

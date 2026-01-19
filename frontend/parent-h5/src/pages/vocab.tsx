import React, { useMemo, useRef, useState, useEffect } from 'react';
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

// 获取基于状态的卡片背景色
const getCardBgColor = (status: 'perfect' | 'unclear' | 'failed') => {
  switch (status) {
    case 'perfect': return '#F0FDF4';   // 淡绿色
    case 'unclear': return '#FFF7ED';   // 淡橙色
    case 'failed': return '#FEF2F2';    // 淡红色
    default: return '#FFFFFF';
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
  left: number;   // 像素值
  top: number;    // 像素值
  rotate: number;
  scale: number;
  size: CardSize;
  width: number;
  height: number;
}

// 计算单词卡片宽度：高度固定50px，最小宽度150px（3:1），单词长可以更宽
const calculateCardWidth = (wordText: string): number => {
  const minWidth = 150;
  const charWidth = 12;
  const padding = 40;
  const calculatedWidth = wordText.length * charWidth + padding;
  return Math.max(minWidth, calculatedWidth);
};

// 生成卡片位置 - 使用像素坐标
const generateCardPositions = (
  total: number, 
  words: ExtendedVocabWord[],
  containerWidth: number,
  containerHeight: number
): CardPosition[] => {
  if (containerWidth === 0 || containerHeight === 0) return [];
  
  const positions: CardPosition[] = [];
  const usedAreas: Array<{ x: number; y: number; width: number; height: number; status: string }> = [];
  
  const random = (index: number, offset: number) => {
    const seed = index * 137.508 + offset;
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };
  
  const cardHeight = 50;
  
  // 检查重叠（像素）
  const checkOverlap = (x: number, y: number, width: number, height: number, status: string): boolean => {
    const padding = status === 'perfect' ? -5 : 8;
    
    for (const area of usedAreas) {
      const effectivePadding = (status === 'perfect' && area.status === 'perfect') ? -10 : padding;
      
      if (
        x < area.x + area.width + effectivePadding &&
        x + width + effectivePadding > area.x &&
        y < area.y + area.height + effectivePadding &&
        y + height + effectivePadding > area.y
      ) {
        return true;
      }
    }
    return false;
  };
  
  for (let i = 0; i < total; i++) {
    const word = words[i];
    const sizeType: CardSize = 'medium';
    const scale = 1.0;
    
    // 卡片实际像素尺寸
    const cardWidthPx = calculateCardWidth(word?.text || '');
    const halfCardWidth = cardWidthPx / 2;
    const halfCardHeight = cardHeight / 2;
    
    const col = i % 3;
    const row = Math.floor(i / 3);
    const totalRows = Math.ceil(total / 3);
    
    // 安全边界（像素）：卡片中心点的允许范围
    // 增加边距确保卡片完全可见（包括阴影）
    const safeMargin = 10;
    const minX = halfCardWidth + safeMargin;                    // 左边界
    const maxX = containerWidth - halfCardWidth - safeMargin;   // 右边界
    const minY = halfCardHeight + safeMargin;                   // 上边界
    const maxY = containerHeight - halfCardHeight - safeMargin; // 下边界
    
    // 调试：打印容器尺寸
    if (i === 0) {
      console.log('[VocabCloud] Container:', containerWidth, 'x', containerHeight);
      console.log('[VocabCloud] Card width:', cardWidthPx, 'Safe X range:', minX, '-', maxX);
    }
    
    const availableWidth = maxX - minX;
    const availableHeight = maxY - minY;
    
    // 3 列均匀分布
    const colWidth = availableWidth / 3;
    // 限制偏移量，避免超出边界
    const maxColOffset = Math.min(colWidth * 0.2, 15);
    const colOffset = (random(i, 500) - 0.5) * maxColOffset;
    let baseX = minX + (col + 0.5) * colWidth + colOffset;
    
    const rowSpacing = availableHeight / Math.max(totalRows, 1);
    let baseY = minY + row * rowSpacing + rowSpacing * 0.5;
    
    let finalX = baseX;
    let finalY = baseY;
    let attempts = 0;
    const maxAttempts = 80;
    let foundPosition = false;
    
    while (attempts < maxAttempts && !foundPosition) {
      // 限制随机偏移范围
      const offsetRangeX = Math.min(colWidth * 0.25, 20);
      const offsetRangeY = Math.min(rowSpacing * 0.25, 15);
      
      const offsetX = (random(i, attempts * 2) - 0.5) * offsetRangeX;
      const offsetY = (random(i, attempts * 2 + 1) - 0.5) * offsetRangeY;
      
      const testX = baseX + offsetX;
      const testY = baseY + offsetY;
      
      // 确保卡片中心在安全区域内
      if (testX >= minX && testX <= maxX && testY >= minY && testY <= maxY) {
        const cardLeft = testX - halfCardWidth;
        const cardTop = testY - halfCardHeight;
        if (!checkOverlap(cardLeft, cardTop, cardWidthPx, cardHeight, word?.status || 'perfect')) {
          finalX = testX;
          finalY = testY;
          foundPosition = true;
        }
      }
      attempts++;
    }
    
    // 强制在安全区域内（无论是否找到位置）
    finalX = Math.max(minX, Math.min(maxX, finalX));
    finalY = Math.max(minY, Math.min(maxY, finalY));
    
    const rotationRange = 18;
    const rotation = (random(i, 100) - 0.5) * rotationRange;
    
    usedAreas.push({
      x: finalX - halfCardWidth,
      y: finalY - halfCardHeight,
      width: cardWidthPx,
      height: cardHeight,
      status: word?.status || 'perfect',
    });
    
    positions.push({
      left: finalX,
      top: finalY,
      rotate: rotation,
      scale: scale,
      size: sizeType,
      width: cardWidthPx,
      height: cardHeight,
    });
  }
  
  return positions;
};

interface WordCardProps {
  word: ExtendedVocabWord;
  index: number;
  positions: CardPosition[];
  dragConstraints: React.RefObject<HTMLDivElement | null>;
  isActive: boolean;
  onDragStart: () => void;
  baseZIndex: number;
}

const WordCard: React.FC<WordCardProps> = ({ 
  word, 
  index, 
  positions, 
  dragConstraints, 
  isActive, 
  onDragStart,
  baseZIndex 
}) => {
  const statusBadgeBg = getStatusColor(word.status);
  const cardBg = getCardBgColor(word.status);
  const position = positions[index];
  
  if (!position) return null;
  
  // 基础 z-index：active 卡片最高，否则根据 baseZIndex
  const zIndex = isActive ? 200 : baseZIndex;
  
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
      // 启用拖拽
      drag
      dragConstraints={dragConstraints}
      dragMomentum={false}
      dragElastic={0}
      onDragStart={onDragStart}
      whileHover={{ scale: position.scale * 1.05, rotate: position.rotate + (index % 2 === 0 ? 2 : -2) }}
      whileDrag={{ scale: position.scale * 1.15, cursor: 'grabbing' }}
      className={`absolute cursor-grab active:cursor-grabbing ${word.status === 'failed' ? 'opacity-60' : 'opacity-100'}`}
      style={{
        left: `${position.left}px`,
        top: `${position.top}px`,
        transform: 'translate(-50%, -50%)',
        width: `${position.width}px`,
        height: `${position.height}px`,
        zIndex: zIndex,
      }}
    >
      <WordBubbles index={index} />
      
      <div 
        className="border-[1.5px] border-black rounded-xl shadow-[3px_3px_0px_rgba(0,0,0,1)] flex items-center justify-center h-full relative overflow-hidden px-4 group transition-shadow hover:shadow-[4px_4px_0px_rgba(0,0,0,1)]"
        style={{ backgroundColor: cardBg }}
      >
        <div 
          className="absolute top-0 right-0 px-1.5 py-0.5 rounded-bl-md border-l border-b border-black/10 z-10"
          style={{ backgroundColor: statusBadgeBg }}
        >
          <span className="text-[8px] font-black text-white leading-none whitespace-nowrap">
            {word.statusText}
          </span>
        </div>
        <span 
          className="text-klein font-black italic tracking-tight text-center whitespace-nowrap select-none"
          style={{ fontSize: word.text.length > 8 ? '14px' : '16px' }}
        >
          {word.text}
        </span>
      </div>
    </motion.div>
  );
};

export const VocabPage: React.FC = () => {
  const { data, isLoading } = useReport();
  
  // 拖拽边界引用
  const dragConstraintsRef = useRef<HTMLDivElement>(null);
  
  // 容器尺寸
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  
  // 监听容器尺寸变化
  useEffect(() => {
    const container = dragConstraintsRef.current;
    if (!container) return;
    
    const updateSize = () => {
      setContainerSize({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    };
    
    // 初始化尺寸
    updateSize();
    
    // 使用 ResizeObserver 监听尺寸变化
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(container);
    
    return () => resizeObserver.disconnect();
  }, []);
  
  // 追踪当前激活的卡片（最后被拖动的）
  const [activeCardIndex, setActiveCardIndex] = useState<number | null>(null);
  // 追踪 z-index 顺序：记录每张卡片被拖动的顺序
  const [zIndexOrder, setZIndexOrder] = useState<number[]>([]);
  
  // Transform data from API to display format
  const words: ExtendedVocabWord[] = useMemo(() => {
    if (!data?.part1?.words) return [];
    return data.part1.words.map(w => ({
      text: w.text,
      status: w.status,
      statusText: getStatusText(w.status)
    }));
  }, [data?.part1?.words]);
  
  // Generate positions based on actual word count and container size
  const cardPositions = useMemo(() => 
    generateCardPositions(words.length, words, containerSize.width, containerSize.height), 
    [words, containerSize.width, containerSize.height]
  );
  
  // Calculate stats
  const stats = useMemo(() => {
    if (!words.length) return { masteryRate: 0, starLevel: 0 };
    const perfectCount = words.filter(w => w.status === 'perfect').length;
    const masteryRate = Math.round((perfectCount / words.length) * 100);
    const starLevel = masteryRate >= 90 ? 5 : masteryRate >= 75 ? 4 : masteryRate >= 60 ? 3 : masteryRate >= 40 ? 2 : 1;
    return { masteryRate, starLevel };
  }, [words]);
  
  // 处理卡片开始拖动
  const handleCardDragStart = (index: number) => {
    setActiveCardIndex(index);
    // 更新 z-index 顺序：将当前卡片移到最后（最高层）
    setZIndexOrder(prev => {
      const newOrder = prev.filter(i => i !== index);
      return [...newOrder, index];
    });
  };
  
  // 获取卡片的 z-index
  const getCardZIndex = (index: number) => {
    const orderIndex = zIndexOrder.indexOf(index);
    // 如果卡片还没被拖动过，使用初始 index
    if (orderIndex === -1) {
      return 10 + index;
    }
    // 被拖动过的卡片，根据顺序设置 z-index
    return 50 + orderIndex;
  };

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

      {/* 顶部 Header - 添加 flex-wrap 支持小屏幕 */}
      <div className="relative z-20 flex flex-wrap justify-between items-start mb-2 px-1 gap-2">
        <div className="space-y-0 min-w-0 flex-shrink">
          <motion.div 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="inline-flex items-center space-x-1.5 bg-baby px-2 py-0.5 rounded border border-black shadow-[1px_1px_0px_rgba(0,0,0,1)]"
          >
            <Flame size={10} className="text-klein fill-klein" />
            <span className="text-[8px] font-black text-klein uppercase tracking-widest">词汇能量</span>
          </motion.div>
          <motion.h2 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-3xl font-black text-white italic tracking-tighter leading-tight"
          >
            能量词汇站
          </motion.h2>
          <motion.p 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-[9px] font-bold text-baby/80 tracking-wide mt-0.5"
          >
            让每一个单词都充满成长的能量
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="relative flex-shrink-0"
        >
          <Monkey variant="glasses" layoutId="monkey" className="w-16 h-16 drop-shadow-2xl" imageSrc="/3.gif" />
        </motion.div>
      </div>

      <div className="relative z-10 flex-1 overflow-hidden my-3">
        <div ref={dragConstraintsRef} className="relative w-full h-full">
          {words.map((word, i) => (
            <WordCard 
              key={i} 
              word={word} 
              index={i} 
              positions={cardPositions} 
              dragConstraints={dragConstraintsRef}
              isActive={activeCardIndex === i}
              onDragStart={() => handleCardDragStart(i)}
              baseZIndex={getCardZIndex(i)}
            />
          ))}
        </div>
      </div>

      <div className="relative z-20 mt-4">
        <div className="w-full h-px bg-white/20 mb-3" />
        
        {/* 使用 flex-wrap 允许换行，gap 控制间距 */}
        <div className="flex flex-wrap items-end justify-between gap-3">
          {/* 左侧统计信息 - 设置最小宽度确保不被过度压缩 */}
          <div className="flex flex-col space-y-2 min-w-0 flex-shrink">
            <div className="flex items-center space-x-3">
              <div className="flex flex-col">
                <div className="flex items-center space-x-1 text-baby/60 mb-0.5">
                   <Activity size={10} />
                   <span className="text-[7px] font-black uppercase tracking-widest">单词数量</span>
                </div>
                <span className="text-base font-black text-white italic leading-none">{words.length}<span className="text-baby/40 text-[10px] ml-1 font-mono">个</span></span>
              </div>
              <div className="w-px h-6 bg-white/10" />
              <div className="flex flex-col">
                <div className="flex items-center space-x-1 text-baby/60 mb-0.5">
                   <ShieldCheck size={10} />
                   <span className="text-[7px] font-black uppercase tracking-widest">发音质量</span>
                </div>
                <span className="text-base font-black text-white italic leading-none">{stats.masteryRate >= 80 ? '优秀' : stats.masteryRate >= 60 ? '良好' : '加油'}</span>
              </div>
            </div>
            
            <div className="flex space-x-0.5">
               {Array.from({ length: 10 }).map((_, i) => (
                 <div key={i} className={`h-1 rounded-full ${i < Math.round(stats.masteryRate / 10) ? 'w-3 bg-baby' : 'w-1 bg-white/10'}`} />
               ))}
            </div>
          </div>

          {/* 右侧词汇掌握率卡片 - 允许收缩 */}
          <motion.div 
            initial={{ scale: 0, rotate: -5 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", delay: 1.2 }}
            className="bg-white border-2 border-black p-1 rounded-xl shadow-[4px_4px_0px_#FFF59D] flex items-stretch flex-shrink-0"
          >
            <div className="bg-klein text-white px-3 py-1.5 rounded-lg flex flex-col justify-center items-center">
              <span className="text-[7px] font-black text-white/40 uppercase leading-none mb-0.5">词汇掌握率</span>
              <div className="flex items-baseline leading-none">
                <span className="text-2xl font-black italic tracking-tighter">{stats.masteryRate}</span>
                <span className="text-[10px] font-black ml-0.5 opacity-50">%</span>
              </div>
            </div>
            <div className="px-2 flex flex-col justify-center space-y-0.5">
              <div className="flex space-x-0.5">
                {[1, 2, 3, 4, 5].map(i => (
                  <Star key={i} size={10} className={i <= stats.starLevel ? "text-klein fill-klein" : "text-klein/10"} strokeWidth={3} />
                ))}
              </div>
              <span className="text-[6px] font-black text-klein/40 text-center uppercase tracking-tighter">
                {stats.starLevel >= 4 ? '黄金等级' : stats.starLevel >= 3 ? '白银等级' : '青铜等级'}
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

import React, { useMemo, useState } from 'react';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { Monkey } from '@/components/monkey';
import { RadarDimension } from '@/types';
import { useReport } from '@/context/ReportContext';
import { Mic, Zap, BookOpen, Sun, MessageSquare, X, CheckCircle2, AlertCircle } from 'lucide-react';

const getIcon = (type: string, size: number = 14) => {
  switch (type) {
    case 'fluency': return <Zap size={size} />;
    case 'pronunciation': return <Mic size={size} />;
    case 'vocab': return <BookOpen size={size} />;
    case 'confidence': return <Sun size={size} />;
    case 'sentence': return <MessageSquare size={size} />;
    default: return <Mic size={size} />;
  }
};

// Custom Tick Component with click handler
interface CustomTickProps {
  payload?: { value: string };
  x?: number | string;
  y?: number | string;
  cx?: number | string;
  cy?: number | string;
  onClick: (item: RadarDimension | null) => void;
  data: RadarDimension[];
}

const CustomTick = ({ payload, x: rawX = 0, y: rawY = 0, cx: rawCx = 0, cy: rawCy = 0, onClick, data }: CustomTickProps) => {
  const x = Number(rawX);
  const y = Number(rawY);
  const cx = Number(rawCx);
  const cy = Number(rawCy);
  
  const item = data.find(d => d.subject === payload?.value);
  const icon = item ? getIcon(item.icon, 14) : null;
  const score = item ? Math.round(item.score) : 0;
  const isWeak = item && item.score < 60;

  // Adjust position slightly to not overlap the grid - 减小偏移量
  const yOffset = y > cy ? 18 : -18;
  const xOffset = x > cx ? 18 : x < cx ? -18 : 0;

  // 处理点击事件 - 移动端使用 onPointerDown
  const handleClick = (e: React.MouseEvent | React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onClick(item || null);
  };

  return (
    <g 
      transform={`translate(${x + xOffset},${y + yOffset})`} 
      onPointerDown={handleClick}
      style={{ cursor: 'pointer', touchAction: 'manipulation' }}
    >
      <foreignObject x="-40" y="-30" width="80" height="60">
        <div 
          className="flex flex-col items-center justify-center w-full h-full group"
          style={{ touchAction: 'manipulation' }}
        >
          {/* The Badge */}
          <div className={`flex items-center space-x-1 shadow-lg rounded-full px-2 py-0.5 border-2 transition-colors active:scale-95 ${isWeak ? 'bg-orange-100 border-orange-500' : 'bg-white border-baby'}`}>
            <span className={`${isWeak ? 'text-orange-600' : 'text-klein'}`}>{icon}</span>
            <span className={`text-xs font-black ${isWeak ? 'text-orange-600' : 'text-klein'}`}>{score}</span>
          </div>
        </div>
      </foreignObject>
    </g>
  );
};

// Detail Modal Component
const DetailModal = ({ item, onClose }: { item: RadarDimension; onClose: () => void }) => {
  if (!item) return null;
  
  const isWeak = item.score < 60;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-50 flex items-end justify-center bg-klein/80 backdrop-blur-sm p-4 pb-8"
      onClick={onClose}
    >
      <motion.div 
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        className="w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl relative overflow-hidden"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking card
      >
        {/* Background Decoration */}
        <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl -mr-10 -mt-10 opacity-20 ${isWeak ? 'bg-orange-500' : 'bg-babyDark'}`} />

        {/* Header */}
        <div className="flex justify-between items-start mb-6 relative z-10">
          <div className="flex items-center space-x-4">
             <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border-2 ${isWeak ? 'bg-orange-100 border-orange-500 text-orange-600' : 'bg-baby border-babyDark text-klein'}`}>
                {getIcon(item.icon, 28)}
             </div>
             <div>
               <h3 className="text-sm text-gray-500 font-bold uppercase tracking-wider">{item.subject}</h3>
               <h2 className="text-lg font-black text-gray-800 leading-tight">{item.comment.split(' - ')[0]}</h2>
             </div>
          </div>
          <button onClick={onClose} className="p-2 bg-gray-100 rounded-full hover:bg-gray-200 text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Score */}
        <div className="flex items-center space-x-4 mb-6">
           <div className="flex items-baseline space-x-1">
              <span className={`text-5xl font-black ${isWeak ? 'text-orange-500' : 'text-klein'}`}>{Math.round(item.score)}</span>
              <span className="text-gray-400 font-bold text-xl">/100</span>
           </div>
        </div>

        {/* Description */}
        <div className="bg-gray-50 rounded-xl p-4 mb-4 border border-gray-100">
           <div className="flex items-start space-x-3">
              {isWeak ? (
                <AlertCircle className="text-orange-500 flex-shrink-0 mt-0.5" size={20} />
              ) : (
                <CheckCircle2 className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
              )}
              <p className="text-gray-700 leading-relaxed font-medium text-sm">
                {item.comment.includes(' - ') ? item.comment.split(' - ')[1] : item.comment}
              </p>
           </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2">
           {item.tags?.map((tag, i) => (
             <span key={i} className={`text-xs font-bold px-3 py-1.5 rounded-lg ${isWeak ? 'bg-orange-50 text-orange-600' : 'bg-baby/30 text-klein'}`}>
               #{tag}
             </span>
           ))}
        </div>

      </motion.div>
    </motion.div>
  );
};

export const RadarPage: React.FC = () => {
  const { data, isLoading } = useReport();
  const [selectedItem, setSelectedItem] = useState<RadarDimension | null>(null);

  // Transform data for recharts (use 'score' as 'A' for backward compatibility)
  const chartData = useMemo(() => {
    if (!data?.radar) return [];
    return data.radar.map(item => ({
      ...item,
      A: item.score  // Recharts uses 'A' as the dataKey
    }));
  }, [data?.radar]);

  const averageScore = useMemo(() => {
    if (!data?.radar || data.radar.length === 0) return '0';
    const total = data.radar.reduce((acc, curr) => acc + curr.score, 0);
    return Math.round(total / data.radar.length).toString();
  }, [data?.radar]);

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col relative bg-klein overflow-hidden">
      
      {/* 1. Background Effects */}
      <div className="absolute inset-0 z-0">
         <motion.div 
           animate={{ rotate: 360 }}
           transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
           className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] opacity-10 bg-[conic-gradient(from_90deg_at_50%_50%,#fff_0deg,transparent_10deg,#fff_20deg,transparent_30deg,#fff_40deg,transparent_50deg,#fff_60deg,transparent_70deg,#fff_80deg,transparent_90deg,#fff_100deg,transparent_110deg,#fff_120deg,transparent_130deg,#fff_140deg,transparent_150deg,#fff_160deg,transparent_170deg,#fff_180deg,transparent_190deg,#fff_200deg,transparent_210deg,#fff_220deg,transparent_230deg,#fff_240deg,transparent_250deg,#fff_260deg,transparent_270deg,#fff_280deg,transparent_290deg,#fff_300deg,transparent_310deg,#fff_320deg,transparent_330deg,#fff_340deg,transparent_350deg,#fff_360deg)]"
         />
      </div>

      {/* 2. Top UI: Header & Score - 添加 flex-wrap 支持换行 */}
      <div className="relative z-10 w-full px-4 pt-6 flex flex-wrap justify-between items-start gap-3 flex-shrink-0">
         <div className="flex flex-col min-w-0">
            <motion.span 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              className="text-[10px] font-bold text-white/60 tracking-widest uppercase"
            >
              Ability Map
            </motion.span>
            <motion.h2 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-2xl font-black text-white italic"
            >
              五维<span className="text-baby">能力图谱</span>
            </motion.h2>
            <span className="text-[9px] text-white/50 mt-1">点击维度查看详情</span>
         </div>
         
         <motion.div 
           initial={{ scale: 0, rotate: -20 }}
           animate={{ scale: 1, rotate: 0 }}
           transition={{ type: "spring", delay: 0.3 }}
           className="relative flex-shrink-0"
         >
            <div className="w-14 h-14 bg-white rounded-xl rotate-3 shadow-[3px_3px_0px_#FBC02D] flex flex-col items-center justify-center border-2 border-klein z-20 relative">
               <span className="text-[7px] font-bold text-klein uppercase">AVG</span>
               <span className="text-2xl font-black text-klein leading-none">{averageScore}</span>
            </div>
            <div className="absolute inset-0 bg-baby rounded-xl rotate-12 -z-10" />
         </motion.div>
      </div>

      {/* 3. The Radar Chart (Interactive) */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-start pt-10 min-h-0">
         <motion.div 
           initial={{ scale: 0.8, opacity: 0 }}
           animate={{ scale: 1, opacity: 1 }}
           transition={{ duration: 0.6, ease: "backOut" }}
           className="w-full h-[45vh] max-h-[420px] relative"
         >
            {/* Central Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] h-[90%] bg-baby rounded-full blur-[80px] opacity-20 pointer-events-none" />

            {/* Background Rings */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[65%] h-[65%] border border-white/10 rounded-full" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[45%] h-[45%] border border-white/5 rounded-full" />

            <ResponsiveContainer width="100%" height="100%">
              {/* Domain set to 0-100 for percentage scale */}
              <RadarChart cx="50%" cy="50%" outerRadius="55%" data={chartData} margin={{ top: 50, right: 50, bottom: 50, left: 50 }}>
                <PolarGrid stroke="rgba(255,255,255,0.3)" strokeDasharray="4 4" />
                <PolarAngleAxis 
                  dataKey="subject" 
                  tick={(props) => <CustomTick {...props} onClick={setSelectedItem} data={data?.radar || []} />} 
                />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tickCount={6} tick={false} axisLine={false} />
                <Radar
                  name="Stats"
                  dataKey="A"
                  stroke="#FFF59D"
                  strokeWidth={3}
                  fill="#FFF59D"
                  fillOpacity={0.6}
                  isAnimationActive={true}
                  animationDuration={1500}
                />
              </RadarChart>
            </ResponsiveContainer>
         </motion.div>
      </div>

      {/* 4. The Monkey - 固定在右下角 */}
      <div 
        className="absolute z-20 pointer-events-none"
        style={{ bottom: 0, right: 0, position: 'absolute' }}
      >
         <div className="relative pointer-events-auto">
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 1.5, type: "spring" }}
              className="absolute -top-2 -left-24 bg-white text-klein px-3 py-1.5 rounded-2xl rounded-br-none shadow-lg border-2 border-baby whitespace-nowrap z-30"
            >
               <span className="text-[10px] font-black">分析完成!</span>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.5 }}
            >
              <Monkey variant="glasses" layoutId="monkey" className="h-[25vh] w-auto max-h-[220px] drop-shadow-2xl" imageSrc="/2.gif" />
            </motion.div>
         </div>
      </div>

      {/* 5. Detail Modal Overlay */}
      <AnimatePresence>
        {selectedItem && (
          <DetailModal item={selectedItem} onClose={() => setSelectedItem(null)} />
        )}
      </AnimatePresence>

    </div>
  );
};

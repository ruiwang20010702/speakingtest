import React from 'react';
import { motion } from 'framer-motion';
import { useReport } from '@/context/ReportContext';
import { Sun, RefreshCw, Clock, Sparkles, Rocket, Heart, Star, AlertTriangle, CheckCircle } from 'lucide-react';

const PlanCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  desc: string;
  bgColor: string;
  index: number;
}> = ({ icon, title, desc, bgColor, index }) => (
  <motion.div
    initial={{ x: 30, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay: 0.4 + index * 0.1 }}
    className="flex items-center space-x-4 bg-white border-2 border-black p-3 rounded-2xl shadow-[4px_4px_0px_#000]"
  >
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center border-2 border-black shadow-[2px_2px_0px_#000] ${bgColor}`}>
      {icon}
    </div>
    <div className="flex-1">
      <h4 className="text-xs font-black text-klein uppercase tracking-tight">{title}</h4>
      <p className="text-[10px] font-bold text-gray-500 mt-0.5">{desc}</p>
    </div>
  </motion.div>
);

// Icons for dynamic plan items
const planIcons = [
  { icon: <Sun size={20} className="text-orange-600" />, bgColor: "bg-yellow-100" },
  { icon: <RefreshCw size={20} className="text-blue-600" />, bgColor: "bg-blue-100" },
  { icon: <Clock size={20} className="text-red-600" />, bgColor: "bg-red-100" },
  { icon: <Star size={20} className="text-purple-600" />, bgColor: "bg-purple-100" },
];

export const RoadmapPage: React.FC = () => {
  const { data, isLoading } = useReport();

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-klein">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  const suggestion = data?.suggestion;

  return (
    <div className="w-full h-full flex flex-col relative bg-klein overflow-hidden select-none px-5 pt-8 pb-4">
      
      {/* 标题区 */}
      <div className="relative z-30 mb-4">
        <motion.div 
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="inline-flex items-center space-x-1.5 bg-baby px-2 py-0.5 rounded-sm border-[1.5px] border-black shadow-[2px_2px_0px_#000]"
        >
          <Rocket size={10} className="text-klein fill-klein" />
          <span className="text-[8px] font-black text-klein uppercase tracking-widest">学习建议</span>
        </motion.div>
        <motion.h2 
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-3xl font-black text-white italic tracking-tighter mt-2 leading-none"
        >
          成长<span className="text-baby">计划</span>
        </motion.h2>
      </div>

      {/* 亮点和短板卡片 */}
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="relative z-20 bg-white border-2 border-black rounded-[32px] px-6 pt-5 pb-5 mb-4 shadow-[6px_6px_0px_#000] overflow-hidden"
      >
        <div className="absolute top-2 right-4 opacity-10">
           <Sparkles size={40} className="text-klein" />
        </div>
        
        <div className="space-y-4">
          {/* 亮点 */}
          {suggestion?.highlights && suggestion.highlights.length > 0 && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0 border border-green-200">
                <CheckCircle size={16} className="text-green-600" />
              </div>
              <div className="flex-1">
                <h4 className="text-xs font-black text-green-600 uppercase tracking-tight mb-1">亮点表现</h4>
                <div className="space-y-1">
                  {suggestion.highlights.map((highlight, i) => (
                    <p key={i} className="text-[10px] font-bold text-gray-600 leading-tight">{highlight}</p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 短板 */}
          {suggestion?.weaknesses && suggestion.weaknesses.length > 0 && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center flex-shrink-0 border border-orange-200">
                <AlertTriangle size={16} className="text-orange-600" />
              </div>
              <div className="flex-1">
                <h4 className="text-xs font-black text-orange-600 uppercase tracking-tight mb-1">提升空间</h4>
                <div className="space-y-1">
                  {suggestion.weaknesses.map((weakness, i) => (
                    <p key={i} className="text-[10px] font-bold text-gray-600 leading-tight">{weakness}</p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* 行动计划列表 */}
      <div className="space-y-2.5 mb-4 relative z-20">
        {suggestion?.plan && suggestion.plan.length > 0 ? (
          suggestion.plan.slice(0, 4).map((item, index) => {
            const iconData = planIcons[index % planIcons.length];
            return (
              <PlanCard 
                key={index}
                icon={iconData.icon}
                title={`建议 ${index + 1}`}
                desc={item}
                bgColor={iconData.bgColor}
                index={index}
              />
            );
          })
        ) : (
          <>
            <PlanCard 
              icon={<Sun size={20} className="text-orange-600" />}
              title="每日跟读"
              desc="每天 10 分钟标准音频跟读"
              bgColor="bg-yellow-100"
              index={0}
            />
            <PlanCard 
              icon={<RefreshCw size={20} className="text-blue-600" />}
              title="整句练习"
              desc="多用完整句子回答问题"
              bgColor="bg-blue-100"
              index={1}
            />
            <PlanCard 
              icon={<Clock size={20} className="text-red-600" />}
              title="自信表达"
              desc="保持自信，大声开口练习"
              bgColor="bg-red-100"
              index={2}
            />
          </>
        )}
      </div>

      {/* 其他建议与寄语 */}
      <div className="relative z-20 flex-1 flex flex-col">
        <motion.div 
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="relative bg-white/5 border border-white/20 rounded-3xl p-5 flex-1 backdrop-blur-sm"
        >
          <div className="flex items-center space-x-2 mb-3">
            <Heart size={14} className="text-baby fill-baby" />
            <span className="text-[10px] font-black text-white uppercase tracking-widest">寄语</span>
          </div>
          <div className="space-y-3 overflow-y-auto pr-1">
            <p className="text-[11px] font-bold text-white/90 leading-relaxed">
              语言学习的关键在于接触这门语言的频率。想要提高英语口语，每周至少需要上<span className="text-baby">5~6节外教课</span>。
            </p>
            <p className="text-[11px] font-bold text-white/90 leading-relaxed">
              另外，课前预习和课后复习也是非常有帮助的。坚持高频学习，<span className="text-baby italic">未来的你一定会感谢现在努力的自己！</span>
            </p>
          </div>
        </motion.div>
      </div>

      {/* 底部 Footer */}
      <div className="mt-4 flex items-center justify-between opacity-30 px-2 shrink-0 relative z-10">
         <span className="text-[7px] font-mono text-white tracking-widest">51TALK AI LAB © 2026</span>
         <div className="flex space-x-2">
            <div className="w-1 h-1 bg-white rounded-full" />
            <div className="w-1 h-1 bg-white rounded-full" />
            <div className="w-1 h-1 bg-white rounded-full" />
         </div>
         <span className="text-[7px] font-black text-baby tracking-widest uppercase italic">Keep Growing</span>
      </div>

      {/* 装饰性背景 */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.05] z-0">
        <div className="w-full h-full bg-[repeating-linear-gradient(45deg,#fff,#fff_2px,transparent_2px,transparent_40px)]" />
      </div>
    </div>
  );
};

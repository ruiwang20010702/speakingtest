import React, { useEffect } from 'react';
import { Star, MessageCircle, CheckCircle2 } from 'lucide-react';

interface ResultPageProps {
  part1Score?: number;  // Part 1 score (0-20)
  onRestart: () => void;
}

const ResultPage: React.FC<ResultPageProps> = ({ part1Score, onRestart }) => {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 overflow-hidden bg-white">
      <div className="w-full max-w-md flex flex-col items-center relative py-8">

        {/* Success Icon */}
        <div className="w-24 h-24 bg-[#58CC02] rounded-full flex items-center justify-center mb-8 shadow-xl animate-pop">
          <CheckCircle2 className="w-14 h-14 text-white" strokeWidth={2.5} />
        </div>

        {/* Title */}
        <h1 className="text-3xl font-black text-[#1E293B] mb-3 tracking-tight animate-pop delay-1">
          测评完成！
        </h1>

        <p className="text-[#1E293B]/60 font-bold text-base mb-10 animate-pop delay-1">
          你真棒，已完成本次口语测评
        </p>

        {/* Part 1 Score Card */}
        {part1Score !== undefined && (
          <div className="w-full bg-gradient-to-br from-[#FFD200]/10 to-[#FFD200]/5 rounded-[24px] p-6 mb-8 border-2 border-[#FFD200]/30 animate-pop delay-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-[#1E293B]/60 mb-1">词汇朗读得分</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-black text-[#1E293B]">{part1Score}</span>
                  <span className="text-2xl font-black text-[#1E293B]/40">/20</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-[#FFD200] rounded-full flex items-center justify-center shadow-lg">
                <Star className="w-9 h-9 text-white fill-current" />
              </div>
            </div>
          </div>
        )}

        {/* Guidance Card */}
        <div className="w-full bg-[#1CB0F6]/5 rounded-[24px] p-6 mb-10 border-2 border-[#1CB0F6]/20 animate-pop delay-3">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="font-black text-[#1E293B] text-base mb-2">完整报告已生成</p>
              <p className="text-sm text-[#1E293B]/60 leading-relaxed">
                包含总分、星级评定与学习建议。<br />
                请联系<span className="font-bold text-[#1CB0F6]">班主任老师</span>获取详细报告。
              </p>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={onRestart}
          className="w-full py-5 bg-[#1CB0F6] text-white font-black text-xl rounded-[20px] active:scale-95 transition-all shadow-[0_6px_0_#1899D6] active:shadow-none active:translate-y-[6px] animate-pop delay-4"
        >
          完成
        </button>

        <p className="mt-6 text-center text-gray-400 font-bold text-xs uppercase tracking-widest">
          51TALK AI 口语测评系统
        </p>
      </div>
    </div>
  );
};

export default ResultPage;


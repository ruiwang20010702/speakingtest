
import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

const LoadingPage: React.FC = () => {
  const [step, setStep] = useState(0);
  const steps = [
    "正在分析 Part 1 词汇...",
    "正在分析 Part 2 句子...",
    "正在分析 Part 3 问答...",
    "正在生成报告...",
    "评分即将揭晓..."
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setStep(prev => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-4 sm:p-8 text-center bg-white">
      <div className="relative mb-12">
         <img 
           src="/Dynamic%20materials/progress%20bar.gif?t=123456" 
           alt="Loading" 
           className="w-64 h-64 object-contain drop-shadow-2xl"
           key="progress-bar-gif"
         />
      </div>

      <h1 className="text-2xl sm:text-3xl font-black text-[#1E293B] mb-2 animate-pulse">AI 正在分析中...</h1>
      <p className="text-sm sm:text-lg text-[#1E293B]/60 mb-8 sm:mb-12 font-bold">请稍候，老师正在为你批改</p>
      
      <div className="bg-gray-50 rounded-[24px] sm:rounded-[32px] p-6 sm:p-8 w-full max-w-sm border border-gray-200 shadow-sm">
        <div className="flex flex-col space-y-5">
          {steps.map((s, i) => (
            <div key={i} className={`flex items-center gap-3 transition-all duration-500 ${i === step ? 'text-[#1E293B] font-bold opacity-100' : i < step ? 'text-[#58CC02] opacity-60' : 'text-[#1E293B]/40 opacity-40'}`}>
              <div className={`w-2.5 h-2.5 rounded-full ${i === step ? 'bg-[#FFD200] scale-150 animate-pulse' : i < step ? 'bg-[#58CC02]' : 'bg-white/50'}`}></div>
              <span className="text-sm tracking-tight">{s}</span>
              {i < step && <span className="text-[10px] ml-auto font-black uppercase">Complete</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-16 flex flex-col items-center gap-4">
         <div className="px-5 py-2.5 bg-[#FFD200] rounded-full text-[#824B00] text-sm font-black shadow-md">
           请不要关闭页面
         </div>
         <p className="text-[#1E293B]/60 font-bold italic opacity-80">"马上就好，你一定很棒！"</p>
      </div>
    </div>
  );
};

export default LoadingPage;

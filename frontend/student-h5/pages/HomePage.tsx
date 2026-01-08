
import React, { useState, useEffect } from 'react';
import { User, Layers, BookOpen, ArrowRight, Zap, Sparkles, ShieldCheck, CheckCircle2, Star, Phone } from 'lucide-react';
import { Level } from '../types';

interface HomePageProps {
  onStart: (name: string, level: Level, unit: string) => void;
}

const AICore = () => (
  <div className="relative w-64 h-64 sm:w-80 sm:h-80 flex items-center justify-center">
    <img 
      src="/Dynamic materials/Homepage.gif" 
      alt="AI Core" 
      className="w-64 h-64 sm:w-80 sm:h-80 object-contain drop-shadow-2xl"
    />
  </div>
);

const HomePage: React.FC<HomePageProps> = ({ onStart }) => {
  const [step, setStep] = useState<'info' | 'intro'>('info');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [level, setLevel] = useState<Level | ''>('');
  const [unit, setUnit] = useState('Unit 1-4');

  const levels: Level[] = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'];

  // 核心逻辑：单元选项依赖于等级
  useEffect(() => {
    if (!level) {
      setUnit(''); // 未选等级时单元清空
    } else if (level === 'L1' || level === 'L2') {
      setUnit('Unit 1-4'); // L1, L2 默认 Unit 1-4
    } else {
      setUnit('Full Level'); // 其它等级锁定为全单元
    }
  }, [level]);

  const handleNextStep = () => {
    if (!name.trim() || !phone.trim() || !level || !unit) return;
    setStep('intro');
  };

  const hasUnitDifference = level === 'L1' || level === 'L2';

  return (
    <div className="min-h-screen w-full flex flex-col items-center overflow-y-auto p-4 sm:p-6 pt-8 sm:pt-14 pb-8 sm:pb-12 relative bg-white">
      {step === 'intro' && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[10%] left-[5%] animate-float opacity-20"><Star className="w-8 sm:w-12 h-8 sm:h-12 text-[#FFD200] fill-current" /></div>
          <div className="absolute top-[20%] right-[10%] animate-float opacity-10" style={{animationDelay: '1.5s'}}><Zap className="w-12 sm:w-16 h-12 sm:h-16 text-[#1CB0F6] fill-current" /></div>
          <div className="absolute bottom-[20%] left-[10%] animate-float opacity-20" style={{animationDelay: '0.5s'}}><Sparkles className="w-8 sm:w-10 h-8 sm:h-10 text-[#58CC02]" /></div>
        </div>
      )}

      <div className="w-full max-w-md flex justify-between items-center mb-6 z-10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 sm:w-8 sm:h-8 bg-[#1CB0F6] rounded-xl flex items-center justify-center">
            <Zap className="text-white w-4 h-4 sm:w-5 sm:h-5 fill-current" />
          </div>
          <span className="font-black text-lg sm:text-xl tracking-tight text-[#1CB0F6]">51Talk AI</span>
        </div>
        <div className="px-2 sm:px-3 py-1 bg-gray-100 rounded-full text-[9px] sm:text-[10px] font-black text-[#1E293B] uppercase tracking-widest border border-gray-200">
          v2.5 Professional
        </div>
      </div>

      {step === 'info' ? (
        <div className="flex-1 w-full max-w-md flex flex-col py-2 sm:py-4 z-10 min-h-0">
          <div className="flex flex-col items-center text-center space-y-2 mb-3 sm:mb-4 flex-shrink-0">
            <AICore />
            <div className="space-y-1">
              <h1 className="text-2xl sm:text-3xl font-black text-[#1E293B] tracking-tight">你好, 学习伙伴!</h1>
              <p className="text-sm sm:text-base text-[#1E293B]/70 font-bold">准备好开始你的口语测评了吗？</p>
            </div>
          </div>

          <div className="space-y-2.5 sm:space-y-3 pt-2 sm:pt-4 flex-1 flex flex-col justify-end pb-4">
            <div className="relative">
              <User className="absolute left-5 top-1/2 -translate-y-1/2 text-[#1CB0F6] w-5 h-5" />
              <input 
                type="text" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="输入你的姓名"
                className="w-full bg-white/60 backdrop-blur-md rounded-[25px] border-2 border-transparent py-4 pl-14 pr-6 font-black text-lg outline-none focus:border-[#1CB0F6] focus:bg-white transition-all shadow-sm"
              />
            </div>

            <div className="relative">
              <Phone className="absolute left-5 top-1/2 -translate-y-1/2 text-[#58CC02] w-5 h-5" />
              <input 
                type="tel" 
                value={phone}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '');
                  setPhone(value);
                }}
                placeholder="输入手机号"
                maxLength={11}
                className="w-full bg-white/60 backdrop-blur-md rounded-[25px] border-2 border-transparent py-4 pl-14 pr-6 font-black text-lg outline-none focus:border-[#58CC02] focus:bg-white transition-all shadow-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="relative">
                <Layers className="absolute left-5 top-1/2 -translate-y-1/2 text-[#FFD200] w-4 h-4" />
                <select 
                  value={level}
                  onChange={(e) => setLevel(e.target.value as Level)}
                  className="w-full bg-white/60 backdrop-blur-md rounded-[25px] py-4 pl-12 pr-4 font-black outline-none appearance-none cursor-pointer focus:bg-white"
                >
                  <option value="" disabled>选择等级</option>
                  {levels.map(l => (
                    <option key={l} value={l}>{l} 等级</option>
                  ))}
                </select>
              </div>
              
              <div className={`relative transition-all duration-300 ${!level ? 'opacity-40' : 'opacity-100'}`}>
                <BookOpen className={`absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 ${!level ? 'text-gray-400' : 'text-[#58CC02]'}`} />
                <select 
                  value={unit}
                  disabled={!level || !hasUnitDifference}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full bg-white/60 backdrop-blur-md rounded-[25px] py-4 pl-12 pr-4 font-black outline-none appearance-none disabled:cursor-not-allowed disabled:text-gray-400"
                >
                  {!level && <option value="">待选等级</option>}
                  {level && !hasUnitDifference && <option value="Full Level">全单元</option>}
                  {level && hasUnitDifference && (
                    <>
                      <option value="Unit 1-4">Unit 1-4</option>
                      <option value="Unit 5-8">Unit 5-8</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            <button
              onClick={handleNextStep}
              disabled={!name.trim() || !phone.trim() || !level || !unit}
              className={`w-full py-4 sm:py-5 rounded-[25px] font-black text-xl btn-duo flex items-center justify-center gap-3 mt-auto ${
                name.trim() && phone.trim() && level && unit
                ? 'bg-[#1CB0F6] text-white border-[#1899D6]' 
                : 'bg-white/40 text-[#1E293B]/40 border-white/30 cursor-not-allowed'
              }`}
            >
              继续 <ArrowRight className="w-6 h-6" />
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 w-full max-w-sm flex flex-col justify-between py-4 pb-8 animate-in fade-in slide-in-from-right-4 z-10">
          <div className="space-y-8">
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-black text-[#1E293B] tracking-tight">测评任务清单</h2>
              <p className="text-[#1E293B]/70 font-bold text-base italic">Hi <span className="text-[#1CB0F6]">{name}</span>, 我们将进行以下挑战:</p>
            </div>

            <div className="space-y-4">
              <div className="group relative bg-white/60 backdrop-blur-md p-5 rounded-[35px] border-2 border-white/50 flex items-center gap-5 shadow-lg hover:translate-y-[-2px] transition-all duration-300 overflow-hidden">
                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                  <CheckCircle2 className="w-16 h-16 text-[#FFD200]" />
                </div>
                <div className="w-14 h-14 bg-[#FFD200] rounded-[22px] flex items-center justify-center font-black text-white text-2xl shadow-inner">1</div>
                <div>
                  <h4 className="font-black text-[#1E293B] text-lg">词汇挑战</h4>
                  <p className="text-[#1E293B]/60 text-sm font-bold">看图朗读核心单词</p>
                </div>
              </div>

              <div className="group relative bg-white/60 backdrop-blur-md p-5 rounded-[35px] border-2 border-white/50 flex items-center gap-5 shadow-lg hover:translate-y-[-2px] transition-all duration-300 overflow-hidden">
                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                   <Zap className="w-16 h-16 text-[#1CB0F6]" />
                </div>
                <div className="w-14 h-14 bg-[#1CB0F6] rounded-[22px] flex items-center justify-center font-black text-white text-2xl shadow-inner">2</div>
                <div>
                  <h4 className="font-black text-[#1E293B] text-lg">回答老师的问题</h4>
                  <p className="text-[#1E293B]/60 text-sm font-bold">与 AI 进行 10-12 个对话</p>
                </div>
              </div>
            </div>

            <div className="bg-[#1CB0F6]/10 backdrop-blur-sm p-5 rounded-[30px] border-2 border-[#1CB0F6]/20 flex gap-4 items-center">
              <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm">
                <ShieldCheck className="w-7 h-7 text-[#1CB0F6]" strokeWidth={2.5} />
              </div>
              <p className="text-[#1CB0F6] text-xs font-black leading-snug">
                建议佩戴耳机，并在安静环境下进行。<br/>宝贝，准备好了吗？
              </p>
            </div>
          </div>

          <div className="space-y-4 pt-8 pb-4">
            <button
              onClick={() => level && onStart(name, level, unit)}
              className="w-full py-6 bg-[#FFD200] text-[#824B00] font-black text-2xl rounded-[30px] border-[#E5A000] btn-duo shadow-lg flex items-center justify-center gap-4 transition-transform active:scale-95"
            >
              立刻开始! <Zap className="w-6 h-6 fill-current" />
            </button>
            <button 
              onClick={() => setStep('info')}
              className="w-full text-[#1E293B]/50 font-black text-sm text-center underline underline-offset-4 decoration-2 decoration-white/30"
            >
              返回修改信息
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;


import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronRight, ChevronLeft, Trophy, Star, Sparkles, Heart, Mic, Square, CheckCircle2, Play, Info } from 'lucide-react';
import { Question, Level } from '../types';
import { getQuestions } from '../services/api';
import ProgressBar from '../components/ProgressBar';

interface TestPageProps {
  studentName: string;
  level: Level;
  unit: string;
  onExit: () => void;
  onComplete: (audios: Blob[]) => void;
  onPart1Complete?: (audio: Blob, part1Questions: Question[]) => void; // 传递题目列表避免重复请求
}


const SpeechBubble = ({ text, onPlayAudio, isRecording, isAudioPlaying, onAudioStateChange }: {
  text: string;
  onPlayAudio?: () => void;
  isRecording?: boolean;
  isAudioPlaying?: boolean;
  onAudioStateChange?: (playing: boolean) => void;
}) => {
  const handlePlay = () => {
    // 录音期间完全禁止播放音频
    if (isRecording) {
      return;
    }

    if (onPlayAudio && onAudioStateChange) {
      onAudioStateChange(true);
      onPlayAudio();
    }
  };

  return (
    <div className="relative mb-4 animate-in fade-in slide-in-from-top-4 duration-500 min-h-[100px] flex items-center">
      <div className="bg-[#1E293B] text-white p-5 rounded-[28px] shadow-xl border-2 border-white/10 flex items-start gap-3 w-full max-w-[280px]">
        {onPlayAudio && (
          <button
            onClick={handlePlay}
            disabled={isAudioPlaying || isRecording}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-95 flex-shrink-0 ${isAudioPlaying || isRecording
              ? 'bg-[#FFF59D]/30 cursor-not-allowed'
              : 'bg-gradient-to-r from-[#FFF59D] to-[#FBC02D] hover:from-[#FFF59D]/90 hover:to-[#FBC02D]/90 shadow-md'
              }`}
            title={isRecording ? "录音中，无法播放" : "再听一次"}
          >
            <Play className={`w-5 h-5 text-white ${isAudioPlaying ? 'animate-pulse' : ''}`} fill="currentColor" />
          </button>
        )}
        <div className="flex-1">
          <p className="text-lg font-black leading-snug tracking-tight">{text}</p>
        </div>
      </div>
      <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[12px] border-l-transparent border-r-[12px] border-r-transparent border-t-[12px] border-t-[#1E293B]"></div>
    </div>
  );
};

const CircularRecordButton = ({
  onClick,
  variant,
  isRecording
}: {
  onClick: () => void,
  variant: 'blue' | 'red' | 'green' | 'yellow',
  isRecording?: boolean
}) => {
  const styles = {
    blue: "bg-[#FFF59D] border-[#FBC02D] text-[#002FA7]",
    red: "bg-[#FF4B4B] border-[#D32F2F] text-white",
    green: "bg-[#58CC02] border-[#419D01] text-white",
    yellow: "bg-[#FFD200] border-[#E5A000] text-white"
  };

  return (
    <button
      onClick={onClick}
      className={`w-20 h-20 rounded-[24px] border-b-[6px] flex items-center justify-center transition-all active:border-b-0 active:translate-y-[6px] relative shadow-lg ${styles[variant]} ${isRecording ? 'animate-pulse' : ''}`}
    >
      {isRecording ? (
        <Square className="w-8 h-8 fill-current relative z-10" />
      ) : (
        <Mic className="w-8 h-8 relative z-10" strokeWidth={3} />
      )}
    </button>
  );
};

const TestPage: React.FC<TestPageProps> = ({ studentName, level, unit, onExit, onComplete, onPart1Complete }) => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0); // 从 Part 1 开始
  const [currentPart, setCurrentPart] = useState(1); // 从 Part 1 开始
  const [audios, setAudios] = useState<Blob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showTransition, setShowTransition] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showPart2Guide, setShowPart2Guide] = useState(true);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [showStartGuide, setShowStartGuide] = useState(true); // 开始前的引导页

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);

  // 滑动相关状态
  const minSwipeDistance = 50;

  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoadError(null);
      const q = await getQuestions(level, unit);
      setQuestions(q);
      } catch (error: any) {
        console.error('Failed to load questions:', error);
        // 如果 getQuestions 已经自动切换到模拟数据，这里不应该有错误
        // 但如果还是失败了，显示错误信息
        if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
          setLoadError('后端服务未启动。提示：已在控制台自动切换到模拟数据模式，刷新页面即可使用');
        } else if (error.response?.status === 500) {
          setLoadError('后端服务错误。提示：已在控制台自动切换到模拟数据模式，刷新页面即可使用');
        } else {
          setLoadError(error.response?.data?.detail || '加载题目失败，请检查网络连接');
        }
      } finally {
      setIsLoading(false);
      }
    };
    fetchQuestions();

    // 清理函数：组件卸载时停止语音播放
    return () => {
      window.speechSynthesis.cancel();
    };
  }, [level, unit]);

  const getPartBounds = (part: number) => {
    if (part === 1) return [0, 19];
    return [20, questions.length - 1];
  };

  const bounds = questions.length > 0 ? getPartBounds(currentPart) : [0, 0];
  const [startIdx, endIdx] = bounds;
  const partTotal = endIdx - startIdx + 1;
  const partCurrent = currentIndex - startIdx + 1;

  const startRecording = async () => {
    try {
      // 重要：开始录音前，立即停止所有音频播放，避免录制到系统播放的声音
      window.speechSynthesis.cancel();
      setIsAudioPlaying(false);

      // 等待一小段时间，确保音频完全停止后再开始录音
      await new Promise(resolve => setTimeout(resolve, 200));

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
        const newAudios = [...audios, blob];
        setAudios(newAudios);
        setIsRecording(false);

        if (currentPart === 1) {
          // Part 1 完成，立即触发回调开始后台评分（传递题目列表）
          if (onPart1Complete) {
            onPart1Complete(blob, questions.slice(0, 20));
          }
          setShowTransition(true);
        } else {
          onComplete(newAudios);
        }
      };
      recorder.start();
      setIsRecording(true);
    } catch (err) { alert("请允许麦克风权限"); }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  // 触摸滑动处理
  const touchStartRef = useRef<number | null>(null);
  const touchEndRef = useRef<number | null>(null);

  const onTouchStart = (e: React.TouchEvent) => {
    touchEndRef.current = null;
    touchStartRef.current = e.targetTouches[0].clientX;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    touchEndRef.current = e.targetTouches[0].clientX;
  };

  const onTouchEnd = () => {
    if (!touchStartRef.current || !touchEndRef.current) return;

    // 必须先开始录音才能滑动（检查当前 part 是否已开始录音）
    const currentPartStarted = currentPart === 1 ? audios.length > 0 : audios.length > 20;
    if (!isRecording && !currentPartStarted) {
      alert("请先点击麦克风开始录音 🎤");
      return;
    }

    // 录音期间或录音完成后可以自由滑动
    const distance = touchStartRef.current - touchEndRef.current;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe) {
      handleNext();
    }
    if (isRightSwipe) {
      handlePrev();
    }
  };

  const handleNext = () => {
    if (currentIndex < endIdx) setCurrentIndex(prev => prev + 1);
  };

  const handlePrev = () => {
    if (currentIndex > startIdx) setCurrentIndex(prev => prev - 1);
  };

  // 播放英语句子音频
  const playEnglishAudio = (text: string) => {
    // 停止之前的播放
    window.speechSynthesis.cancel();
    setIsAudioPlaying(true);

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 0.8; // 稍微慢一点，适合小朋友
    utterance.pitch = 1.1; // 稍微高一点，更友好
    utterance.volume = 1.0; // 提高音量，确保能听清

    // 播放完成后的回调
    utterance.onend = () => {
      setIsAudioPlaying(false);
      speechSynthesisRef.current = null;
    };

    // 播放错误时的回调
    utterance.onerror = () => {
      setIsAudioPlaying(false);
      speechSynthesisRef.current = null;
    };

    speechSynthesisRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  // Part 2 切换问题时自动播放音频
  useEffect(() => {
    // 确保 questions 已加载且 currentIndex 有效
    if (questions.length === 0 || isLoading || currentIndex < 0 || currentIndex >= questions.length) return;

    const currentQ = questions[currentIndex];
    const isPartDialogue = currentPart === 2;

    if (isPartDialogue && currentQ && currentQ.text) {
      // 延迟一点播放，让页面切换动画完成
      const timer = setTimeout(() => {
        playEnglishAudio(currentQ.text);
      }, 500);
      return () => {
        clearTimeout(timer);
        window.speechSynthesis.cancel();
      };
    }
  }, [currentIndex, currentPart, questions.length, isLoading]);

  if (isLoading) return <div className="h-screen flex items-center justify-center font-black text-[#FFF59D] bg-[#002FA7]">加载中...</div>;

  // 测试开始前的引导页面
  if (showStartGuide) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-between p-6 pt-12 pb-10 bg-[#002FA7] animate-in fade-in duration-500">
        {/* 顶部标题 */}
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Sparkles className="w-6 h-6 text-[#FFF59D]" />
            <span className="text-[#FFF59D] font-black text-sm uppercase tracking-widest">Speaking Test</span>
            <Sparkles className="w-6 h-6 text-[#FFF59D]" />
          </div>
          <h1 className="text-3xl font-black text-white">
            Hi，<span className="text-[#FFF59D]">{studentName}</span>！
          </h1>
          <p className="text-white/70 font-bold text-sm">准备好开始口语测评了吗？</p>
        </div>

        {/* 中间引导卡片 */}
        <div className="w-full max-w-sm space-y-4 my-6 overflow-y-auto max-h-[60vh]">
          {/* Part 1 操作说明 */}
          <div className="bg-gradient-to-br from-[#FFD200]/20 to-[#FFD200]/5 backdrop-blur-sm rounded-[24px] p-4 border border-[#FFD200]/30">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#FFD200] rounded-full flex items-center justify-center">
                <span className="text-xl">📖</span>
              </div>
              <div>
                <h3 className="font-black text-white text-base">Part 1 · 核心词汇</h3>
                <p className="text-white/60 text-xs font-bold">看图朗读单词</p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#FFD200] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-[#002FA7] font-black text-xs">1</span>
                </div>
                <p className="text-white text-sm font-bold">点击<span className="text-[#FFD200]">黄色麦克风</span>开始录音</p>
              </div>
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#FFD200] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-[#002FA7] font-black text-xs">2</span>
                </div>
                <p className="text-white text-sm font-bold">看图片，<span className="text-[#FFD200]">大声朗读</span>单词</p>
              </div>
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#FFD200] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-[#002FA7] font-black text-xs">3</span>
                </div>
                <p className="text-white text-sm font-bold"><span className="text-[#FFD200]">左右滑动</span>查看下一个单词</p>
              </div>
            </div>
          </div>

          {/* Part 2 操作说明 */}
          <div className="bg-gradient-to-br from-[#1CB0F6]/20 to-[#1CB0F6]/5 backdrop-blur-sm rounded-[24px] p-4 border border-[#1CB0F6]/30">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#1CB0F6] rounded-full flex items-center justify-center">
                <span className="text-xl">💬</span>
              </div>
              <div>
                <h3 className="font-black text-white text-base">Part 2 · 对话问答</h3>
                <p className="text-white/60 text-xs font-bold">听问题，用英语回答</p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-black text-xs">1</span>
                </div>
                <p className="text-white text-sm font-bold">问题<span className="text-[#1CB0F6]">自动播放</span>，仔细听</p>
              </div>
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-black text-xs">2</span>
                </div>
                <p className="text-white text-sm font-bold">点击<span className="text-[#1CB0F6]">蓝色麦克风</span>开始录音</p>
              </div>
              <div className="flex items-center gap-3 bg-white/10 rounded-[12px] p-3">
                <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-black text-xs">3</span>
                </div>
                <p className="text-white text-sm font-bold"><span className="text-[#1CB0F6]">用英语回答</span>老师的问题</p>
              </div>
            </div>
          </div>

          {/* 提示 */}
          <div className="bg-white/5 rounded-[16px] p-3 border border-white/10">
            <p className="text-xs font-bold text-white/70 text-center">
              💡 提示：建议使用耳机，避免录制到播放的声音
            </p>
          </div>
        </div>

        {/* 底部按钮 */}
        <button
          onClick={() => setShowStartGuide(false)}
          className="w-full max-w-sm py-5 bg-[#FFF59D] text-[#002FA7] font-black text-xl rounded-[28px] border-b-[6px] border-[#FBC02D] active:translate-y-[6px] active:border-b-0 transition-all shadow-xl flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-6 h-6" />
          我知道了，开始答题
        </button>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="h-screen flex flex-col items-center justify-center p-6 text-center bg-[#002FA7]">
        <div className="text-red-400 text-xl font-bold mb-4">😞 加载失败</div>
        <div className="text-white/80 mb-6 max-w-md">{loadError}</div>
        <div className="flex gap-3">
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-[#FFF59D] text-[#002FA7] rounded-xl font-bold"
          >
            重试
          </button>
          <button
            onClick={() => window.location.href = '/s/'}
            className="px-6 py-3 bg-white/20 text-white rounded-xl font-bold border border-white/30"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  if (showTransition) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-between p-10 pt-12 animate-in fade-in duration-700 overflow-hidden relative bg-[#002FA7]">

        <div className="flex-1 flex flex-col items-center justify-center space-y-10 text-center z-10 w-full max-sm:max-w-sm">
          <div className="relative w-full h-64 flex items-center justify-center mb-6">
            <img
              src={`${import.meta.env.BASE_URL}Dynamic%20materials/Settlement%20page.gif?t=123456`}
              alt="Celebration"
              className="w-full max-w-sm h-64 object-contain drop-shadow-2xl"
            />
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <h1 className="text-5xl font-black tracking-tight text-white drop-shadow-sm">第一部分完成!</h1>
              <div className="flex justify-center gap-2">
                {[...Array(3)].map((_, i) => <Star key={i} className="w-8 h-8 text-[#FFD200] fill-current animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />)}
              </div>
            </div>

            <div className="space-y-3 px-4">
              <p className="text-3xl font-black text-[#58CC02]">宝贝，你真棒！</p>
              <p className="text-white/80 font-black text-lg leading-relaxed">
                准备好开始<span className="text-[#FFF59D]">对话环节</span>了吗？
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            setShowTransition(false);
            setCurrentPart(2);
            setCurrentIndex(20);
            setShowPart2Guide(true); // 重置指引显示
          }}
          className="w-full max-w-sm py-6 bg-[#FFF59D] text-[#002FA7] font-black text-2xl rounded-[35px] border-b-8 border-[#FBC02D] active:translate-y-2 active:border-b-0 transition-all uppercase shadow-[0_20px_40px_rgba(255,245,157,0.3)] z-10 mb-10 hover:scale-[1.02] active:scale-95 flex items-center justify-center gap-3 group"
        >
          开始对话环节 <ChevronRight className="w-8 h-8 group-hover:translate-x-1 transition-transform" strokeWidth={3} />
        </button>
      </div>
    );
  }

  const currentQ = questions[currentIndex];
  const isPartDialogue = currentPart === 2;

  // 只有在最后一页且已录音才能退出
  const isLastQuestion = currentIndex === questions.length - 1;
  const hasCompletedRecording = audios.length === questions.length;
  const canExit = isLastQuestion && hasCompletedRecording;

  const handleExitClick = () => {
    if (!canExit) {
      alert("请完成所有录音后再退出");
      return;
    }
    onExit();
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center p-4 sm:p-6 pt-6 sm:pt-10 bg-[#002FA7]">
      <div className="w-full max-w-md mb-8 sm:mb-12 flex items-center gap-3 sm:gap-4">
        <button
          onClick={handleExitClick}
          className={`text-[#1E293B] p-1 ${canExit ? 'hover:text-[#1E293B]/80' : 'opacity-30 cursor-not-allowed'}`}
        >
          <X className="w-8 h-8" strokeWidth={3} />
        </button>
        <div className="flex-1"><ProgressBar current={partCurrent} total={partTotal} /></div>
        <span className="text-base font-black text-[#1E293B]">{partCurrent}/{partTotal}</span>
      </div>

      <div className="absolute left-7 top-[100px]">
        <span className="text-[14px] font-black text-[#1E293B] bg-blue-100 px-3 py-1 rounded-full">
          {currentPart === 1 ? "核心词汇挑战" : "回答老师的问题"}
        </span>
      </div>

      <main className="flex-1 w-full max-w-md flex flex-col items-center">
        <div
          className="w-full flex-1 flex flex-col items-center justify-center relative select-none cursor-grab active:cursor-grabbing"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          onMouseDown={(e) => {
            touchEndRef.current = null;
            touchStartRef.current = e.clientX;
          }}
          onMouseMove={(e) => {
            if (touchStartRef.current !== null) {
              touchEndRef.current = e.clientX;
            }
          }}
          onMouseUp={() => {
            onTouchEnd();
            touchStartRef.current = null;
            touchEndRef.current = null;
          }}
          onMouseLeave={() => {
            if (touchStartRef.current !== null) {
              onTouchEnd();
              touchStartRef.current = null;
              touchEndRef.current = null;
            }
          }}
        >

          {/* 对话环节现在也有左右翻页箭头 */}
          {isPartDialogue ? (
            <div className="flex flex-col items-center w-full relative">
                      {/* Part 2 简短提示 - 自动消失 */}
                      {showPart2Guide && currentIndex === startIdx && (
                <div className="mb-4 p-3 bg-[#1CB0F6]/20 rounded-[16px] border border-[#1CB0F6]/40 max-w-sm animate-in fade-in slide-in-from-top-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
                      <Play className="w-4 h-4 text-white" fill="currentColor" />
                    </div>
                    <div className="flex-1">
                      <p className="font-black text-[#1E293B] text-sm">问题即将自动播放</p>
                      <p className="text-xs font-bold text-[#1E293B]/60">听完后点击麦克风开始回答</p>
                    </div>
                    <button
                      onClick={() => setShowPart2Guide(false)}
                      className="text-[#1CB0F6] font-black text-xs px-2 py-1 rounded hover:bg-[#1CB0F6]/10"
                    >
                      知道了
                    </button>
                  </div>
                </div>
              )}

              <div className="flex flex-col items-center">
                <SpeechBubble
                  text={currentQ.text}
                  onPlayAudio={() => playEnglishAudio(currentQ.text)}
                  isRecording={isRecording}
                  isAudioPlaying={isAudioPlaying}
                  onAudioStateChange={(playing) => setIsAudioPlaying(playing)}
                />
                {/* 对话环节下方的猴子 */}
                <div className="mt-4 flex items-center justify-center">
                  <img 
                    src={`${import.meta.env.BASE_URL}Dynamic materials/3.gif`} 
                    alt="Monkey" 
                    className="w-64 h-64 sm:w-80 sm:h-80 object-contain drop-shadow-lg"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="w-full flex flex-col items-center justify-center relative touch-pan-y">
              {/* 隐藏按钮但保留滑动功能 */}

              {/* 图片和文字容器 - 移除分割线 */}
              <div className="flex flex-col items-center gap-2">
                <div className="relative flex items-center justify-center">
                  {currentQ.image ? (
                    <img src={currentQ.image} className="w-64 h-64 object-contain drop-shadow-2xl" alt="" referrerPolicy="no-referrer" />
                  ) : (
                    <div className="w-64 h-64 flex items-center justify-center">
                      <div className="text-3xl font-black text-[#1E293B] px-6 text-center leading-relaxed">{currentQ.text}</div>
                    </div>
                  )}
                </div>

                {/* 文字信息 - 紧贴图片无分割 */}
                {currentQ.translation && (
                  <div className="text-center">
                    <div className="font-black text-[#1E293B] text-4xl tracking-tight mb-1">{currentQ.text}</div>
                    <p className="text-xl font-black text-[#1E293B]/20 italic">{currentQ.translation}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="w-full flex flex-col items-center gap-4 pb-10">
          {/* 未开始录音：显示开始按钮 */}
          {!isRecording && audios.length <= startIdx ? (
            <CircularRecordButton
              onClick={startRecording}
              variant={currentPart === 1 ? "yellow" : "blue"}
            />
          ) : isRecording && currentIndex === endIdx ? (
            /* 录音中且在最后一页：显示红色停止按钮 */
            <CircularRecordButton onClick={stopRecording} variant="red" isRecording={true} />
          ) : isRecording ? (
            /* 录音中但不在最后一页：显示脉动效果（不可点击） */
            <div className={`w-20 h-20 rounded-[24px] border-b-[6px] flex items-center justify-center animate-pulse shadow-xl pointer-events-none ${currentPart === 1 ? 'bg-[#FFD200] border-[#E5A000]' : 'bg-[#1CB0F6] border-[#1899D6]'}`}>
              <div className="w-6 h-6 bg-white rounded-full relative z-10 shadow-inner"></div>
            </div>
          ) : (
            /* 录音已完成：显示脉动效果 */
            <div className={`w-20 h-20 rounded-[24px] border-b-[6px] flex items-center justify-center shadow-xl pointer-events-none ${currentPart === 1 ? 'bg-[#FFD200] border-[#E5A000]' : 'bg-[#1CB0F6] border-[#1899D6]'}`}>
              <div className="w-6 h-6 bg-white rounded-full relative z-10 shadow-inner opacity-50"></div>
            </div>
          )}
          <p className="text-[13px] font-black text-[#1E293B]/40 uppercase tracking-widest text-center">
            {isPartDialogue
              ? (isRecording
                ? (currentIndex === endIdx ? "到达最后一页，点击红色按钮关闭录音" : "录音中，可以滑动屏幕查看其他问题")
                : (audios.length > startIdx ? "录音已完成，您可以继续翻页" : "问题会自动播放，点击麦克风开始回答"))
              : (isRecording
                ? (currentIndex === endIdx ? "到达最后一页，点击红色按钮关闭录音" : "录音中，可以滑动屏幕浏览单词")
                : (audios.length > startIdx ? "录音已完成，您可以继续翻页" : "点击麦克风开始录音并滑动屏幕"))}
          </p>
        </div>
      </main>
    </div>
  );
};

export default TestPage;

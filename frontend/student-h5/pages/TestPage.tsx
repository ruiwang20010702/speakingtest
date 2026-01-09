
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
              ? 'bg-[#46DDF0]/30 cursor-not-allowed'
              : 'bg-gradient-to-r from-[#46DDF0] to-[#1CB0F6] hover:from-[#46DDF0]/90 hover:to-[#1CB0F6]/90 shadow-md'
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
    blue: "bg-[#1CB0F6] border-[#1899D6] text-white",
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
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentPart, setCurrentPart] = useState(1);
  const [audios, setAudios] = useState<Blob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showTransition, setShowTransition] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showPart2Guide, setShowPart2Guide] = useState(true);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);

  // 滑动相关状态
  const minSwipeDistance = 50;

  useEffect(() => {
    const fetch = async () => {
      const q = await getQuestions(level, unit);
      setQuestions(q);
      setIsLoading(false);
    };
    fetch();

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

  if (isLoading) return <div className="h-screen flex items-center justify-center font-black text-[#1CB0F6]">加载中...</div>;

  if (showTransition) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-between p-10 pt-12 animate-in fade-in duration-700 overflow-hidden relative bg-white">

        <div className="flex-1 flex flex-col items-center justify-center space-y-10 text-center z-10 w-full max-sm:max-w-sm">
          <div className="relative w-full h-64 flex items-center justify-center mb-6">
            <img
              src="/Dynamic%20materials/Settlement%20page.gif?t=123456"
              alt="Celebration"
              className="w-full max-w-sm h-64 object-contain drop-shadow-2xl"
            />
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <h1 className="text-5xl font-black tracking-tight text-[#1E293B] drop-shadow-sm">第一部分完成!</h1>
              <div className="flex justify-center gap-2">
                {[...Array(3)].map((_, i) => <Star key={i} className="w-8 h-8 text-[#FFD200] fill-current animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />)}
              </div>
            </div>

            <div className="space-y-3 px-4">
              <p className="text-3xl font-black text-[#58CC02]">宝贝，你真棒！</p>
              <p className="text-[#1E293B]/60 font-black text-lg leading-relaxed">
                准备好开始<span className="text-[#1CB0F6]">对话环节</span>了吗？
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
          className="w-full max-w-sm py-6 bg-[#1CB0F6] text-white font-black text-2xl rounded-[35px] border-b-8 border-[#1899D6] active:translate-y-2 active:border-b-0 transition-all uppercase shadow-[0_20px_40px_rgba(28,176,246,0.3)] z-10 mb-10 hover:scale-[1.02] active:scale-95 flex items-center justify-center gap-3 group"
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
    <div className="min-h-screen w-full flex flex-col items-center p-4 sm:p-6 pt-6 sm:pt-10 bg-white">
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
              {/* Part 2 指引提示 */}
              {showPart2Guide && currentIndex === startIdx && (
                <div className="mb-6 p-5 bg-gradient-to-r from-[#1CB0F6]/10 to-[#58CC02]/10 rounded-[24px] border-2 border-[#1CB0F6]/40 max-w-sm animate-in fade-in slide-in-from-top-4 shadow-lg">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
                        <Info className="w-6 h-6 text-white" />
                      </div>
                      <h4 className="font-black text-[#1E293B] text-base">📚 操作步骤</h4>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-start gap-3 bg-white/60 rounded-[16px] p-3 border border-[#1CB0F6]/20">
                        <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-white font-black text-xs">1</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Play className="w-4 h-4 text-[#1CB0F6]" fill="currentColor" />
                            <span className="font-black text-[#1E293B] text-sm">问题会自动播放</span>
                          </div>
                          <p className="text-xs font-bold text-[#1E293B]/60">仔细听清楚老师问什么</p>
                        </div>
                      </div>

                      <div className="flex items-start gap-3 bg-white/60 rounded-[16px] p-3 border border-[#1CB0F6]/20">
                        <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-white font-black text-xs">2</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Mic className="w-4 h-4 text-[#1CB0F6]" />
                            <span className="font-black text-[#1E293B] text-sm">点击蓝色麦克风</span>
                          </div>
                          <p className="text-xs font-bold text-[#1E293B]/60">开始录音，用英语回答</p>
                        </div>
                      </div>

                      <div className="flex items-start gap-3 bg-white/60 rounded-[16px] p-3 border border-[#1CB0F6]/20">
                        <div className="w-6 h-6 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-white font-black text-xs">3</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <ChevronRight className="w-4 h-4 text-[#1CB0F6]" />
                            <span className="font-black text-[#1E293B] text-sm">左右滑动屏幕</span>
                          </div>
                          <p className="text-xs font-bold text-[#1E293B]/60">查看下一个问题（会自动播放）</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-[#FFD200]/20 rounded-[12px] p-3 border border-[#FFD200]/30">
                      <p className="text-xs font-bold text-[#1E293B]/70 text-center">
                        💡 提示：建议使用耳机，避免录制到播放的声音
                      </p>
                    </div>

                    <button
                      onClick={() => setShowPart2Guide(false)}
                      className="w-full py-2.5 bg-[#1CB0F6] text-white font-black text-sm rounded-[16px] active:scale-95 transition-transform shadow-md"
                    >
                      ✓ 我知道了，开始答题
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

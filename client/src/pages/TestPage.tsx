/**
 * 测试页面 - 51Talk 新设计
 * 显示题目并进行三个部分的录音
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getQuestions, evaluateTest } from '../services/api';
import type { QuestionData } from '../types';
import { Mic, Square, Play, Pause, ChevronRight, ChevronLeft, CheckCircle2 } from 'lucide-react';

export default function TestPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const studentName = searchParams.get('student') || '';
    const level = searchParams.get('level') || 'level1';
    const unit = searchParams.get('unit') || 'unit1-3';

    const [questions, setQuestions] = useState<QuestionData | null>(null);
    const [currentPart, setCurrentPart] = useState(1);
    const [recordings, setRecordings] = useState<{
        part1?: Blob;
        part2?: Blob;
    }>({});

    // Part 3 专用状态
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [part3Recordings, setPart3Recordings] = useState<Record<number, Blob>>({});

    // 录音状态
    const [isRecording, setIsRecording] = useState(false);
    const [isPaused, setIsPaused] = useState(false); // 新增：暂停状态
    const [recordingTime, setRecordingTime] = useState(0);
    const [audioURL, setAudioURL] = useState<string | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [recordingError, setRecordingError] = useState<string | null>(null);
    const [audioSegments, setAudioSegments] = useState<Blob[]>([]); // 新增：存储多段录音

    // Part 1/2 切换状态
    const [currentGroup, setCurrentGroup] = useState<1 | 2>(1);
    const [showSentences, setShowSentences] = useState(false);

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null); // 新增：保存音频流引用
    const audioChunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        loadQuestions();
    }, [level, unit]);

    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
            if (audioURL) {
                URL.revokeObjectURL(audioURL);
            }
        };
    }, [audioURL]);

    // 切换 Part 时重置录音状态
    useEffect(() => {
        setRecordingTime(0);
        setIsPlaying(false);
        setRecordingError(null);
        setAudioSegments([]); // 清空录音片段
        setIsPaused(false);

        // 恢复已有录音
        const existingBlob = recordings[`part${currentPart}` as keyof typeof recordings];
        if (existingBlob) {
            setAudioURL(URL.createObjectURL(existingBlob));
        } else {
            setAudioURL(null);
        }
    }, [currentPart]);

    const loadQuestions = async () => {
        try {
            const data = await getQuestions(level, unit);
            setQuestions(data);
        } catch (err) {
            setError('加载题目失败，请刷新重试');
            console.error(err);
        }
    };

    // 开始录音（支持继续追加录音）
    const startRecording = async (isContinuing: boolean = false) => {
        try {
            setRecordingError(null);
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    noiseSuppression: true,
                    echoCancellation: true,
                    autoGainControl: true
                }
            });
            streamRef.current = stream;
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            // 如果是全新录音（不是继续录音），清空之前的片段
            if (!isContinuing) {
                setAudioSegments([]);
            }

            mediaRecorder.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const currentSegment = new Blob(audioChunksRef.current, { type: 'audio/webm' });

                // 合并所有片段（包括之前的）
                setAudioSegments(prev => {
                    const allSegments = [...prev, currentSegment];
                    const mergedBlob = new Blob(allSegments, { type: 'audio/webm' });
                    const url = URL.createObjectURL(mergedBlob);
                    setAudioURL(url);

                    if (currentPart === 3) {
                        setPart3Recordings(prevRec => ({
                            ...prevRec,
                            [currentQuestionIndex]: mergedBlob
                        }));
                    } else {
                        setRecordings(prevRec => ({
                            ...prevRec,
                            [`part${currentPart}`]: mergedBlob
                        }));
                    }

                    return allSegments;
                });

                stream.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            };

            mediaRecorder.start(100); // 每100ms收集一次数据
            setIsRecording(true);
            setIsPaused(false);

            // 如果不是继续录音，重置时间
            if (!isContinuing) {
                setRecordingTime(0);
            }

            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        } catch (err) {
            if (err instanceof DOMException) {
                if (err.name === 'NotAllowedError') {
                    setRecordingError('麦克风权限被拒绝。请在浏览器设置中允许麦克风访问权限。');
                } else if (err.name === 'NotFoundError') {
                    setRecordingError('未找到麦克风设备。请确保您的设备有可用的麦克风。');
                } else {
                    setRecordingError('无法访问麦克风。请检查设备和权限设置。');
                }
            } else {
                setRecordingError('无法访问麦克风。请检查设备和权限设置。');
            }
        }
    };

    // 暂停录音
    const pauseRecording = () => {
        if (mediaRecorderRef.current && isRecording && !isPaused) {
            mediaRecorderRef.current.pause();
            setIsPaused(true);
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    // 恢复录音
    const resumeRecording = () => {
        if (mediaRecorderRef.current && isRecording && isPaused) {
            mediaRecorderRef.current.resume();
            setIsPaused(false);
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        }
    };

    // 继续追加录音（录音完成后）
    const continueRecording = () => {
        startRecording(true);
    };

    // 重新录音（清空所有）
    const resetRecording = () => {
        if (audioURL) {
            URL.revokeObjectURL(audioURL);
        }
        setAudioURL(null);
        setAudioSegments([]);
        setRecordingTime(0);
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            setIsPaused(false);
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    const togglePlayback = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
                setIsPlaying(false);
            } else {
                audioRef.current.play();
                setIsPlaying(true);
            }
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const handleNext = () => {
        if (!recordings[`part${currentPart}` as keyof typeof recordings]) {
            alert('请先完成录音');
            return;
        }
        if (currentPart < 3) {
            setCurrentPart(currentPart + 1);
            setAudioURL(null);
            setCurrentGroup(1);
            setShowSentences(false);
        }
    };

    const goToNextQuestion = () => {
        if (!part3Recordings[currentQuestionIndex]) {
            alert('请先完成当前问题的录音');
            return;
        }
        const dialogues = questions?.parts.find(p => p.part_id === 3)?.dialogues;
        if (dialogues && currentQuestionIndex < dialogues.length - 1) {
            setCurrentQuestionIndex(currentQuestionIndex + 1);
            setAudioURL(null);
            setRecordingTime(0);
            setIsPlaying(false);
            setAudioSegments([]); // 清空录音片段
        }
    };

    const goToPrevQuestion = () => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(currentQuestionIndex - 1);
            const existingBlob = part3Recordings[currentQuestionIndex - 1];
            if (existingBlob) {
                setAudioURL(URL.createObjectURL(existingBlob));
            } else {
                setAudioURL(null);
            }
            setRecordingTime(0);
            setIsPlaying(false);
            setAudioSegments([]); // 清空录音片段
        }
    };

    const handleSubmit = async () => {
        if (!recordings.part1 || !recordings.part2) {
            alert('请完成 Part 1 和 Part 2 的录音');
            return;
        }

        const dialogues = questions?.parts.find(p => p.part_id === 3)?.dialogues;
        const totalQuestions = dialogues?.length || 12;
        const completedPart3 = Object.keys(part3Recordings).length;

        if (completedPart3 < totalQuestions) {
            alert(`请完成所有 ${totalQuestions} 个问题的录音（已完成 ${completedPart3} 个）`);
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const part1File = new File([recordings.part1], 'part1.webm', { type: 'audio/webm' });
            const part2File = new File([recordings.part2], 'part2.webm', { type: 'audio/webm' });

            // 将12个问题的录音合并成2个分组
            // Group 1: 问题1-6
            const group1Blobs: Blob[] = [];
            for (let i = 0; i < 6; i++) {
                const blob = part3Recordings[i];
                if (blob) {
                    group1Blobs.push(blob);
                }
            }
            const group1Merged = new Blob(group1Blobs, { type: 'audio/webm' });
            const part3Group1File = new File([group1Merged], 'part3_group1.webm', { type: 'audio/webm' });

            // Group 2: 问题7-12
            const group2Blobs: Blob[] = [];
            for (let i = 6; i < 12; i++) {
                const blob = part3Recordings[i];
                if (blob) {
                    group2Blobs.push(blob);
                }
            }
            const group2Merged = new Blob(group2Blobs, { type: 'audio/webm' });
            const part3Group2File = new File([group2Merged], 'part3_group2.webm', { type: 'audio/webm' });

            const result = await evaluateTest(
                studentName,
                level,
                unit,
                part1File,
                part2File,
                part3Group1File,
                part3Group2File
            );

            navigate(`/result?id=${result.id}`);
        } catch (err: any) {
            setError(err.response?.data?.detail || '评分失败，请重试');
            console.error(err);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!questions) {
        return (
            <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
                <div className="absolute inset-0 bg-[#00B4EE]">
                    <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                </div>
                <div className="relative z-10 min-h-screen flex items-center justify-center">
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-8 text-center">
                        <div className="w-16 h-16 border-4 border-[#FDE700] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-gray-600">加载中...</p>
                    </div>
                </div>
            </div>
        );
    }

    const currentPartData = questions.parts.find(p => p.part_id === currentPart);
    const part3Dialogues = questions.parts.find(p => p.part_id === 3)?.dialogues;

    return (
        <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
            {/* Blue Background with decorative elements */}
            <div className="absolute inset-0 bg-[#00B4EE]">
                <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                <div className="absolute bottom-0 left-0 w-48 h-32">
                    <div className="absolute bottom-4 left-0 w-24 h-24 bg-white rounded-full -translate-x-1/3" />
                    <div className="absolute bottom-8 left-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute bottom-12 left-6 w-16 h-16 bg-white rounded-full" />
                </div>
                <div className="absolute top-0 right-0 w-48 h-32">
                    <div className="absolute top-4 right-0 w-24 h-24 bg-white rounded-full translate-x-1/3" />
                    <div className="absolute top-8 right-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute top-12 right-6 w-16 h-16 bg-white rounded-full" />
                </div>
                <div className="absolute bottom-0 right-0 w-40 h-40 bg-[#FDE700] translate-x-1/4 translate-y-1/4" style={{ clipPath: 'polygon(0 100%, 100% 100%, 100% 0)' }} />
            </div>

            {/* Content */}
            <div className="relative z-10 p-3 pb-6">
                <div className="max-w-md mx-auto">
                    {/* Header */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                        <div className="flex items-center justify-between mb-1">
                            <h1 className="text-lg font-semibold text-gray-900">
                                Part {currentPart} - {currentPart === 1 ? '词汇' : currentPart === 2 ? 'Phonics' : '深度讨论'}
                            </h1>
                            <span className="px-3 py-1 bg-[#FDE700] text-gray-900 rounded-full text-sm font-medium">
                                {currentPart === 1 ? '词汇阅读' : currentPart === 2 ? '语音朗读' : '深度讨论'}
                            </span>
                        </div>
                        <p className="text-gray-600 text-sm">学生: {studentName}</p>
                        <p className="text-gray-600 text-sm">{questions.level_name} - {questions.unit_name}</p>
                    </div>

                    {/* Part 1 - 词汇 */}
                    {currentPart === 1 && currentPartData?.items && (
                        <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                            <h2 className="text-lg font-semibold text-gray-900 mb-1">
                                词汇列表 {currentGroup === 1 ? `(1-${Math.ceil(currentPartData.items.length / 2)})` : `(${Math.ceil(currentPartData.items.length / 2) + 1}-${currentPartData.items.length})`}
                            </h2>
                            <p className="text-gray-500 text-sm mb-3">Read the following words aloud.</p>

                            <div className="grid grid-cols-2 gap-2 mb-3">
                                {currentPartData.items
                                    .slice(
                                        currentGroup === 1 ? 0 : Math.ceil(currentPartData.items.length / 2),
                                        currentGroup === 1 ? Math.ceil(currentPartData.items.length / 2) : currentPartData.items.length
                                    )
                                    .map((item, index) => {
                                        const actualIndex = currentGroup === 1 ? index : index + Math.ceil(currentPartData.items!.length / 2);
                                        return (
                                            <div
                                                key={item.id}
                                                className="p-3 bg-gradient-to-br from-[#E3F2FD] to-white rounded-xl border border-[#00B4EE]/20"
                                            >
                                                <p className="text-gray-700 text-sm">
                                                    <span className="text-gray-500">{actualIndex + 1}. </span>
                                                    {item.word}
                                                </p>
                                            </div>
                                        );
                                    })}
                            </div>

                            <button
                                onClick={() => setCurrentGroup(currentGroup === 1 ? 2 : 1)}
                                className={`w-full py-2.5 rounded-lg hover:shadow-md transition-all active:scale-95 ${currentGroup === 1
                                        ? 'bg-[#FDE700] text-gray-900'
                                        : 'bg-white text-gray-900 border border-gray-200'
                                    }`}
                            >
                                {currentGroup === 1 ? `下部分词汇 (${Math.ceil(currentPartData.items.length / 2) + 1}-${currentPartData.items.length})` : `上部分词汇 (1-${Math.ceil(currentPartData.items.length / 2)})`}
                            </button>
                        </div>
                    )}

                    {/* Part 2 - Phonics */}
                    {currentPart === 2 && (
                        <>
                            {!showSentences && currentPartData?.words && (
                                <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                                    <h3 className="text-[#00B4EE] font-semibold mb-1">单词 (Words)</h3>
                                    <p className="text-gray-500 text-sm mb-3">Read the following words aloud.</p>
                                    <div className="grid grid-cols-2 gap-2 mb-4">
                                        {currentPartData.words.map((item, index) => (
                                            <div
                                                key={item.id}
                                                className="p-3 bg-gradient-to-br from-[#E3F2FD] to-white rounded-xl border border-[#00B4EE]/20"
                                            >
                                                <p className="text-gray-700 text-sm">
                                                    <span className="text-gray-500">{index + 1}. </span>
                                                    {item.word}
                                                </p>
                                            </div>
                                        ))}
                                    </div>

                                    <button
                                        onClick={() => setShowSentences(true)}
                                        className="w-full py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-md transition-all flex items-center justify-center gap-2"
                                    >
                                        <span>下一部分: 句子</span>
                                        <ChevronRight className="w-5 h-5" />
                                    </button>
                                </div>
                            )}

                            {showSentences && currentPartData?.sentences && (
                                <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                                    <h3 className="text-[#00B4EE] font-semibold mb-1">句子 (Sentences)</h3>
                                    <p className="text-gray-500 text-sm mb-3">Read the following sentences aloud.</p>
                                    <div className="space-y-2 mb-4">
                                        {currentPartData.sentences.map((item, index) => (
                                            <div
                                                key={item.id}
                                                className="p-3 bg-gradient-to-r from-[#E3F2FD] to-white rounded-xl border-l-4 border-[#00B4EE]"
                                            >
                                                <p className="text-gray-700 text-sm">
                                                    <span className="text-gray-500">{(currentPartData.words?.length || 0) + index + 1}. </span>
                                                    {item.text}
                                                </p>
                                            </div>
                                        ))}
                                    </div>

                                    <button
                                        onClick={() => setShowSentences(false)}
                                        className="w-full py-3 bg-white text-gray-900 font-medium rounded-xl hover:shadow-md transition-all flex items-center justify-center gap-2 border border-gray-200"
                                    >
                                        <ChevronLeft className="w-5 h-5" />
                                        <span>上一部分: 单词</span>
                                    </button>
                                </div>
                            )}
                        </>
                    )}

                    {/* Part 3 - 深度讨论 */}
                    {currentPart === 3 && part3Dialogues && (
                        <>
                            {/* Progress */}
                            <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-gray-700 text-sm">进度</span>
                                    <span className="text-gray-900 font-medium">
                                        {currentQuestionIndex + 1} / {part3Dialogues.length}
                                    </span>
                                </div>
                                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-[#FDE700] transition-all duration-300"
                                        style={{ width: `${((currentQuestionIndex + 1) / part3Dialogues.length) * 100}%` }}
                                    />
                                </div>
                            </div>

                            {/* Question Card */}
                            <div className="bg-gradient-to-br from-white/95 to-white/90 backdrop-blur rounded-2xl shadow-xl p-6 mb-3 min-h-[200px] flex flex-col justify-center border-l-4 border-[#00B4EE]">
                                <div className="flex items-start gap-3 mb-4">
                                    <div className="flex-shrink-0 w-10 h-10 bg-[#00B4EE] rounded-full flex items-center justify-center text-white">
                                        {part3Recordings[currentQuestionIndex] ? (
                                            <CheckCircle2 className="w-6 h-6" />
                                        ) : (
                                            <span className="font-medium">{currentQuestionIndex + 1}</span>
                                        )}
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-gray-500 text-sm mb-2">Question {currentQuestionIndex + 1}</p>
                                        <p className="text-gray-900 text-lg leading-relaxed">
                                            {part3Dialogues[currentQuestionIndex].teacher}
                                        </p>
                                    </div>
                                </div>

                                {part3Recordings[currentQuestionIndex] && (
                                    <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-xl">
                                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                                        <span className="text-green-700 text-sm">已录音</span>
                                    </div>
                                )}
                            </div>

                            {/* Navigation Dots */}
                            <div className="flex justify-center gap-2 mb-3">
                                {part3Dialogues.map((_, index) => (
                                    <button
                                        key={index}
                                        onClick={() => {
                                            setCurrentQuestionIndex(index);
                                            const existingBlob = part3Recordings[index];
                                            if (existingBlob) {
                                                setAudioURL(URL.createObjectURL(existingBlob));
                                            } else {
                                                setAudioURL(null);
                                            }
                                            setRecordingTime(0);
                                            setIsPlaying(false);
                                        }}
                                        className={`w-2 h-2 rounded-full transition-all ${index === currentQuestionIndex
                                                ? 'w-6 bg-[#00B4EE]'
                                                : part3Recordings[index]
                                                    ? 'bg-[#FDE700]'
                                                    : 'bg-gray-300'
                                            }`}
                                    />
                                ))}
                            </div>
                        </>
                    )}

                    {/* Recording Controls */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4">
                        <h2 className="text-lg font-semibold text-gray-900 mb-3">录音</h2>

                        <div className="flex flex-col items-center gap-3">
                            {/* Recording Status & Time */}
                            <div className="flex items-center gap-3">
                                {isRecording && (
                                    <span className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${isPaused
                                            ? 'bg-yellow-100 text-yellow-700'
                                            : 'bg-red-100 text-red-700'
                                        }`}>
                                        <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-red-500 animate-pulse'
                                            }`}></span>
                                        {isPaused ? '已暂停' : '录音中'}
                                    </span>
                                )}
                                <div className="text-3xl text-gray-900 tabular-nums font-mono">
                                    {formatTime(recordingTime)}
                                </div>
                            </div>

                            {/* 片段计数 */}
                            {audioSegments.length > 1 && !isRecording && (
                                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                                    📎 已合并 {audioSegments.length} 段录音
                                </span>
                            )}

                            {/* Recording Buttons */}
                            {!isRecording && !audioURL && (
                                <button
                                    onClick={() => startRecording(false)}
                                    className="w-16 h-16 bg-gradient-to-br from-red-500 to-pink-600 rounded-full flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all active:scale-95"
                                >
                                    <Mic className="w-7 h-7" />
                                </button>
                            )}

                            {/* 录音中的控制按钮 */}
                            {isRecording && (
                                <div className="flex items-center gap-3">
                                    {/* 暂停/继续按钮 */}
                                    {!isPaused ? (
                                        <button
                                            onClick={pauseRecording}
                                            className="w-14 h-14 bg-yellow-500 rounded-full flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all active:scale-95"
                                            title="暂停"
                                        >
                                            <Pause className="w-6 h-6" />
                                        </button>
                                    ) : (
                                        <button
                                            onClick={resumeRecording}
                                            className="w-14 h-14 bg-green-500 rounded-full flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all active:scale-95"
                                            title="继续"
                                        >
                                            <Play className="w-6 h-6" />
                                        </button>
                                    )}

                                    {/* 完成按钮 */}
                                    <button
                                        onClick={stopRecording}
                                        className="w-14 h-14 bg-gray-800 rounded-full flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all active:scale-95"
                                        title="完成"
                                    >
                                        <Square className="w-6 h-6" />
                                    </button>
                                </div>
                            )}

                            <p className="text-gray-600 text-sm">
                                {!audioURL && !isRecording && '点击开始录音'}
                                {isRecording && !isPaused && '录音中...'}
                                {isRecording && isPaused && '已暂停，点击继续或完成'}
                                {audioURL && !isRecording && '录音完成'}
                            </p>

                            {/* Error Message */}
                            {recordingError && (
                                <div className="w-full p-3 bg-red-50 border border-red-200 rounded-xl">
                                    <p className="text-red-700 text-sm">{recordingError}</p>
                                    <p className="text-red-600 text-xs mt-1">
                                        如何开启麦克风权限：<br />
                                        • 点击浏览器地址栏左侧的锁图标<br />
                                        • 找到麦克风权限并设置为"允许"<br />
                                        • 刷新页面后重试
                                    </p>
                                </div>
                            )}

                            {/* Playback & Controls */}
                            {audioURL && !isRecording && (
                                <div className="w-full mt-2 space-y-2">
                                    <audio
                                        ref={audioRef}
                                        src={audioURL}
                                        onEnded={() => setIsPlaying(false)}
                                        className="hidden"
                                    />

                                    {/* 播放按钮 */}
                                    <button
                                        onClick={togglePlayback}
                                        className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 rounded-xl flex items-center justify-center gap-2 transition-colors"
                                    >
                                        {isPlaying ? (
                                            <>
                                                <Pause className="w-5 h-5" />
                                                <span>暂停播放</span>
                                            </>
                                        ) : (
                                            <>
                                                <Play className="w-5 h-5" />
                                                <span>播放录音</span>
                                            </>
                                        )}
                                    </button>

                                    {/* 继续录音 & 重新录音按钮 */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={continueRecording}
                                            className="flex-1 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-xl flex items-center justify-center gap-2 transition-colors font-medium"
                                        >
                                            <span>➕</span>
                                            <span>继续录音</span>
                                        </button>
                                        <button
                                            onClick={resetRecording}
                                            className="flex-1 py-2.5 bg-white border border-gray-200 hover:bg-gray-50 rounded-xl text-gray-700 text-sm transition-colors"
                                        >
                                            🔄 重新录音
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Navigation Buttons */}
                    {currentPart !== 3 && (
                        <div className="mt-3 flex gap-3">
                            <button
                                onClick={() => currentPart > 1 ? setCurrentPart(currentPart - 1) : navigate('/')}
                                className="flex-1 py-4 bg-white/95 backdrop-blur text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 border border-gray-200"
                            >
                                <ChevronLeft className="w-5 h-5" />
                                <span>{currentPart > 1 ? '返回' : '首页'}</span>
                            </button>
                            <button
                                onClick={handleNext}
                                disabled={currentPart === 1 ? currentGroup === 1 : !showSentences}
                                className={`flex-1 py-4 rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 ${(currentPart === 1 && currentGroup === 2) || (currentPart === 2 && showSentences)
                                        ? 'bg-[#FDE700] text-gray-900'
                                        : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    }`}
                            >
                                <span>进入 Part {currentPart + 1}</span>
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        </div>
                    )}

                    {/* Part 3 Navigation */}
                    {currentPart === 3 && part3Dialogues && (
                        <>
                            <div className="flex gap-3 mt-3">
                                <button
                                    onClick={goToPrevQuestion}
                                    disabled={currentQuestionIndex === 0}
                                    className="flex-1 py-3 bg-white/95 backdrop-blur hover:bg-white rounded-xl flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-200"
                                >
                                    <ChevronLeft className="w-5 h-5" />
                                    <span>上一题</span>
                                </button>

                                {currentQuestionIndex === part3Dialogues.length - 1 ? (
                                    <button
                                        onClick={handleSubmit}
                                        disabled={isSubmitting || Object.keys(part3Recordings).length < part3Dialogues.length}
                                        className="flex-1 py-3 bg-[#FDE700] hover:bg-[#FDE700]/90 rounded-xl flex items-center justify-center gap-2 transition-colors text-gray-900 font-medium disabled:opacity-50"
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <div className="w-5 h-5 border-2 border-gray-900 border-t-transparent rounded-full animate-spin"></div>
                                                <span>提交中...</span>
                                            </>
                                        ) : (
                                            <span>提交测试</span>
                                        )}
                                    </button>
                                ) : (
                                    <button
                                        onClick={goToNextQuestion}
                                        className="flex-1 py-3 bg-[#FDE700] hover:bg-[#FDE700]/90 rounded-xl flex items-center justify-center gap-2 transition-colors text-gray-900 font-medium"
                                    >
                                        <span>下一题</span>
                                        <ChevronRight className="w-5 h-5" />
                                    </button>
                                )}
                            </div>

                            {/* Return to Part 2 */}
                            {currentQuestionIndex === 0 && (
                                <button
                                    onClick={() => setCurrentPart(2)}
                                    className="w-full mt-3 py-3 bg-white/95 backdrop-blur text-gray-700 rounded-xl hover:shadow-md transition-all flex items-center justify-center gap-2 border border-gray-200"
                                >
                                    <ChevronLeft className="w-5 h-5" />
                                    <span>返回 Part 2</span>
                                </button>
                            )}

                            {/* Completion hint */}
                            {currentQuestionIndex === part3Dialogues.length - 1 && (
                                <p className="text-center text-white mt-3 text-sm">
                                    已完成 {Object.keys(part3Recordings).length} / {part3Dialogues.length} 个问题的录音
                                </p>
                            )}
                        </>
                    )}

                    {error && (
                        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl">
                            <p className="text-red-700 text-sm">{error}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

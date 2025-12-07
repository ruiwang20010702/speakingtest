/**
 * 录音组件
 * 使用 MediaRecorder API 录制音频
 * 支持暂停/继续录音功能
 */
import { useState, useRef, useEffect, useCallback } from 'react';

interface AudioRecorderProps {
    onRecordingComplete: (audioBlob: Blob) => void;
    label?: string;
    existingAudio?: Blob | null; // 已存在的录音
}

type RecordingState = 'idle' | 'recording' | 'paused' | 'completed';

export default function AudioRecorder({ onRecordingComplete, label, existingAudio }: AudioRecorderProps) {
    const [recordingState, setRecordingState] = useState<RecordingState>('idle');
    const [audioURL, setAudioURL] = useState<string | null>(null);
    const [recordingTime, setRecordingTime] = useState(0);
    const [segmentCount, setSegmentCount] = useState(0);
    
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const allSegmentsRef = useRef<Blob[]>([]); // 存储所有录音片段
    const timerRef = useRef<number | null>(null);

    // 如果有已存在的录音，恢复显示
    useEffect(() => {
        if (existingAudio) {
            const url = URL.createObjectURL(existingAudio);
            setAudioURL(url);
            setRecordingState('completed');
            allSegmentsRef.current = [existingAudio];
            setSegmentCount(1);
        }
    }, [existingAudio]);

    // 清理定时器
    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        };
    }, []);

    // 格式化时间显示
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    // 合并所有录音片段
    const mergeAudioSegments = useCallback(async (segments: Blob[]): Promise<Blob> => {
        if (segments.length === 1) {
            return segments[0];
        }
        // 合并所有片段
        return new Blob(segments, { type: 'audio/webm' });
    }, []);

    // 开始录音（新录音或继续录音）
    const startRecording = async (isContinuing: boolean = false) => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    noiseSuppression: true,
                    echoCancellation: true,
                    autoGainControl: true,
                    sampleRate: 44100,
                    channelCount: 1
                }
            });
            
            streamRef.current = stream;
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            if (!isContinuing) {
                // 全新录音，清空所有片段
                allSegmentsRef.current = [];
                setSegmentCount(0);
                setRecordingTime(0);
            }

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // 将当前录音片段保存
                const currentSegment = new Blob(chunksRef.current, { type: 'audio/webm' });
                allSegmentsRef.current.push(currentSegment);
                setSegmentCount(allSegmentsRef.current.length);
                
                // 合并所有片段
                const mergedBlob = await mergeAudioSegments(allSegmentsRef.current);
                const url = URL.createObjectURL(mergedBlob);
                
                if (audioURL) {
                    URL.revokeObjectURL(audioURL);
                }
                setAudioURL(url);
                onRecordingComplete(mergedBlob);

                // 停止所有tracks
                stream.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            };

            mediaRecorder.start(100); // 每100ms收集一次数据
            setRecordingState('recording');

            // 开始计时
            timerRef.current = window.setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('无法访问麦克风，请检查权限设置');
        }
    };

    // 暂停录音
    const pauseRecording = () => {
        if (mediaRecorderRef.current && recordingState === 'recording') {
            mediaRecorderRef.current.pause();
            setRecordingState('paused');
            
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    // 继续录音（从暂停状态恢复）
    const resumeRecording = () => {
        if (mediaRecorderRef.current && recordingState === 'paused') {
            mediaRecorderRef.current.resume();
            setRecordingState('recording');
            
            // 重新开始计时
            timerRef.current = window.setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        }
    };

    // 停止录音
    const stopRecording = () => {
        if (mediaRecorderRef.current && (recordingState === 'recording' || recordingState === 'paused')) {
            mediaRecorderRef.current.stop();
            setRecordingState('completed');
            
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    // 继续追加录音（录音完成后）
    const continueRecording = () => {
        startRecording(true);
    };

    // 重置所有录音
    const resetRecording = () => {
        if (audioURL) {
            URL.revokeObjectURL(audioURL);
        }
        setAudioURL(null);
        setRecordingState('idle');
        setRecordingTime(0);
        setSegmentCount(0);
        chunksRef.current = [];
        allSegmentsRef.current = [];
    };

    return (
        <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            {label && (
                <label className="block text-lg font-semibold text-gray-800 mb-4">
                    {label}
                </label>
            )}

            {/* 录音提示 - 仅在初始状态显示 */}
            {recordingState === 'idle' && !audioURL && (
                <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-xl p-4 mb-4">
                    <p className="text-amber-800 text-sm">
                    💡 <strong>录音提示：</strong>
                    已启用智能降噪，请保持麦克风距离适中（20-30cm），在相对安静的环境中录音效果最佳。
                    </p>
                </div>
            )}

            {/* 录音时间和状态显示 */}
            {(recordingState === 'recording' || recordingState === 'paused') && (
                <div className="flex items-center justify-center gap-4 mb-6">
                    <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                        recordingState === 'recording' 
                            ? 'bg-red-100 text-red-700' 
                            : 'bg-yellow-100 text-yellow-700'
                    }`}>
                        <span className={`w-3 h-3 rounded-full ${
                            recordingState === 'recording' 
                                ? 'bg-red-500 animate-pulse' 
                                : 'bg-yellow-500'
                        }`}></span>
                        <span className="font-medium">
                            {recordingState === 'recording' ? '录音中' : '已暂停'}
                        </span>
                    </div>
                    <div className="text-2xl font-mono font-bold text-gray-700">
                        {formatTime(recordingTime)}
                    </div>
                </div>
            )}

            {/* 片段计数 - 有多个片段时显示 */}
            {segmentCount > 1 && recordingState === 'completed' && (
                <div className="text-center mb-4">
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                        📎 已合并 {segmentCount} 段录音
                    </span>
                </div>
            )}

            {/* 控制按钮 */}
            <div className="flex flex-col items-center gap-4">
                {/* 初始状态 - 开始录音 */}
                {recordingState === 'idle' && (
                    <button 
                        onClick={() => startRecording(false)} 
                        className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-[#00B4EE] to-[#0099CC] text-white font-semibold rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200"
                    >
                        <span className="text-xl">🎤</span>
                        <span>开始录音</span>
                    </button>
                )}

                {/* 录音中状态 */}
                {recordingState === 'recording' && (
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={pauseRecording}
                            className="flex items-center gap-2 px-6 py-3 bg-yellow-500 text-white font-semibold rounded-full shadow-md hover:bg-yellow-600 transition-colors"
                        >
                            <span>⏸️</span>
                            <span>暂停</span>
                        </button>
                        <button 
                            onClick={stopRecording}
                            className="flex items-center gap-2 px-6 py-3 bg-red-500 text-white font-semibold rounded-full shadow-md hover:bg-red-600 transition-colors"
                        >
                            <span>⏹️</span>
                            <span>完成</span>
                    </button>
                    </div>
                )}

                {/* 暂停状态 */}
                {recordingState === 'paused' && (
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={resumeRecording}
                            className="flex items-center gap-2 px-6 py-3 bg-green-500 text-white font-semibold rounded-full shadow-md hover:bg-green-600 transition-colors"
                        >
                            <span>▶️</span>
                            <span>继续</span>
                        </button>
                        <button 
                            onClick={stopRecording}
                            className="flex items-center gap-2 px-6 py-3 bg-red-500 text-white font-semibold rounded-full shadow-md hover:bg-red-600 transition-colors"
                        >
                            <span>⏹️</span>
                            <span>完成</span>
                        </button>
                    </div>
                )}

                {/* 录音完成状态 */}
                {recordingState === 'completed' && audioURL && (
                    <div className="w-full space-y-4">
                        {/* 音频播放器 */}
                        <div className="bg-gray-50 rounded-xl p-4">
                            <audio 
                                src={audioURL} 
                                controls 
                                className="w-full"
                            />
                            <p className="text-center text-sm text-gray-500 mt-2">
                                总时长: {formatTime(recordingTime)}
                            </p>
                        </div>
                        
                        {/* 操作按钮 */}
                        <div className="flex justify-center gap-3">
                            <button 
                                onClick={continueRecording}
                                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-full shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                            >
                                <span>➕</span>
                                <span>继续录音</span>
                            </button>
                            <button 
                                onClick={resetRecording}
                                className="flex items-center gap-2 px-5 py-2.5 bg-gray-200 text-gray-700 font-medium rounded-full hover:bg-gray-300 transition-colors"
                            >
                                <span>🔄</span>
                                <span>重新录音</span>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

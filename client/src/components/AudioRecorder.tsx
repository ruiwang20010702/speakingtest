/**
 * 录音组件
 * 使用 MediaRecorder API 录制音频
 */
import { useState, useRef, useEffect } from 'react';
import './AudioRecorder.css';

interface AudioRecorderProps {
    onRecordingComplete: (audioBlob: Blob) => void;
    label?: string;
    existingAudio?: Blob | null; // 已存在的录音
}

export default function AudioRecorder({ onRecordingComplete, label, existingAudio }: AudioRecorderProps) {
    const [isRecording, setIsRecording] = useState(false);
    const [audioURL, setAudioURL] = useState<string | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    // 如果有已存在的录音，恢复显示
    useEffect(() => {
        if (existingAudio) {
            const url = URL.createObjectURL(existingAudio);
            setAudioURL(url);
        }
    }, [existingAudio]);


    const startRecording = async () => {
        try {
            // 启用降噪和音频增强功能
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    // 噪音抑制 - 减少背景噪音
                    noiseSuppression: true,
                    // 回声消除 - 防止扬声器声音被录入
                    echoCancellation: true,
                    // 自动增益控制 - 自动调整音量
                    autoGainControl: true,
                    // 采样率 - 高质量录音
                    sampleRate: 44100,
                    // 单声道（可选，减少文件大小）
                    channelCount: 1
                }
            });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
                const url = URL.createObjectURL(audioBlob);
                setAudioURL(url);
                onRecordingComplete(audioBlob);

                // 停止所有tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('无法访问麦克风，请检查权限设置');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const resetRecording = () => {
        setAudioURL(null);
        chunksRef.current = [];
    };

    return (
        <div className="audio-recorder">
            {label && <label className="recorder-label">{label}</label>}

            {/* 录音提示 */}
            {!audioURL && (
                <div className="recording-tips">
                    💡 <strong>录音提示：</strong>
                    已启用智能降噪，请保持麦克风距离适中（20-30cm），在相对安静的环境中录音效果最佳。
                </div>
            )}

            <div className="recorder-controls">
                {!isRecording && !audioURL && (
                    <button onClick={startRecording} className="btn btn-primary">
                        🎤 开始录音
                    </button>
                )}

                {isRecording && (
                    <button onClick={stopRecording} className="btn btn-recording">
                        <span className="recording-indicator"></span>
                        停止录音
                    </button>
                )}

                {audioURL && (
                    <div className="audio-playback">
                        <audio src={audioURL} controls />
                        <button onClick={resetRecording} className="btn btn-secondary">
                            🔄 重新录音
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

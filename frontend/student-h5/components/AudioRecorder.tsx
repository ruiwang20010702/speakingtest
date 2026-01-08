
import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Pause, Play } from 'lucide-react';

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  isLarge?: boolean;
  className?: string;
}

type RecorderStatus = 'idle' | 'recording' | 'paused';

const AudioRecorder: React.FC<AudioRecorderProps> = ({ 
  onRecordingComplete, 
  isLarge = false, 
  className = ""
}) => {
  const [status, setStatus] = useState<RecorderStatus>('idle');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
  // Use a ref for the callback to ensure the 'stop' event always uses the latest logic
  // without needing to restart the recording if the parent re-renders.
  const onCompleteRef = useRef(onRecordingComplete);
  useEffect(() => {
    onCompleteRef.current = onRecordingComplete;
  }, [onRecordingComplete]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        onCompleteRef.current(blob);
        setStatus('idle');
      };

      mediaRecorder.start();
      setStatus('recording');
    } catch (err) {
      alert("请允许麦克风权限以进行测试");
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && status === 'recording') {
      mediaRecorderRef.current.pause();
      setStatus('paused');
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && status === 'paused') {
      mediaRecorderRef.current.resume();
      setStatus('recording');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && (status === 'recording' || status === 'paused')) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  if (status === 'idle') {
    return (
      <div className={`flex flex-col items-center ${className}`}>
        <button
          onClick={startRecording}
          className={`${
            isLarge ? 'w-24 h-24' : 'w-16 h-16'
          } bg-[#FFD200] rounded-[32px] flex items-center justify-center shadow-[0_6px_0_#E5A000] active:translate-y-1 active:shadow-none transition-all text-[#824B00] border-none outline-none`}
        >
          <Mic className={isLarge ? 'w-10 h-10' : 'w-6 h-6'} strokeWidth={2.5} />
        </button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-6 ${className} animate-in fade-in zoom-in duration-300`}>
      {/* Stop/Finish Button */}
      <button
        onClick={stopRecording}
        className={`${
          isLarge ? 'w-20 h-20' : 'w-14 h-14'
        } bg-red-500 rounded-[24px] flex items-center justify-center shadow-[0_6px_0_#C53030] active:translate-y-1 active:shadow-none transition-all text-white border-none outline-none`}
      >
        <Square className={isLarge ? 'w-8 h-8' : 'w-6 h-6'} fill="currentColor" />
      </button>

      {/* Pause/Resume Button */}
      {status === 'recording' ? (
        <button
          onClick={pauseRecording}
          className={`${
            isLarge ? 'w-20 h-20' : 'w-14 h-14'
          } bg-[#1CB0F6] rounded-[24px] flex items-center justify-center shadow-[0_6px_0_#1899D6] active:translate-y-1 active:shadow-none transition-all text-white border-none outline-none animate-pulse`}
        >
          <Pause className={isLarge ? 'w-8 h-8' : 'w-6 h-6'} fill="currentColor" />
        </button>
      ) : (
        <button
          onClick={resumeRecording}
          className={`${
            isLarge ? 'w-20 h-20' : 'w-14 h-14'
          } bg-[#58CC02] rounded-[24px] flex items-center justify-center shadow-[0_6px_0_#419D01] active:translate-y-1 active:shadow-none transition-all text-white border-none outline-none`}
        >
          <Play className={isLarge ? 'w-8 h-8' : 'w-6 h-6'} fill="currentColor" />
        </button>
      )}
    </div>
  );
};

export default AudioRecorder;

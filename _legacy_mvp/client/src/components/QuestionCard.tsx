/**
 * 问题卡片组件 - 用于Part 3单独录音
 */
import { useState, useEffect } from 'react';
import AudioRecorder from './AudioRecorder';
import type { DialogueItem } from '../types';
import './QuestionCard.css';

interface QuestionCardProps {
    question: DialogueItem;
    questionNumber: number;
    totalQuestions: number;
    onRecordingComplete: (audioBlob: Blob) => void;
    existingAudio: Blob | null;
    onNext?: () => void;
    onPrevious?: () => void;
    isFirst: boolean;
    isLast: boolean;
}

export default function QuestionCard({
    question,
    questionNumber,
    totalQuestions,
    onRecordingComplete,
    existingAudio,
    onNext,
    onPrevious,
    isFirst,
    isLast
}: QuestionCardProps) {
    const [hasRecording, setHasRecording] = useState(!!existingAudio);

    // 同步 existingAudio prop 变化到 hasRecording 状态
    useEffect(() => {
        setHasRecording(!!existingAudio);
    }, [existingAudio]);

    const handleRecordingComplete = (blob: Blob) => {
        setHasRecording(true);
        onRecordingComplete(blob);
    };

    return (
        <div className="question-card">
            {/* 进度指示器 */}
            <div className="progress-header">
                <div className="progress-bar">
                    <div
                        className="progress-fill"
                        style={{ width: `${(questionNumber / totalQuestions) * 100}%` }}
                    />
                </div>
                <span className="progress-text">
                    问题 {questionNumber} / {totalQuestions}
                </span>
            </div>

            {/* 问题内容卡片 */}
            <div className="card-content">
                <div className="teacher-section">
                    <div className="teacher-icon">👨‍🏫</div>
                    <div className="teacher-question">
                        <h3>老师提问：</h3>
                        <p className="question-text">{question.teacher}</p>
                    </div>
                </div>

                {/* 参考答案（可选显示） */}
                {question.student_options && question.student_options.length > 0 && (
                    <div className="hint-section">
                        <details>
                            <summary>💡 点击查看参考答案</summary>
                            <div className="reference-answers">
                                {question.student_options.map((option, idx) => (
                                    <div key={idx} className="answer-option">
                                        {option}
                                    </div>
                                ))}
                            </div>
                        </details>
                    </div>
                )}

                {/* 录音区域 */}
                <div className="recording-section">
                    <h4>🎤 你的回答：</h4>
                    <AudioRecorder
                        key={questionNumber}
                        onRecordingComplete={handleRecordingComplete}
                        label="录制你的回答"
                        existingAudio={existingAudio}
                    />
                </div>

                {/* 导航按钮 */}
                <div className="navigation-buttons">
                    <button
                        onClick={onPrevious}
                        disabled={isFirst}
                        className="btn btn-secondary"
                    >
                        ← 上一题
                    </button>

                    {!isLast ? (
                        <button
                            onClick={onNext}
                            disabled={!hasRecording}
                            className="btn btn-primary"
                            title={!hasRecording ? '请先录制回答' : ''}
                        >
                            下一题 →
                        </button>
                    ) : (
                        <button
                            disabled={!hasRecording}
                            className="btn btn-success"
                            title={!hasRecording ? '请先录制回答' : '完成所有问题'}
                        >
                            ✓ 完成录音
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

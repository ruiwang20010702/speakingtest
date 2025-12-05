/**
 * 测试页面
 * 显示题目并进行三个部分的录音
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getQuestions, evaluateTest } from '../services/api';
import AudioRecorder from '../components/AudioRecorder';
import QuestionCard from '../components/QuestionCard';
import type { QuestionData } from '../types';
import './TestPage.css';

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
        part3?: Blob;
    }>({});

    // Part 3 专用状态：当前问题索引和12个问题的录音
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [part3Recordings, setPart3Recordings] = useState<Record<number, Blob>>({});

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadQuestions();
    }, [level, unit]);

    const loadQuestions = async () => {
        try {
            const data = await getQuestions(level, unit);
            setQuestions(data);
        } catch (err) {
            setError('加载题目失败，请刷新重试');
            console.error(err);
        }
    };

    const handleRecordingComplete = (audioBlob: Blob) => {
        setRecordings(prev => ({
            ...prev,
            [`part${currentPart}`]: audioBlob
        }));
    };

    // Part 3 问题录音处理
    const handleQuestionRecording = (questionIndex: number, audioBlob: Blob) => {
        setPart3Recordings(prev => ({
            ...prev,
            [questionIndex]: audioBlob
        }));
    };

    // Part 3 导航
    const handleNextQuestion = () => {
        const dialogues = questions?.parts.find(p => p.part_id === 3)?.dialogues;
        if (dialogues && currentQuestionIndex < dialogues.length - 1) {
            setCurrentQuestionIndex(currentQuestionIndex + 1);
        }
    };

    const handlePreviousQuestion = () => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(currentQuestionIndex - 1);
        }
    };

    const handleNext = () => {
        if (!recordings[`part${currentPart}` as keyof typeof recordings]) {
            alert('请先完成录音');
            return;
        }
        if (currentPart < 3) {
            setCurrentPart(currentPart + 1);
        }
    };

    const handleSubmit = async () => {
        // 检查 Part 1 和 Part 2
        if (!recordings.part1 || !recordings.part2) {
            alert('请完成 Part 1 和 Part 2 的录音');
            return;
        }

        // 检查 Part 3 的12个问题录音
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
            // 验证录音存在
            if (!recordings.part1 || !recordings.part2) {
                throw new Error('录音数据丢失');
            }

            // 将 Part 1 和 Part 2 的 Blob 转换为 File
            const part1File = new File([recordings.part1], 'part1.webm', { type: 'audio/webm' });
            const part2File = new File([recordings.part2], 'part2.webm', { type: 'audio/webm' });

            // 将 Part 3 的多个 Blob 转换为 File 数组
            const dialogues = questions?.parts.find(p => p.part_id === 3)?.dialogues;
            const totalQuestions = dialogues?.length || 12;
            const part3Files: File[] = [];

            for (let i = 0; i < totalQuestions; i++) {
                const blob = part3Recordings[i];
                if (!blob) {
                    throw new Error(`问题 ${i + 1} 的录音丢失`);
                }
                part3Files.push(new File([blob], `part3_q${i + 1}.webm`, { type: 'audio/webm' }));
            }

            const result = await evaluateTest(
                studentName,
                level,
                unit,
                part1File,
                part2File,
                part3Files  // 传递 File 数组
            );

            // 跳转到结果页面
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
            <div className="test-page">
                <div className="container">
                    <div className="card">
                        <h2>加载中...</h2>
                    </div>
                </div>
            </div>
        );
    }

    const currentPartData = questions.parts.find(p => p.part_id === currentPart);

    return (
        <div className="test-page">
            <div className="container">
                <div className="test-header">
                    <h2>📝 {studentName} - {questions.level_name} {questions.unit_name}</h2>
                    <div className="progress-bar">
                        <div className={`progress-step ${currentPart >= 1 ? 'active' : ''}`}>Part 1</div>
                        <div className={`progress-step ${currentPart >= 2 ? 'active' : ''}`}>Part 2</div>
                        <div className={`progress-step ${currentPart >= 3 ? 'active' : ''}`}>Part 3</div>
                    </div>
                </div>

                <div className="card test-card">
                    <h3>{currentPartData?.part_name}</h3>
                    <p className="instruction">{currentPartData?.instruction}</p>

                    {/* Part 1 - 词汇朗读 */}
                    {currentPart === 1 && currentPartData?.items && (
                        <div className="word-list">
                            {currentPartData.items.map((item, idx) => (
                                <div key={item.id} className="word-item">
                                    {idx + 1}. {item.word}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Part 2 - 自然拼读 */}
                    {currentPart === 2 && (
                        <div className="phonics-content">
                            <div className="section">
                                <h4>单词 (Words)</h4>
                                <div className="word-list">
                                    {currentPartData?.words?.map((item, idx) => (
                                        <div key={item.id} className="word-item">
                                            {idx + 1}. {item.word}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="section">
                                <h4>句子 (Sentences)</h4>
                                <div className="sentence-list">
                                    {currentPartData?.sentences?.map((item) => (
                                        <div key={item.id} className="sentence-item">
                                            {item.id}. {item.text}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Part 3 - 句子问答（卡片式单独录音） */}
                    {currentPart === 3 && currentPartData?.dialogues && (
                        <QuestionCard
                            question={currentPartData.dialogues[currentQuestionIndex]}
                            questionNumber={currentQuestionIndex + 1}
                            totalQuestions={currentPartData.dialogues.length}
                            onRecordingComplete={(blob) => handleQuestionRecording(currentQuestionIndex, blob)}
                            existingAudio={part3Recordings[currentQuestionIndex] || null}
                            onNext={handleNextQuestion}
                            onPrevious={handlePreviousQuestion}
                            isFirst={currentQuestionIndex === 0}
                            isLast={currentQuestionIndex === currentPartData.dialogues.length - 1}
                        />
                    )}

                    {/* Part 1 和 Part 2 继续使用统一录音 */}
                    {currentPart !== 3 && (
                        <>
                            <AudioRecorder
                                key={currentPart}
                                onRecordingComplete={handleRecordingComplete}
                                label={`请录制 ${currentPartData?.part_name}`}
                                existingAudio={recordings[`part${currentPart}` as keyof typeof recordings] || null}
                            />

                            {error && <div className="error-message">{error}</div>}

                            <div className="button-group">
                                {currentPart > 1 && (
                                    <button
                                        onClick={() => setCurrentPart(currentPart - 1)}
                                        className="btn btn-secondary"
                                    >
                                        ← 上一部分
                                    </button>
                                )}

                                {currentPart < 3 ? (
                                    <button onClick={handleNext} className="btn btn-primary">
                                        下一部分 →
                                    </button>
                                ) : (
                                    <button
                                        onClick={handleSubmit}
                                        className="btn btn-primary"
                                        disabled={isSubmitting}
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <span className="loading"></span>
                                                提交评分中...
                                            </>
                                        ) : (
                                            '提交评分 ✓'
                                        )}
                                    </button>
                                )}
                            </div>
                        </>
                    )}

                    {/* Part 3 的提交按钮单独显示 */}
                    {currentPart === 3 && currentPartData?.dialogues && currentQuestionIndex === currentPartData.dialogues.length - 1 && (
                        <div className="part3-submit-section">
                            {error && <div className="error-message">{error}</div>}
                            <p className="completion-hint">
                                已完成 {Object.keys(part3Recordings).length} / {currentPartData.dialogues.length} 个问题的录音
                            </p>
                            <button
                                onClick={handleSubmit}
                                className="btn btn-primary btn-large"
                                disabled={isSubmitting || Object.keys(part3Recordings).length < currentPartData.dialogues.length}
                            >
                                {isSubmitting ? (
                                    <>
                                        <span className="loading"></span>
                                        提交评分中...
                                    </>
                                ) : (
                                    '提交评分 ✓'
                                )}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

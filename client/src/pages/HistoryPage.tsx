/**
 * 历史记录页面
 * 显示学生的所有测试记录
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getHistory } from '../services/api';
import type { TestResult } from '../types';
import './HistoryPage.css';

export default function HistoryPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const studentName = searchParams.get('student') || '';

    const [records, setRecords] = useState<TestResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadHistory();
    }, [studentName]);

    const loadHistory = async () => {
        try {
            // 如果有学生姓名，则获取该学生的记录；否则获取所有记录
            const data = await getHistory(studentName || undefined);
            setRecords(data);
        } catch (err) {
            setError('加载历史记录失败');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderStars = (rating: number) => {
        return (
            <div className="stars">
                {[1, 2, 3, 4, 5].map(star => (
                    <span key={star} className={star <= rating ? 'star' : 'star empty'}>
                        ⭐
                    </span>
                ))}
            </div>
        );
    };

    if (loading) {
        return (
            <div className="history-page">
                <div className="container">
                    <div className="card">
                        <div className="loading-container">
                            <span className="loading"></span>
                            <p>加载历史记录中...</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="history-page">
            <div className="container">
                <div className="history-header">
                    <h1>📚 测试历史记录</h1>
                    {studentName && <p className="student-name">{studentName} 的所有测试记录</p>}
                    <button onClick={() => navigate('/')} className="btn btn-secondary">
                        返回首页
                    </button>
                </div>

                <div className="records-container">
                    {error && (
                        <div className="card error-card">
                            <p>{error}</p>
                        </div>
                    )}

                    {!error && records.length === 0 && (
                        <div className="card empty-card">
                            <p>暂无测试记录</p>
                            <button onClick={() => navigate('/')} className="btn btn-primary">
                                开始测试
                            </button>
                        </div>
                    )}

                    {!error && records.length > 0 && (
                        <div className="records-grid">
                            {records.map(record => (
                                <div
                                    key={record.id}
                                    className="record-card card"
                                    onClick={() => navigate(`/result?id=${record.id}`)}
                                >
                                    <div className="record-header">
                                        <h3>{record.student_name}</h3>
                                        <span className="record-date">
                                            {new Date(record.created_at).toLocaleDateString('zh-CN', {
                                                year: 'numeric',
                                                month: 'long',
                                                day: 'numeric'
                                            })}
                                        </span>
                                    </div>

                                    <div className="record-info">
                                        <span className="level-badge">{record.level}</span>
                                        <span className="unit-badge">{record.unit}</span>
                                    </div>

                                    <div className="record-score">
                                        <div className="score-big">
                                            {record.total_score}
                                            <span className="score-small">/60</span>
                                        </div>
                                        {renderStars(record.star_rating)}
                                    </div>

                                    <div className="record-parts">
                                        {record.part_scores.map(part => (
                                            <div key={part.part_number} className="part-mini">
                                                <span>Part {part.part_number}</span>
                                                <span className="part-score">
                                                    {part.score}/{part.max_score}
                                                </span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="view-detail">
                                        查看详情 →
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

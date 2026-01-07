import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { studentsApi, type TestSummary } from '../api';
import './StudentDetailPage.css';

export default function StudentDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [tests, setTests] = useState<TestSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [generating, setGenerating] = useState(false);

    // New test modal
    const [showNewTest, setShowNewTest] = useState(false);
    const [level, setLevel] = useState('L1');
    const [unit, setUnit] = useState('Unit 1');

    useEffect(() => {
        if (id) {
            loadTests();
        }
    }, [id]);

    const loadTests = async () => {
        try {
            const response = await studentsApi.getTests(parseInt(id!));
            setTests(response.data);
        } catch (err) {
            setError('加载测评记录失败');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateToken = async () => {
        setGenerating(true);
        try {
            const response = await studentsApi.generateToken(parseInt(id!), level, unit);
            // Show token/QR code (simplified for now, just alert URL)
            alert(`测评链接已生成：\n${response.data.entry_url}\n\n请复制发给学生`);
            setShowNewTest(false);
            loadTests(); // Reload list
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            alert(error.response?.data?.detail || '生成失败');
        } finally {
            setGenerating(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const map: Record<string, string> = {
            pending: '待开始',
            part1_done: '进行中',
            processing: '评分中',
            completed: '已完成',
            failed: '失败'
        };
        return <span className={`status-badge ${status}`}>{map[status] || status}</span>;
    };

    return (
        <div className="detail-page">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/')}>← 返回列表</button>
                <h1>学生详情</h1>
            </header>

            <div className="content-container">
                <div className="section-header">
                    <h2>测评历史</h2>
                    <button className="btn-primary" onClick={() => setShowNewTest(true)}>
                        + 发起新测评
                    </button>
                </div>

                {loading ? (
                    <div className="loading">加载中...</div>
                ) : error ? (
                    <div className="error">{error}</div>
                ) : tests.length === 0 ? (
                    <div className="empty">暂无测评记录</div>
                ) : (
                    <div className="tests-list">
                        {tests.map((test) => (
                            <div
                                key={test.id}
                                className="test-item"
                                onClick={() => test.status === 'completed' && navigate(`/report/${test.id}`)}
                            >
                                <div className="test-info">
                                    <h3>{test.level} - {test.unit}</h3>
                                    <span className="test-date">{new Date(test.created_at).toLocaleDateString()}</span>
                                </div>

                                <div className="test-stats">
                                    {test.total_score && (
                                        <div className="score-box">
                                            <span className="label">总分</span>
                                            <span className="value">{test.total_score.toFixed(1)}</span>
                                        </div>
                                    )}
                                    {test.star_level && (
                                        <div className="star-box">
                                            {'⭐'.repeat(test.star_level)}
                                        </div>
                                    )}
                                </div>

                                <div className="test-status">
                                    {getStatusBadge(test.status)}
                                    {test.status === 'completed' && <span className="arrow">→</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* New Test Modal */}
            {showNewTest && (
                <div className="modal-overlay" onClick={() => setShowNewTest(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2>发起新测评</h2>

                        <div className="form-group">
                            <label>选择级别</label>
                            <select value={level} onChange={(e) => setLevel(e.target.value)}>
                                <option value="L1">Level 1</option>
                                <option value="L2">Level 2</option>
                                <option value="L3">Level 3</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>选择单元</label>
                            <select value={unit} onChange={(e) => setUnit(e.target.value)}>
                                <option value="Unit 1">Unit 1</option>
                                <option value="Unit 2">Unit 2</option>
                                <option value="Unit 3">Unit 3</option>
                            </select>
                        </div>

                        <div className="modal-actions">
                            <button
                                className="btn-cancel"
                                onClick={() => setShowNewTest(false)}
                                disabled={generating}
                            >
                                取消
                            </button>
                            <button
                                className="btn-confirm"
                                onClick={handleGenerateToken}
                                disabled={generating}
                            >
                                {generating ? '生成中...' : '生成测评链接'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { testsApi, type TestReport, type Interpretation } from '../api';
import './ReportPage.css';

export default function ReportPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [report, setReport] = useState<TestReport | null>(null);
    const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [shareLink, setShareLink] = useState('');
    const [sharing, setSharing] = useState(false);

    useEffect(() => {
        if (id) {
            loadData();
        }
    }, [id]);

    const loadData = async () => {
        try {
            const [reportRes, interpRes] = await Promise.all([
                testsApi.getReport(parseInt(id!)),
                testsApi.getInterpretation(parseInt(id!))
            ]);
            setReport(reportRes.data);
            setInterpretation(interpRes.data);
        } catch (err) {
            setError('加载报告失败');
        } finally {
            setLoading(false);
        }
    };

    const handleShare = async () => {
        setSharing(true);
        try {
            const response = await testsApi.generateShareLink(parseInt(id!));
            setShareLink(response.data.share_url);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            alert(error.response?.data?.detail || '生成分享链接失败');
        } finally {
            setSharing(false);
        }
    };

    if (loading) return <div className="loading">加载中...</div>;
    if (error) return <div className="error">{error}</div>;
    if (!report) return <div className="error">报告不存在</div>;

    return (
        <div className="report-page">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate(-1)}>← 返回</button>
                <h1>测评报告</h1>
                <button className="btn-share" onClick={handleShare} disabled={sharing}>
                    {sharing ? '生成中...' : '📤 分享给家长'}
                </button>
            </header>

            <div className="report-container">
                {/* Score Card */}
                <div className="score-card">
                    <div className="score-header">
                        <div className="student-info">
                            <h2>{report.student_name}</h2>
                            <span>{report.level} - {report.unit}</span>
                        </div>
                        <div className="total-score">
                            <span className="label">总分</span>
                            <span className="value">{report.total_score?.toFixed(1)}</span>
                        </div>
                    </div>

                    <div className="stars">
                        {'⭐'.repeat(report.star_level || 0)}
                    </div>

                    <div className="sub-scores">
                        <div className="score-item">
                            <span className="label">Part 1 朗读</span>
                            <span className="value">{report.part1_score?.toFixed(1)}</span>
                        </div>
                        <div className="score-item">
                            <span className="label">Part 2 问答</span>
                            <span className="value">{report.part2_score?.toFixed(1)}</span>
                        </div>
                    </div>
                </div>

                {/* AI Interpretation */}
                {interpretation && (
                    <div className="interpretation-section">
                        <h3>AI 智能解读</h3>

                        <div className="interp-grid">
                            <div className="interp-card highlight">
                                <h4>✨ 表现亮点</h4>
                                <ul>
                                    {interpretation.highlights.map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>

                            <div className="interp-card weakness">
                                <h4>💪 待提升点</h4>
                                <ul>
                                    {interpretation.weaknesses.map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div className="interp-card suggestions">
                            <h4>📝 学习建议</h4>
                            <ul>
                                {interpretation.suggestions.map((item, i) => (
                                    <li key={i}>{item}</li>
                                ))}
                            </ul>
                        </div>

                        <div className="interp-card script">
                            <h4>💬 家长沟通话术</h4>
                            <div className="script-content">
                                {interpretation.parent_script.split('\n').map((line, i) => (
                                    <p key={i}>{line}</p>
                                ))}
                            </div>
                            <button
                                className="btn-copy"
                                onClick={() => {
                                    navigator.clipboard.writeText(interpretation.parent_script);
                                    alert('已复制到剪贴板');
                                }}
                            >
                                复制话术
                            </button>
                        </div>
                    </div>
                )}

                {/* Detailed Items */}
                <div className="details-section">
                    <h3>详细评分</h3>
                    <div className="items-list">
                        {report.items.map((item) => (
                            <div key={item.question_no} className="report-item">
                                <div className="item-header">
                                    <span className="q-no">Q{item.question_no}</span>
                                    <span className={`score-tag score-${item.score}`}>
                                        {item.score === 2 ? '优秀' : item.score === 1 ? '良好' : '需努力'}
                                    </span>
                                </div>
                                {item.evidence && (
                                    <div className="item-evidence">
                                        "{item.evidence}"
                                    </div>
                                )}
                                {item.feedback && (
                                    <div className="item-feedback">
                                        点评：{item.feedback}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Share Modal */}
            {shareLink && (
                <div className="modal-overlay" onClick={() => setShareLink('')}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2>分享报告</h2>
                        <p>将此链接发送给家长，无需登录即可查看：</p>
                        <div className="share-link-box">
                            <input type="text" value={shareLink} readOnly />
                            <button onClick={() => {
                                navigator.clipboard.writeText(shareLink);
                                alert('已复制');
                            }}>复制</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

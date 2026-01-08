import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { QRCodeCanvas } from 'qrcode.react';
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
    const [level, setLevel] = useState('L0');
    const [unit, setUnit] = useState('All');

    // QR code modal
    const [showQRModal, setShowQRModal] = useState(false);
    const [generatedUrl, setGeneratedUrl] = useState('');
    const [copied, setCopied] = useState(false);

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
            setGeneratedUrl(response.data.entry_url);
            setShowNewTest(false);
            setShowQRModal(true);
            setCopied(false);
            loadTests(); // Reload list
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            alert(error.response?.data?.detail || '生成失败');
        } finally {
            setGenerating(false);
        }
    };

    const handleCopyLink = async () => {
        try {
            await navigator.clipboard.writeText(generatedUrl);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = generatedUrl;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleDownloadQR = () => {
        const canvas = document.querySelector('.qr-code-container canvas') as HTMLCanvasElement;
        if (canvas) {
            const pngUrl = canvas.toDataURL('image/png');
            const downloadLink = document.createElement('a');
            downloadLink.href = pngUrl;
            downloadLink.download = `qrcode-${level}-${unit}.png`;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        }
    };

    const getStatusBadge = (test: TestSummary) => {
        const isExpired = !test.completed_at && new Date(test.created_at).getTime() + 7 * 24 * 60 * 60 * 1000 < Date.now();

        if (isExpired) {
            return <span className="status-badge status-expired">已失效</span>;
        }

        const map: Record<string, { text: string; className: string }> = {
            pending: { text: '待开始', className: 'status-pending' },
            part1_done: { text: '测试中', className: 'status-progress' },
            processing: { text: '测试中', className: 'status-processing' }, // Processing also means in progress for user
            completed: { text: '已完成', className: 'status-completed' },
            failed: { text: '失败', className: 'status-failed' }
        };
        const info = map[test.status] || { text: test.status, className: '' };
        return <span className={`status-badge ${info.className}`}>{info.text}</span>;
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
    };

    return (
        <div className="detail-page">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/')}>← 返回列表</button>
                <h1>学生详情</h1>
            </header>

            <div className="content-container">
                <div className="section-header">
                    <h2>测评记录</h2>
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
                    <div className="tests-grid">
                        {tests.map((test) => (
                            <div key={test.id} className="test-card">
                                <div className="card-header">
                                    <span className="level-unit">{test.level} - {test.unit}</span>
                                    {getStatusBadge(test)}
                                </div>

                                <div className="card-body">
                                    <div className="card-time">
                                        创建: {formatDate(test.created_at)}
                                        {test.completed_at && (
                                            <> | 完成: {formatDate(test.completed_at)}</>
                                        )}
                                    </div>

                                    {test.total_score !== undefined && test.total_score !== null && (
                                        <div className="card-score">
                                            <span className="score-value">{test.total_score.toFixed(0)}</span>
                                            <span className="score-label">分</span>
                                            {test.star_level && (
                                                <span className="stars">{'⭐'.repeat(test.star_level)}</span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="card-actions">
                                    {/* Show buttons for pending/in-progress tests if they have entry_url (backend ensures entry_url is only sent if valid) */}
                                    {test.entry_url && test.status !== 'completed' && (
                                        <>
                                            <button
                                                className="btn-action btn-copy"
                                                onClick={() => {
                                                    navigator.clipboard.writeText(test.entry_url!);
                                                    alert('链接已复制');
                                                }}
                                            >
                                                🔗 复制链接
                                            </button>
                                            <button
                                                className="btn-action btn-qr"
                                                onClick={() => {
                                                    setGeneratedUrl(test.entry_url!);
                                                    setLevel(test.level);
                                                    setUnit(test.unit);
                                                    setShowQRModal(true);
                                                }}
                                            >
                                                📱 二维码
                                            </button>
                                        </>
                                    )}

                                    {test.status === 'completed' && (
                                        <>
                                            <button
                                                className="btn-action btn-report"
                                                onClick={() => navigate(`/report/${test.id}`)}
                                            >
                                                📊 查看报告
                                            </button>
                                            <button
                                                className="btn-action btn-interpret"
                                                onClick={() => navigate(`/report/${test.id}?tab=interpretation`)}
                                            >
                                                💬 查看解读
                                            </button>
                                        </>
                                    )}
                                    {test.status === 'processing' && !test.entry_url && (
                                        <span className="processing-hint">正在生成报告...</span>
                                    )}
                                    {test.status === 'part1_done' && !test.entry_url && (
                                        <span className="processing-hint">学生正在作答...</span>
                                    )}
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
                                <option value="L0">L0 (启蒙级)</option>
                                <option value="L1">L1</option>
                                <option value="L2">L2</option>
                                <option value="L3">L3</option>
                                <option value="L4">L4</option>
                                <option value="L5">L5</option>
                                <option value="L6">L6</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>选择单元</label>
                            <select value={unit} onChange={(e) => setUnit(e.target.value)}>
                                <option value="All">全部单元</option>
                                <option value="Unit 1-4">Unit 1-4</option>
                                <option value="Unit 5-8">Unit 5-8</option>
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

            {/* QR Code Modal */}
            {showQRModal && (
                <div className="modal-overlay" onClick={() => setShowQRModal(false)}>
                    <div className="modal-content qr-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="qr-success-icon">✅</div>
                        <h2>测评链接已生成</h2>

                        <div className="qr-code-container">
                            <QRCodeCanvas
                                value={generatedUrl}
                                size={180}
                                level="M"
                                includeMargin={true}
                            />
                        </div>

                        <button className="btn-download-qr" onClick={handleDownloadQR}>
                            ⬇️ 下载二维码
                        </button>

                        <p className="qr-hint">让学生扫描二维码开始测评</p>

                        <div className="link-container">
                            <input
                                type="text"
                                value={generatedUrl}
                                readOnly
                                className="link-input"
                            />
                            <button
                                className={`btn-copy-link ${copied ? 'copied' : ''}`}
                                onClick={handleCopyLink}
                            >
                                {copied ? '✓ 已复制' : '复制链接'}
                            </button>
                        </div>

                        <p className="expiry-hint">⏰ 链接有效期：24小时</p>

                        <button
                            className="btn-close-qr"
                            onClick={() => setShowQRModal(false)}
                        >
                            完成
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

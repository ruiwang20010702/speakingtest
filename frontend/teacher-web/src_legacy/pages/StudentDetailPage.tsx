import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { QRCodeCanvas } from 'qrcode.react';
import { studentsApi, type TestSummary } from '../api';
import Layout from '../components/Layout';

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
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
                    已失效
                </span>
            );
        }

        const map: Record<string, { text: string; className: string }> = {
            pending: { text: '待开始', className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
            part1_done: { text: '测试中', className: 'bg-blue-50 text-blue-700 border-blue-200' },
            processing: { text: '分析中', className: 'bg-purple-50 text-purple-700 border-purple-200 animate-pulse' },
            completed: { text: '已完成', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
            failed: { text: '失败', className: 'bg-red-50 text-red-700 border-red-200' }
        };
        const info = map[test.status] || { text: test.status, className: 'bg-gray-100 text-gray-800' };
        
        return (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${info.className}`}>
                {info.text}
            </span>
        );
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
    };

    const pageActions = (
                    <button 
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover shadow-sm transition-all shadow-primary/20"
                        onClick={() => setShowNewTest(true)}
                    >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        发起新测评
                    </button>
    );

    return (
        <Layout title="学生详情" showBack actions={pageActions}>
            <div className="space-y-6">
                <div className="flex items-center gap-2 mb-4">
                    <span className="bg-primary/10 w-8 h-8 rounded-lg flex items-center justify-center text-primary text-sm">
                        📚
                    </span>
                    <h2 className="text-xl font-bold text-gray-900">测评记录</h2>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
                        <p className="text-gray-500">加载记录中...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-10 text-red-500 bg-white rounded-xl shadow-sm border border-red-100">{error}</div>
                ) : tests.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-xl shadow-sm border border-gray-200 border-dashed">
                        <p className="text-gray-400 mb-4">暂无测评记录</p>
                        <button 
                            className="text-primary hover:underline font-medium"
                            onClick={() => setShowNewTest(true)}
                        >
                            立即发起第一个测评
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {tests.map((test) => (
                            <div key={test.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow group">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-200 font-bold text-gray-800 font-mono">
                                            {test.level}
                                        </div>
                                        <div className="text-gray-600 font-medium">
                                            {test.unit}
                                        </div>
                                        {getStatusBadge(test)}
                                    </div>
                                    
                                    {test.total_score !== undefined && test.total_score !== null && (
                                        <div className="flex items-center gap-3 bg-gradient-to-r from-yellow-50 to-white px-4 py-1 rounded-lg border border-yellow-100">
                                            <div className="flex items-baseline gap-1">
                                                <span className="text-2xl font-bold text-gray-900">{test.total_score.toFixed(0)}</span>
                                                <span className="text-xs text-gray-500 font-medium">分</span>
                                            </div>
                                            {test.star_level && (
                                                <div className="flex text-yellow-400 text-sm">
                                                    {'⭐'.repeat(test.star_level)}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-gray-50 pt-4">
                                    <div className="text-xs text-gray-400 flex flex-col gap-1 font-mono">
                                        <span>创建: {formatDate(test.created_at)}</span>
                                        {test.completed_at && (
                                            <span>完成: {formatDate(test.completed_at)}</span>
                                        )}
                                    </div>

                                    <div className="flex gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                                        {test.entry_url && test.status !== 'completed' && (
                                            <>
                                                <button
                                                    className="px-3 py-1.5 bg-white text-gray-700 rounded-lg hover:bg-gray-50 border border-gray-200 text-xs font-medium transition-colors"
                                                    onClick={() => {
                                                        navigator.clipboard.writeText(test.entry_url!);
                                                        alert('链接已复制');
                                                    }}
                                                >
                                                    🔗 复制链接
                                                </button>
                                                <button
                                                    className="px-3 py-1.5 bg-white text-gray-700 rounded-lg hover:bg-gray-50 border border-gray-200 text-xs font-medium transition-colors"
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
                                                    className="px-3 py-1.5 bg-primary/5 text-primary rounded-lg hover:bg-primary/10 border border-primary/10 text-xs font-bold transition-colors flex items-center gap-1"
                                                    onClick={() => navigate(`/report/${test.id}`)}
                                                >
                                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                                    </svg>
                                                    查看报告
                                                </button>
                                                <button
                                                    className="px-3 py-1.5 bg-secondary/10 text-amber-700 rounded-lg hover:bg-secondary/20 border border-secondary/20 text-xs font-bold transition-colors flex items-center gap-1"
                                                    onClick={() => navigate(`/report/${test.id}`)}
                                                >
                                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                                    </svg>
                                                    AI 解读
                                                </button>
                                            </>
                                        )}
                                        {test.status === 'processing' && !test.entry_url && (
                                            <span className="text-xs text-purple-600 bg-purple-50 px-3 py-1.5 rounded-lg flex items-center border border-purple-100">
                                                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce mr-2"></div>
                                                报告生成中...
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* New Test Modal */}
            {showNewTest && (
                <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden" onClick={(e) => e.stopPropagation()}>
                        <div className="p-6 border-b border-gray-100">
                            <h2 className="text-lg font-bold text-gray-900">发起新测评</h2>
                        </div>
                        
                        <div className="p-6 space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-gray-700">选择级别</label>
                                <div className="relative">
                                <select 
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-gray-900 appearance-none font-medium"
                                    value={level} 
                                    onChange={(e) => setLevel(e.target.value)}
                                >
                                    <option value="L0">L0 (启蒙级)</option>
                                    <option value="L1">L1</option>
                                    <option value="L2">L2</option>
                                    <option value="L3">L3</option>
                                    <option value="L4">L4</option>
                                    <option value="L5">L5</option>
                                    <option value="L6">L6</option>
                                </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-gray-500">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-gray-700">选择单元</label>
                                <div className="relative">
                                <select 
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-gray-900 appearance-none font-medium"
                                    value={unit} 
                                    onChange={(e) => setUnit(e.target.value)}
                                >
                                    <option value="All">全部单元</option>
                                    <option value="Unit 1-4">Unit 1-4</option>
                                    <option value="Unit 5-8">Unit 5-8</option>
                                </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-gray-500">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 pt-0 flex gap-3">
                            <button
                                className="flex-1 px-4 py-3 border border-gray-200 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-colors"
                                onClick={() => setShowNewTest(false)}
                                disabled={generating}
                            >
                                取消
                            </button>
                            <button
                                className="flex-1 px-4 py-3 bg-primary text-white font-bold rounded-xl hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all disabled:opacity-50"
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
                <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden text-center" onClick={(e) => e.stopPropagation()}>
                        <div className="bg-emerald-50 p-6 border-b border-emerald-100 flex flex-col items-center">
                            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 text-xl mb-3 shadow-sm">
                                ✅
                            </div>
                            <h2 className="text-xl font-bold text-gray-900">测评链接已生成</h2>
                            <p className="text-sm text-gray-500 mt-1">让学生扫描二维码开始测评</p>
                        </div>

                        <div className="p-8 flex flex-col items-center qr-code-container bg-white">
                            <div className="p-3 bg-white rounded-2xl shadow-sm border border-gray-100">
                                <QRCodeCanvas
                                    value={generatedUrl}
                                    size={180}
                                    level="M"
                                    includeMargin={true}
                                />
                            </div>
                            
                            <button 
                                className="mt-4 text-primary text-sm font-medium hover:underline flex items-center gap-1 group" 
                                onClick={handleDownloadQR}
                            >
                                <svg className="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                保存二维码图片
                            </button>
                        </div>

                        <div className="px-6 pb-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={generatedUrl}
                                    readOnly
                                    className="flex-1 px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600 outline-none font-mono"
                                />
                                <button
                                    className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm ${
                                        copied 
                                            ? 'bg-emerald-500 text-white' 
                                            : 'bg-gray-900 text-white hover:bg-gray-800'
                                    }`}
                                    onClick={handleCopyLink}
                                >
                                    {copied ? '已复制' : '复制'}
                                </button>
                            </div>
                            
                            <p className="text-xs text-gray-400 bg-gray-50 py-2 rounded-lg border border-gray-100">
                                ⏰ 链接有效期：24小时
                            </p>

                            <button
                                className="w-full py-3 text-gray-600 font-medium hover:bg-gray-50 transition-colors border-t border-gray-100 -mb-6"
                                onClick={() => setShowQRModal(false)}
                            >
                                完成
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

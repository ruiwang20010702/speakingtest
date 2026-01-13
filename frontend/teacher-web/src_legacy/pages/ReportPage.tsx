import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { testsApi, type TestReport, type Interpretation } from '../api';
import Layout from '../components/Layout';

export default function ReportPage() {
    const { id } = useParams<{ id: string }>();

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

    const pageActions = (
        <button 
            onClick={handleShare}
            disabled={sharing}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover shadow-sm transition-all shadow-primary/20 disabled:opacity-50"
        >
            {sharing ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
            )}
            {sharing ? '生成中...' : '分享给家长'}
        </button>
    );

    if (loading) {
        return (
            <Layout title="测评报告" showBack>
                <div className="flex flex-col items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
                    <p className="text-gray-500">报告生成中...</p>
                </div>
            </Layout>
        );
    }

    if (error || !report) {
        return (
            <Layout title="测评报告" showBack>
                <div className="text-center py-10 bg-red-50 text-red-600 rounded-xl border border-red-100">
                    {error || '报告不存在'}
                </div>
            </Layout>
        );
    }

    return (
        <Layout title="测评报告" showBack actions={pageActions}>
            <div className="max-w-4xl mx-auto space-y-8">
                {/* Score Card */}
                <div className="bg-gradient-to-br from-[#002FA7] to-[#001A5C] text-white rounded-2xl p-8 shadow-xl shadow-primary/20 relative overflow-hidden">
                    {/* Decorative background circles */}
                    <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-white/5 blur-3xl"></div>
                    <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-64 h-64 rounded-full bg-secondary/10 blur-3xl"></div>

                    <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-8">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <h2 className="text-3xl font-bold">{report.student_name}</h2>
                                <span className="px-3 py-1 rounded-full bg-white/10 border border-white/20 text-sm backdrop-blur-sm">
                                    {report.level} - {report.unit}
                                </span>
                        </div>
                            <div className="flex text-yellow-400 text-2xl mb-6">
                                {'⭐'.repeat(report.star_level || 0)}
                                <span className="text-white/20">
                                    {'⭐'.repeat(5 - (report.star_level || 0))}
                                </span>
                    </div>

                            <div className="flex gap-8">
                                <div>
                                    <span className="block text-white/60 text-xs uppercase tracking-wider mb-1">Part 1 朗读</span>
                                    <span className="text-2xl font-bold font-mono">{report.part1_score?.toFixed(1)}</span>
                                </div>
                                <div className="w-px bg-white/10"></div>
                                <div>
                                    <span className="block text-white/60 text-xs uppercase tracking-wider mb-1">Part 2 问答</span>
                                    <span className="text-2xl font-bold font-mono">{report.part2_score?.toFixed(1)}</span>
                                </div>
                    </div>
                        </div>

                        <div className="text-right">
                            <span className="block text-white/60 text-sm mb-1">总分</span>
                            <div className="text-7xl font-bold font-mono tracking-tighter leading-none">
                                {report.total_score?.toFixed(1)}
                            </div>
                        </div>
                    </div>
                </div>

                {/* AI Interpretation */}
                {interpretation && (
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <span className="bg-secondary/20 w-8 h-8 rounded-lg flex items-center justify-center text-secondary-hover text-lg">
                                🤖
                            </span>
                            AI 智能解读
                        </h3>

                        <div className="grid md:grid-cols-2 gap-6">
                            {/* Highlights */}
                            <div className="bg-white rounded-xl p-6 border border-emerald-100 shadow-sm relative overflow-hidden group">
                                <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110"></div>
                                <h4 className="text-lg font-bold text-emerald-800 mb-4 flex items-center gap-2 relative z-10">
                                    ✨ 表现亮点
                                </h4>
                                <ul className="space-y-3 relative z-10">
                                    {interpretation.highlights.map((item, i) => (
                                        <li key={i} className="flex gap-3 text-emerald-900/80 text-sm leading-relaxed">
                                            <span className="text-emerald-500 mt-0.5">•</span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Weaknesses */}
                            <div className="bg-white rounded-xl p-6 border border-rose-100 shadow-sm relative overflow-hidden group">
                                <div className="absolute top-0 right-0 w-20 h-20 bg-rose-50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110"></div>
                                <h4 className="text-lg font-bold text-rose-800 mb-4 flex items-center gap-2 relative z-10">
                                    💪 待提升点
                                </h4>
                                <ul className="space-y-3 relative z-10">
                                    {interpretation.weaknesses.map((item, i) => (
                                        <li key={i} className="flex gap-3 text-rose-900/80 text-sm leading-relaxed">
                                            <span className="text-rose-500 mt-0.5">•</span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Suggestions */}
                        <div className="bg-white rounded-xl p-6 border border-blue-100 shadow-sm relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50/50 rounded-full blur-2xl -mr-10 -mt-10"></div>
                            <h4 className="text-lg font-bold text-blue-800 mb-4 flex items-center gap-2 relative z-10">
                                📝 学习建议
                            </h4>
                            <div className="grid md:grid-cols-3 gap-4 relative z-10">
                                {interpretation.suggestions.map((item, i) => (
                                    <div key={i} className="bg-blue-50/50 rounded-lg p-4 text-blue-900/80 text-sm leading-relaxed">
                                        {item}
                        </div>
                                ))}
                            </div>
                        </div>

                        {/* Parent Script */}
                        <div className="bg-amber-50 rounded-xl p-6 border border-amber-100 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="text-lg font-bold text-amber-800 flex items-center gap-2">
                                    💬 家长沟通话术
                                </h4>
                            <button
                                onClick={() => {
                                    navigator.clipboard.writeText(interpretation.parent_script);
                                    alert('已复制到剪贴板');
                                }}
                                    className="text-xs font-medium text-amber-700 bg-amber-100 px-3 py-1.5 rounded-lg hover:bg-amber-200 transition-colors"
                            >
                                复制话术
                            </button>
                            </div>
                            <div className="bg-white/60 rounded-lg p-4 text-amber-900/80 text-sm leading-relaxed whitespace-pre-wrap font-mono">
                                {interpretation.parent_script}
                            </div>
                        </div>
                    </div>
                )}

                {/* Detailed Items */}
                {report.part2_items && report.part2_items.length > 0 && (
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-gray-900 border-l-4 border-primary pl-4">详细评分</h3>
                        <div className="space-y-4">
                            {report.part2_items.map((item) => (
                                <div key={item.question_no} className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm">
                                    <div className="flex items-center justify-between mb-4">
                                        <span className="font-mono font-bold text-gray-400">Q{item.question_no}</span>
                                        <span className={`px-2.5 py-1 rounded text-xs font-bold ${
                                            item.score === 2 
                                                ? 'bg-emerald-100 text-emerald-700' 
                                                : item.score === 1 
                                                    ? 'bg-amber-100 text-amber-700' 
                                                    : 'bg-rose-100 text-rose-700'
                                        }`}>
                                            {item.score === 2 ? '优秀 (2分)' : item.score === 1 ? '良好 (1分)' : '需努力 (0分)'}
                                        </span>
                                    </div>
                                    
                                    {item.evidence && (
                                        <blockquote className="border-l-2 border-gray-200 pl-4 py-1 my-3 text-gray-600 italic text-sm">
                                            "{item.evidence}"
                                        </blockquote>
                                    )}
                                    
                                    {item.feedback && (
                                        <div className="bg-gray-50 rounded-lg p-3 text-gray-600 text-sm flex gap-2">
                                            <span className="text-primary">💡</span>
                                            {item.feedback}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Share Modal */}
            {shareLink && (
                <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" onClick={(e) => e.stopPropagation()}>
                        <div className="bg-primary/5 p-6 border-b border-primary/10">
                            <h2 className="text-lg font-bold text-primary">分享报告</h2>
                            <p className="text-sm text-gray-600 mt-1">将此链接发送给家长，无需登录即可查看</p>
                        </div>
                        
                        <div className="p-6 space-y-4">
                            <div className="flex gap-2">
                                <input 
                                    type="text" 
                                    value={shareLink} 
                                    readOnly 
                                    className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-600 outline-none font-mono"
                                />
                                <button 
                                    onClick={() => {
                                navigator.clipboard.writeText(shareLink);
                                alert('已复制');
                                        setShareLink('');
                                    }}
                                    className="px-6 bg-primary text-white font-bold rounded-xl hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all"
                                >
                                    复制
                                </button>
                            </div>
                            
                            <button
                                onClick={() => setShareLink('')}
                                className="w-full py-3 text-gray-500 font-medium hover:bg-gray-50 rounded-xl transition-colors"
                            >
                                关闭
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

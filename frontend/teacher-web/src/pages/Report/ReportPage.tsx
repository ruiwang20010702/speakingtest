import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Share2 } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { testsApi, type TestReport, type Interpretation } from '../../api';
import { LinkGeneratedModal } from '../Assessment/components/LinkGeneratedModal';

export const ReportPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [report, setReport] = useState<TestReport | null>(null);
    const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [shareLink, setShareLink] = useState('');
    const [sharing, setSharing] = useState(false);
    const [isShareModalOpen, setIsShareModalOpen] = useState(false);

    useEffect(() => {
        if (id) {
            loadData();
        }
    }, [id]);

    const loadData = async () => {
        if (!id) return;
        try {
            setLoading(true);
            const [reportRes, interpRes] = await Promise.all([
                testsApi.getReport(parseInt(id)),
                testsApi.getInterpretation(parseInt(id)).catch(() => null)
            ]);
            setReport(reportRes.data);
            if (interpRes) {
                setInterpretation(interpRes.data);
            }
        } catch (err: any) {
            console.error('Failed to load report:', err);
            setError(err.response?.data?.detail || '加载报告失败');
        } finally {
            setLoading(false);
        }
    };

    const handleShare = async () => {
        if (!id) return;
        setSharing(true);
        try {
            const response = await testsApi.generateShareLink(parseInt(id));
            setShareLink(response.data.share_url);
            setIsShareModalOpen(true);
        } catch (err: any) {
            console.error('Failed to generate share link:', err);
            alert(err.response?.data?.detail || '生成分享链接失败');
        } finally {
            setSharing(false);
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 className="animate-spin text-primary mb-4" size={40} />
                    <p className="text-text-sub">报告加载中...</p>
                </div>
            </DashboardLayout>
        );
    }

    if (error || !report) {
        return (
            <DashboardLayout>
                <div className="text-center py-10 bg-red-50 text-red-600 rounded-xl border border-red-100">
                    {error || '报告不存在'}
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate(-1)}
                        className="p-2 -ml-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold text-text-main">测评报告</h1>
                        <p className="text-text-sub text-sm mt-1">{report.level} - {report.unit}</p>
                    </div>
                </div>
                <button
                    onClick={handleShare}
                    disabled={sharing}
                    className="btn-primary flex items-center gap-2 px-4 py-2"
                >
                    {sharing ? (
                        <Loader2 className="animate-spin" size={18} />
                    ) : (
                        <Share2 size={18} />
                    )}
                    <span>分享给家长</span>
                </button>
            </div>

            <div className="max-w-4xl mx-auto space-y-8">
                {/* Score Card */}
                <div className="bg-gradient-to-br from-[#002FA7] to-[#001A5C] text-white rounded-2xl p-8 shadow-xl shadow-primary/20 relative overflow-hidden">
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
                                    <span className="text-2xl font-bold font-mono">{report.part1_score?.toFixed(1) || 'N/A'}</span>
                                </div>
                                <div className="w-px bg-white/10"></div>
                                <div>
                                    <span className="block text-white/60 text-xs uppercase tracking-wider mb-1">Part 2 问答</span>
                                    <span className="text-2xl font-bold font-mono">{report.part2_score?.toFixed(1) || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        <div className="text-right">
                            <span className="block text-white/60 text-sm mb-1">总分</span>
                            <div className="text-7xl font-bold font-mono tracking-tighter leading-none">
                                {report.total_score?.toFixed(1) || 'N/A'}
                            </div>
                        </div>
                    </div>
                </div>

                {/* AI Interpretation */}
                {interpretation && (
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-text-main flex items-center gap-2">
                            <span className="bg-secondary/20 w-8 h-8 rounded-lg flex items-center justify-center text-secondary-hover text-lg">
                                🤖
                            </span>
                            AI 智能解读
                        </h3>

                        <div className="grid md:grid-cols-2 gap-6">
                            {/* Highlights */}
                            {interpretation.highlights && interpretation.highlights.length > 0 && (
                                <div className="card-surface p-6 border border-emerald-100">
                                    <h4 className="text-lg font-bold text-emerald-800 mb-4 flex items-center gap-2">
                                        ✨ 表现亮点
                                    </h4>
                                    <ul className="space-y-3">
                                        {interpretation.highlights.map((item, i) => (
                                            <li key={i} className="flex gap-3 text-emerald-900/80 text-sm leading-relaxed">
                                                <span className="text-emerald-500 mt-0.5">•</span>
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Weaknesses */}
                            {interpretation.weaknesses && interpretation.weaknesses.length > 0 && (
                                <div className="card-surface p-6 border border-rose-100">
                                    <h4 className="text-lg font-bold text-rose-800 mb-4 flex items-center gap-2">
                                        💪 待提升点
                                    </h4>
                                    <ul className="space-y-3">
                                        {interpretation.weaknesses.map((item, i) => (
                                            <li key={i} className="flex gap-3 text-rose-900/80 text-sm leading-relaxed">
                                                <span className="text-rose-500 mt-0.5">•</span>
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>

                        {/* Suggestions */}
                        {interpretation.suggestions && interpretation.suggestions.length > 0 && (
                            <div className="card-surface p-6 border border-blue-100">
                                <h4 className="text-lg font-bold text-blue-800 mb-4 flex items-center gap-2">
                                    📝 学习建议
                                </h4>
                                <div className="grid md:grid-cols-3 gap-4">
                                    {interpretation.suggestions.map((item, i) => (
                                        <div key={i} className="bg-blue-50/50 rounded-lg p-4 text-blue-900/80 text-sm leading-relaxed">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Parent Script */}
                        {interpretation.parent_script && (
                            <div className="card-surface p-6 border border-amber-100 bg-amber-50/50">
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
                        )}
                    </div>
                )}

                {/* Detailed Items */}
                {report.part2_items && report.part2_items.length > 0 && (
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-text-main border-l-4 border-primary pl-4">详细评分</h3>
                        <div className="space-y-4">
                            {report.part2_items.map((item) => (
                                <div key={item.question_no} className="card-surface p-6 border border-gray-100">
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
            <LinkGeneratedModal
                isOpen={isShareModalOpen}
                onClose={() => setIsShareModalOpen(false)}
                link={shareLink}
                title="报告链接已生成"
                subtitle="请分享给家长"
            />
        </DashboardLayout>
    );
};

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Copy, CheckCircle, BookOpen, Lightbulb, Target, MessageSquare } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { testsApi, type Interpretation, type TestReport } from '../../api';

export const InterpretationPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
    const [report, setReport] = useState<TestReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [copiedScript, setCopiedScript] = useState(false);

    useEffect(() => {
        if (id) {
            loadData();
        }
    }, [id]);

    const loadData = async () => {
        if (!id) return;
        try {
            setLoading(true);
            const [interpRes, reportRes] = await Promise.all([
                testsApi.getInterpretation(parseInt(id)),
                testsApi.getReport(parseInt(id)).catch(() => null)
            ]);
            setInterpretation(interpRes.data);
            if (reportRes) {
                setReport(reportRes.data);
            }
        } catch (err: any) {
            console.error('Failed to load interpretation:', err);
            if (err.response?.status === 404) {
                setError('报告解读尚未生成，请先在测评历史页面点击"生成报告解读"按钮');
            } else {
                setError(err.response?.data?.detail || '加载报告解读失败');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleCopyScript = async () => {
        if (!interpretation?.parent_script) return;
        try {
            await navigator.clipboard.writeText(interpretation.parent_script);
            setCopiedScript(true);
            setTimeout(() => setCopiedScript(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 className="animate-spin text-primary mb-4" size={40} />
                    <p className="text-text-sub">加载中...</p>
                </div>
            </DashboardLayout>
        );
    }

    if (error || !interpretation) {
        return (
            <DashboardLayout>
                <div className="flex items-center gap-4 mb-8">
                    <button
                        onClick={() => navigate(-1)}
                        className="p-2 -ml-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <h1 className="text-2xl font-bold text-text-main">报告解读</h1>
                </div>
                <div className="text-center py-10 bg-amber-50 text-amber-700 rounded-xl border border-amber-100">
                    <BookOpen className="mx-auto mb-3 opacity-50" size={40} />
                    <p>{error || '报告解读不存在'}</p>
                    <button
                        onClick={() => navigate(-1)}
                        className="mt-4 text-primary hover:underline"
                    >
                        返回上一页
                    </button>
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
                        <h1 className="text-3xl font-bold text-text-main flex items-center gap-3">
                            <span className="bg-gradient-to-br from-primary to-blue-600 text-white w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
                                <BookOpen size={20} />
                            </span>
                            AI 报告解读
                        </h1>
                        {report && (
                            <p className="text-text-sub text-sm mt-1 ml-[52px]">
                                {report.student_name} · {report.level} - {report.unit}
                            </p>
                        )}
                    </div>
                </div>
                <button
                    onClick={() => navigate(`/report/${id}`)}
                    className="px-4 py-2 border border-border bg-white text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-slate-50 transition-colors"
                >
                    查看完整报告
                </button>
            </div>

            <div className="max-w-4xl mx-auto space-y-8">
                {/* Score Summary (if available) */}
                {report && (
                    <div className="bg-gradient-to-r from-primary/5 to-secondary/5 rounded-2xl p-6 border border-primary/10">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-6">
                                <div className="text-center">
                                    <span className="block text-text-sub text-xs mb-1">总分</span>
                                    <span className="text-4xl font-bold text-primary font-mono">
                                        {report.total_score?.toFixed(1) || 'N/A'}
                                    </span>
                                </div>
                                <div className="w-px h-12 bg-gray-200"></div>
                                <div className="flex text-yellow-400 text-xl">
                                    {'⭐'.repeat(report.star_level || 0)}
                                    <span className="text-gray-200">
                                        {'⭐'.repeat(5 - (report.star_level || 0))}
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-8 text-sm">
                                <div className="text-center">
                                    <span className="block text-text-sub text-xs mb-1">朗读</span>
                                    <span className="font-bold text-text-main font-mono">{report.part1_score?.toFixed(1) || '-'}</span>
                                </div>
                                <div className="text-center">
                                    <span className="block text-text-sub text-xs mb-1">问答</span>
                                    <span className="font-bold text-text-main font-mono">{report.part2_score?.toFixed(1) || '-'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Highlights */}
                {interpretation.highlights && interpretation.highlights.length > 0 && (
                    <div className="card-surface p-6 border-l-4 border-emerald-500 animate-in slide-in-from-left-4 duration-500">
                        <h3 className="text-xl font-bold text-emerald-700 mb-5 flex items-center gap-3">
                            <span className="bg-emerald-100 w-10 h-10 rounded-xl flex items-center justify-center">
                                ✨
                            </span>
                            表现亮点
                        </h3>
                        <div className="grid gap-4">
                            {interpretation.highlights.map((item, i) => (
                                <div 
                                    key={i} 
                                    className="flex gap-4 p-4 bg-emerald-50/50 rounded-xl border border-emerald-100"
                                    style={{ animationDelay: `${i * 100}ms` }}
                                >
                                    <span className="flex-shrink-0 w-8 h-8 bg-emerald-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">
                                        {i + 1}
                                    </span>
                                    <p className="text-emerald-900/80 leading-relaxed pt-1">{item}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Weaknesses */}
                {interpretation.weaknesses && interpretation.weaknesses.length > 0 && (
                    <div className="card-surface p-6 border-l-4 border-rose-500 animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: '100ms' }}>
                        <h3 className="text-xl font-bold text-rose-700 mb-5 flex items-center gap-3">
                            <span className="bg-rose-100 w-10 h-10 rounded-xl flex items-center justify-center">
                                <Target size={20} className="text-rose-600" />
                            </span>
                            待提升点
                        </h3>
                        <div className="grid gap-4">
                            {interpretation.weaknesses.map((item, i) => (
                                <div 
                                    key={i} 
                                    className="flex gap-4 p-4 bg-rose-50/50 rounded-xl border border-rose-100"
                                >
                                    <span className="flex-shrink-0 w-8 h-8 bg-rose-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">
                                        {i + 1}
                                    </span>
                                    <p className="text-rose-900/80 leading-relaxed pt-1">{item}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Evidence */}
                {interpretation.evidence && interpretation.evidence.length > 0 && (
                    <div className="card-surface p-6 border-l-4 border-slate-400 animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: '200ms' }}>
                        <h3 className="text-xl font-bold text-slate-700 mb-5 flex items-center gap-3">
                            <span className="bg-slate-100 w-10 h-10 rounded-xl flex items-center justify-center">
                                📋
                            </span>
                            评估依据
                        </h3>
                        <div className="space-y-3">
                            {interpretation.evidence.map((item, i) => (
                                <div 
                                    key={i} 
                                    className="flex gap-3 text-slate-700 text-sm leading-relaxed"
                                >
                                    <span className="text-slate-400 font-mono text-xs mt-0.5">#{i + 1}</span>
                                    <p className="flex-1 bg-slate-50 rounded-lg p-3 border border-slate-100">{item}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Suggestions */}
                {interpretation.suggestions && interpretation.suggestions.length > 0 && (
                    <div className="card-surface p-6 border-l-4 border-blue-500 animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: '300ms' }}>
                        <h3 className="text-xl font-bold text-blue-700 mb-5 flex items-center gap-3">
                            <span className="bg-blue-100 w-10 h-10 rounded-xl flex items-center justify-center">
                                <Lightbulb size={20} className="text-blue-600" />
                            </span>
                            学习建议
                        </h3>
                        <div className="grid md:grid-cols-2 gap-4">
                            {interpretation.suggestions.map((item, i) => (
                                <div 
                                    key={i} 
                                    className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100"
                                >
                                    <div className="flex items-start gap-3">
                                        <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-xs">
                                            {i + 1}
                                        </span>
                                        <p className="text-blue-900/80 leading-relaxed text-sm">{item}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Parent Script */}
                {interpretation.parent_script && (
                    <div className="card-surface p-6 border-l-4 border-amber-500 bg-gradient-to-br from-amber-50/80 to-orange-50/80 animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: '400ms' }}>
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-xl font-bold text-amber-700 flex items-center gap-3">
                                <span className="bg-amber-100 w-10 h-10 rounded-xl flex items-center justify-center">
                                    <MessageSquare size={20} className="text-amber-600" />
                                </span>
                                家长沟通话术
                            </h3>
                            <button
                                onClick={handleCopyScript}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                                    copiedScript 
                                        ? 'bg-emerald-100 text-emerald-700' 
                                        : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                                }`}
                            >
                                {copiedScript ? (
                                    <>
                                        <CheckCircle size={16} />
                                        已复制
                                    </>
                                ) : (
                                    <>
                                        <Copy size={16} />
                                        复制话术
                                    </>
                                )}
                            </button>
                        </div>
                        <div className="bg-white/80 rounded-xl p-6 text-amber-900/80 leading-relaxed whitespace-pre-wrap border border-amber-100 shadow-inner">
                            {interpretation.parent_script}
                        </div>
                        <p className="text-xs text-amber-600/70 mt-4 flex items-center gap-1">
                            <span>💡</span>
                            此话术由 AI 生成，请根据实际情况适当调整后使用
                        </p>
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
};

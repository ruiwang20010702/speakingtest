import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Copy, CheckCircle, BookOpen, Radar, BookText, MessageCircle, Map, Award, FileText, RefreshCw } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { testsApi, type Interpretation, type TestReport } from '../../api';

// 页面配置
const PAGE_CONFIG = {
    cover: { 
        label: '封面', 
        icon: BookOpen, 
        color: 'blue',
        description: '开场问候',
        duration: '约1分钟'
    },
    radar: { 
        label: '能力图谱', 
        icon: Radar, 
        color: 'purple',
        description: '五维能力分析',
        duration: '约2分钟'
    },
    vocab: { 
        label: '词汇掌握', 
        icon: BookText, 
        color: 'green',
        description: '单词发音分析',
        duration: '约2分钟'
    },
    dialogue: { 
        label: '对话表现', 
        icon: MessageCircle, 
        color: 'orange',
        description: '问答环节分析',
        duration: '约2分钟'
    },
    roadmap: { 
        label: '成长计划', 
        icon: Map, 
        color: 'rose',
        description: '综合建议',
        duration: '约2分钟'
    },
    badge: { 
        label: '徽章', 
        icon: Award, 
        color: 'amber',
        description: '结束语',
        duration: '约1分钟'
    },
} as const;

type PageKey = keyof typeof PAGE_CONFIG;

const PAGE_ORDER: PageKey[] = ['cover', 'radar', 'vocab', 'dialogue', 'roadmap', 'badge'];

// 颜色映射
const colorClasses = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', badge: 'bg-blue-100' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', badge: 'bg-purple-100' },
    green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100' },
    orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', badge: 'bg-orange-100' },
    rose: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', badge: 'bg-rose-100' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100' },
};

export const InterpretationPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
    const [report, setReport] = useState<TestReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [regenerating, setRegenerating] = useState(false);
    const [error, setError] = useState('');
    const [copiedPage, setCopiedPage] = useState<string | null>(null);
    const [copiedFull, setCopiedFull] = useState(false);
    const [activeTab, setActiveTab] = useState<PageKey>('cover');

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
                setError('演讲稿尚未生成，请先在测评历史页面点击"生成报告解读"按钮');
            } else {
                setError(err.response?.data?.detail || '加载演讲稿失败');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleRegenerate = async () => {
        if (!id || regenerating) return;
        
        if (!confirm('确定要重新生成演讲稿吗？这将覆盖当前的内容。')) {
            return;
        }
        
        try {
            setRegenerating(true);
            const res = await testsApi.generateInterpretation(parseInt(id), true);
            setInterpretation(res.data);
            setError('');
        } catch (err: any) {
            console.error('Failed to regenerate interpretation:', err);
            alert(err.response?.data?.detail || '重新生成失败');
        } finally {
            setRegenerating(false);
        }
    };

    const handleCopyPage = async (pageKey: PageKey) => {
        if (!interpretation?.pages[pageKey]) return;
        try {
            await navigator.clipboard.writeText(interpretation.pages[pageKey]);
            setCopiedPage(pageKey);
            setTimeout(() => setCopiedPage(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const handleCopyFullScript = async () => {
        if (!interpretation?.full_script) return;
        try {
            await navigator.clipboard.writeText(interpretation.full_script);
            setCopiedFull(true);
            setTimeout(() => setCopiedFull(false), 2000);
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
                    <h1 className="text-2xl font-bold text-text-main">班主任演讲稿</h1>
                </div>
                <div className="text-center py-10 bg-amber-50 text-amber-700 rounded-xl border border-amber-100">
                    <FileText className="mx-auto mb-3 opacity-50" size={40} />
                    <p>{error || '演讲稿不存在'}</p>
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

    const currentScript = interpretation.pages[activeTab];
    const config = PAGE_CONFIG[activeTab];
    const colors = colorClasses[config.color];
    const Icon = config.icon;

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate(-1)}
                        className="p-2 -ml-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-text-main flex items-center gap-3">
                            <span className="bg-gradient-to-br from-primary to-blue-600 text-white w-9 h-9 rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
                                <FileText size={18} />
                            </span>
                            班主任演讲稿
                        </h1>
                        {report && (
                            <p className="text-text-sub text-sm mt-1 ml-12">
                                {report.student_name} · {report.level} - {report.unit} · 约10分钟
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRegenerate}
                        disabled={regenerating}
                        className="px-4 py-2 border border-orange-200 bg-orange-50 text-orange-700 rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-orange-100 transition-colors disabled:opacity-50"
                        title="修改报告内容后可重新生成"
                    >
                        {regenerating ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                生成中...
                            </>
                        ) : (
                            <>
                                <RefreshCw size={16} />
                                重新生成
                            </>
                        )}
                    </button>
                    <button
                        onClick={() => navigate(`/report/${id}`)}
                        className="px-4 py-2 border border-border bg-white text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-slate-50 transition-colors"
                    >
                        查看报告
                    </button>
                </div>
            </div>

            {/* 一键复制完整演讲稿 */}
            <div className="bg-gradient-to-r from-primary/5 to-secondary/5 rounded-2xl p-4 border border-primary/10 mb-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <FileText className="text-primary" size={20} />
                        <div>
                            <span className="font-medium text-text-main">完整演讲稿</span>
                            <span className="text-text-sub text-sm ml-2">约 {interpretation.full_script.length} 字</span>
                        </div>
                    </div>
                    <button
                        onClick={handleCopyFullScript}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                            copiedFull 
                                ? 'bg-emerald-100 text-emerald-700' 
                                : 'bg-primary text-white hover:bg-primary/90'
                        }`}
                    >
                        {copiedFull ? (
                            <>
                                <CheckCircle size={16} />
                                已复制
                            </>
                        ) : (
                            <>
                                <Copy size={16} />
                                一键复制全部
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="grid lg:grid-cols-4 gap-6">
                {/* 左侧：Tab 导航 */}
                <div className="lg:col-span-1">
                    <div className="bg-white rounded-2xl border border-gray-100 p-2 sticky top-6">
                        <h3 className="text-sm font-semibold text-gray-500 px-3 py-2 mb-1">演讲流程</h3>
                        <div className="space-y-1">
                            {PAGE_ORDER.map((key, index) => {
                                const cfg = PAGE_CONFIG[key];
                                const isActive = activeTab === key;
                                const cls = colorClasses[cfg.color];
                                
                                return (
                                    <button
                                        key={key}
                                        onClick={() => setActiveTab(key)}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left ${
                                            isActive 
                                                ? `${cls.bg} ${cls.border} border ${cls.text}` 
                                                : 'hover:bg-gray-50 text-gray-600'
                                        }`}
                                    >
                                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                            isActive ? cls.badge + ' ' + cls.text : 'bg-gray-100 text-gray-500'
                                        }`}>
                                            {index + 1}
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <span className={`block text-sm font-medium ${isActive ? cls.text : ''}`}>
                                                {cfg.label}
                                            </span>
                                            <span className="block text-xs text-gray-400">
                                                {cfg.duration}
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* 右侧：演讲内容 */}
                <div className="lg:col-span-3">
                    <div className={`rounded-2xl border ${colors.border} ${colors.bg} p-6`}>
                        {/* 页面标题 */}
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-xl ${colors.badge} flex items-center justify-center`}>
                                    <Icon size={20} className={colors.text} />
                                </div>
                                <div>
                                    <h3 className={`text-lg font-bold ${colors.text}`}>{config.label}</h3>
                                    <p className="text-xs text-gray-500">{config.description} · {config.duration}</p>
                                </div>
                            </div>
                            <button
                                onClick={() => handleCopyPage(activeTab)}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-sm transition-all ${
                                    copiedPage === activeTab 
                                        ? 'bg-emerald-100 text-emerald-700' 
                                        : `${colors.badge} ${colors.text} hover:opacity-80`
                                }`}
                            >
                                {copiedPage === activeTab ? (
                                    <>
                                        <CheckCircle size={14} />
                                        已复制
                                    </>
                                ) : (
                                    <>
                                        <Copy size={14} />
                                        复制此页
                                    </>
                                )}
                            </button>
                        </div>

                        {/* 演讲内容 */}
                        <div className="bg-white/80 rounded-xl p-5 border border-gray-100 shadow-inner">
                            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap text-[15px]">
                                {currentScript}
                            </p>
                        </div>

                        {/* 导航按钮 */}
                        <div className="flex justify-between mt-4">
                            <button
                                onClick={() => {
                                    const idx = PAGE_ORDER.indexOf(activeTab);
                                    if (idx > 0) setActiveTab(PAGE_ORDER[idx - 1]);
                                }}
                                disabled={activeTab === 'cover'}
                                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                ← 上一页
                            </button>
                            <button
                                onClick={() => {
                                    const idx = PAGE_ORDER.indexOf(activeTab);
                                    if (idx < PAGE_ORDER.length - 1) setActiveTab(PAGE_ORDER[idx + 1]);
                                }}
                                disabled={activeTab === 'badge'}
                                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                下一页 →
                            </button>
                        </div>
                    </div>

                    {/* 提示 */}
                    <p className="text-xs text-gray-400 mt-4 text-center">
                        💡 此演讲稿由 AI 生成，建议根据实际情况适当调整后使用
                    </p>
                </div>
            </div>
        </DashboardLayout>
    );
};

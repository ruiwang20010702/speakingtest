import React, { useEffect, useState, useRef } from 'react';
import { ArrowLeft, Plus, QrCode, FileText, Loader2, Sparkles, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { StatusBadge } from '../../components/UI/StatusBadge';
import { NewAssessmentModal } from './components/NewAssessmentModal';
import { LinkGeneratedModal } from './components/LinkGeneratedModal';
import { studentsApi, testsApi, adminApi } from '../../api';
import type { Student, Assessment } from '../../types';

export const AssessmentHistoryPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const location = useLocation();

    const [student, setStudent] = useState<Student | undefined>(location.state?.student);
    const [assessments, setAssessments] = useState<Assessment[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // Modal States
    const [isNewModalOpen, setIsNewModalOpen] = useState(false);
    const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
    const [generatedLink, setGeneratedLink] = useState('');
    const [modalConfig, setModalConfig] = useState({ title: '测评链接已生成', subtitle: '请分享给学生' });
    const [isCreating, setIsCreating] = useState(false);
    const [isGeneratingShareLink, setIsGeneratingShareLink] = useState(false);
    const [generatingInterpretation, setGeneratingInterpretation] = useState<string | null>(null);
    const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
    
    // 轮询计时器和计数
    const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollingCountRef = useRef(0);
    const MAX_POLLING_COUNT = 40; // 最多轮询 40 次
    const POLLING_INTERVAL = 10000; // 每 10 秒一次（总时长约 6-7 分钟）

    const loadData = async () => {
        if (!id) return;
            setIsLoading(true);
        try {
            const [testsRes, listRes] = await Promise.all([
                studentsApi.getTests(Number(id)),
                !student ? studentsApi.list() : Promise.resolve({ data: [] })
            ]);

            // Map tests
            // 后端状态: pending -> part1_processing -> part1_done -> processing -> completed / failed
            const mapStatus = (backendStatus: string): 'pending' | 'in_progress' | 'completed' | 'failed' => {
                if (backendStatus === 'completed') return 'completed';
                if (backendStatus === 'failed') return 'failed';
                if (['part1_processing', 'part1_done', 'processing', 'in_progress'].includes(backendStatus)) {
                    return 'in_progress';
                }
                // 'pending' 或其他未知状态
                return 'pending';
            };

            const mappedAssessments: Assessment[] = testsRes.data.map((t: any) => ({
                id: String(t.id),
                studentId: id,
                title: `${t.level} - ${t.unit}`,
                level: t.level,
                unit: t.unit,
                status: mapStatus(t.status),
                score: t.total_score,
                stars: t.star_level,
                createdAt: t.created_at,
                completedAt: t.completed_at,
                entryUrl: t.entry_url,
                isInterpreted: t.is_interpreted ?? false,
                interpretationStatus: t.interpretation_status ?? 'pending',
                failureReason: t.failure_reason,
                retryCount: t.retry_count ?? 0
            }));
            setAssessments(mappedAssessments);

            // If we didn't have student data, find it in the list
            if (!student && Array.isArray(listRes.data)) {
                const found = listRes.data.find((s: any) => String(s.user_id) === id);
                if (found) {
                    setStudent({
                        id: found.external_user_id || String(found.user_id),
                        internalId: String(found.user_id),
                        name: found.student_name,
                        grade: found.cur_grade || '未设置',
                        level: found.cur_level_desc || 'N/A',
                        currentUnit: found.main_last_buy_unit_name || 'N/A',
                        status: 'active'
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load assessment history:', error);
        } finally {
            setIsLoading(false);
        }
        };

    useEffect(() => {
        loadData();
    }, [id]);

    // 轮询：当有 "generating" 状态的解读时，每 3 秒刷新一次（最多 2 分钟）
    useEffect(() => {
        const hasGenerating = assessments.some(a => a.interpretationStatus === 'generating');
        
        if (hasGenerating) {
            // 检查是否超过最大轮询次数
            if (pollingCountRef.current >= MAX_POLLING_COUNT) {
                console.warn('轮询超时，停止轮询。请手动刷新页面查看状态。');
                if (pollingIntervalRef.current) {
                    clearInterval(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                }
                return;
            }
            
            // 启动轮询
            if (!pollingIntervalRef.current) {
                pollingIntervalRef.current = setInterval(() => {
                    pollingCountRef.current += 1;
                    console.log(`轮询中... (${pollingCountRef.current}/${MAX_POLLING_COUNT})`);
                    
                    if (pollingCountRef.current >= MAX_POLLING_COUNT) {
                        console.warn('轮询达到上限，自动停止');
                        if (pollingIntervalRef.current) {
                            clearInterval(pollingIntervalRef.current);
                            pollingIntervalRef.current = null;
                        }
                        return;
                    }
                    
                    loadData();
                }, POLLING_INTERVAL);
            }
        } else {
            // 停止轮询并重置计数
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
            pollingCountRef.current = 0; // 重置计数
        }
        
        // 清理
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [assessments]);

    const handleCreateAssessment = async (level: string, unit: string) => {
        if (!id) return;
        setIsCreating(true);
        try {
            const res = await studentsApi.generateToken(Number(id), level, unit);
            // Use the entry_url directly from backend response
            const link = res.data.entry_url;
            
            setGeneratedLink(link);
            setModalConfig({ title: '测评链接已生成', subtitle: '请分享给学生' });
            setIsNewModalOpen(false);
            setIsLinkModalOpen(true);
            
            // Reload list to see new assessment (if it appears immediately)
            loadData();
        } catch (error) {
            console.error('Failed to create assessment:', error);
        } finally {
        setIsCreating(false);
        }
    };

    const handleShowQRCode = async (assessment: Assessment) => {
        let linkToShow = '';
        
        if (assessment.status === 'completed') {
            // For completed assessments, generate share link
            try {
                setIsGeneratingShareLink(true);
                const res = await testsApi.generateShareLink(Number(assessment.id));
                linkToShow = res.data.share_url;
                setModalConfig({ title: '报告链接已生成', subtitle: '请分享给家长' });
            } catch (error) {
                console.error('Failed to generate share link:', error);
                alert('生成分享链接失败，请重试');
                return;
            } finally {
                setIsGeneratingShareLink(false);
            }
        } else {
            // For in-progress assessments, use entry_url
            linkToShow = (assessment as any).entryUrl || '';
            if (!linkToShow) {
                alert('该测评尚未生成链接');
                return;
            }
            setModalConfig({ title: '测评链接已生成', subtitle: '请分享给学生' });
        }

        setGeneratedLink(linkToShow);
        setIsLinkModalOpen(true);
    };

    const handleGenerateInterpretation = async (testId: string) => {
        setGeneratingInterpretation(testId);
        try {
            await testsApi.generateInterpretation(Number(testId));
            // Refresh list to update button state
            loadData();
        } catch (error) {
            console.error('Failed to generate interpretation:', error);
            alert('生成报告解读失败，请重试');
        } finally {
            setGeneratingInterpretation(null);
        }
    };

    const handleRegenerate = async (testId: string) => {
        setRegeneratingId(testId);
        try {
            const response = await adminApi.regenerateReport(Number(testId));
            if (response.data.success) {
                alert(response.data.message);
                loadData();
            }
        } catch (error: any) {
            console.error('Failed to regenerate report:', error);
            alert(error.response?.data?.detail || '重新生成报告失败，请重试');
        } finally {
            setRegeneratingId(null);
        }
    };

    if (isLoading && !student) {
        return (
            <DashboardLayout>
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            </DashboardLayout>
        );
    }

    if (!student && !isLoading) return <DashboardLayout>未找到学生</DashboardLayout>;

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="p-2 -ml-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h2 className="text-2xl font-bold text-text-main">{student!.name}</h2>
                        <p className="text-text-sub text-sm">ID: {student!.id} | {student!.level}</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsNewModalOpen(true)}
                    className="btn-primary py-2.5 px-5 flex items-center gap-2 text-sm"
                >
                    <Plus size={18} />
                    <span>发起新测评</span>
                </button>
            </div>

            {/* Assessment List */}
            <div className="space-y-4">
                <h3 className="text-lg font-bold text-text-main">测评记录</h3>
                {assessments.length > 0 ? (
                    assessments.map(assessment => (
                    <div key={assessment.id} className="card-surface p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">

                        {/* Left: Info */}
                        <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                                <h4 className="font-bold text-text-main text-lg">{assessment.title}</h4>
                                <StatusBadge status={assessment.status} />
                            </div>
                            <div className="flex items-center gap-4 text-sm text-text-sub">
                                <span>{new Date(assessment.createdAt).toLocaleDateString()}</span>
                                    {assessment.completedAt && (
                                        <span>
                                            完成时间: {new Date(assessment.completedAt).toLocaleString([], { 
                                                year: 'numeric',
                                                month: '2-digit',
                                                day: '2-digit',
                                                hour: '2-digit', 
                                                minute: '2-digit' 
                                            })}
                                        </span>
                                    )}
                            </div>
                            {/* Score Display */}
                            {assessment.status === 'completed' && assessment.score !== undefined && (
                                <div className="mt-4 flex items-center gap-3">
                                    <span className="text-3xl font-bold text-primary">{assessment.score}</span>
                                    <div className="flex text-secondary">
                                            {[...Array(5)].map((_, i) => (
                                            <svg key={i} className={`w-5 h-5 ${(assessment.stars || 0) > i ? 'fill-current' : 'text-slate-200 fill-current'}`} viewBox="0 0 20 20">
                                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                            </svg>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            {/* Failure Info Display */}
                            {assessment.status === 'failed' && (
                                <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
                                    <div className="flex items-start gap-2">
                                        <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-red-700">评测失败</p>
                                            {assessment.failureReason && (
                                                <p className="text-xs text-red-600 mt-1 break-all">
                                                    原因: {assessment.failureReason}
                                                </p>
                                            )}
                                            {(assessment.retryCount ?? 0) > 0 && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    已重试 {assessment.retryCount} 次
                                                </p>
                                            )}
                                            <button
                                                onClick={() => handleRegenerate(assessment.id)}
                                                disabled={regeneratingId === assessment.id || (assessment.retryCount ?? 0) >= 5}
                                                className="mt-2 px-3 py-1.5 bg-green-600 text-white rounded-md font-medium text-xs flex items-center gap-1.5 hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {regeneratingId === assessment.id ? (
                                                    <>
                                                        <Loader2 size={12} className="animate-spin" />
                                                        生成中...
                                                    </>
                                                ) : (assessment.retryCount ?? 0) >= 5 ? (
                                                    '已达重试上限'
                                                ) : (
                                                    <>
                                                        <RefreshCw size={12} />
                                                        重新生成报告
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Right: Actions */}
                        <div className="flex items-center gap-3">
                            {assessment.status === 'completed' ? (
                                    <>
                                        <button 
                                            onClick={() => navigate(`/report/${assessment.id}`)}
                                            className="px-4 py-2 bg-blue-50 text-primary rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-blue-100 transition-colors"
                                        >
                                    <FileText size={16} /> 查看报告
                                </button>
                                        {assessment.isInterpreted ? (
                                            <button 
                                                onClick={() => navigate(`/interpretation/${assessment.id}`)}
                                                className="px-4 py-2 border border-primary/30 bg-primary/5 text-primary rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-primary/10 transition-colors"
                                            >
                                                <BookOpen size={16} /> 查看解读报告
                                            </button>
                                        ) : assessment.interpretationStatus === 'generating' ? (
                                            <button 
                                                disabled
                                                className="px-4 py-2 border border-amber-200 bg-amber-50 text-amber-700 rounded-lg font-medium text-sm flex items-center gap-2 cursor-not-allowed"
                                            >
                                                <Loader2 className="animate-spin" size={16} />
                                                AI 生成中...
                                            </button>
                                        ) : assessment.interpretationStatus === 'failed' ? (
                                            <button 
                                                onClick={() => handleGenerateInterpretation(assessment.id)}
                                                disabled={generatingInterpretation === assessment.id}
                                                className="px-4 py-2 border border-red-200 bg-red-50 text-red-600 rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-red-100 transition-colors disabled:opacity-50"
                                            >
                                                {generatingInterpretation === assessment.id ? (
                                                    <Loader2 className="animate-spin" size={16} />
                                                ) : (
                                                    <AlertCircle size={16} />
                                                )}
                                                生成失败，点击重试
                                            </button>
                                        ) : (
                                            <button 
                                                onClick={() => handleGenerateInterpretation(assessment.id)}
                                                disabled={generatingInterpretation === assessment.id}
                                                className="px-4 py-2 border border-border bg-white text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-slate-50 transition-colors disabled:opacity-50"
                                            >
                                                {generatingInterpretation === assessment.id ? (
                                                    <Loader2 className="animate-spin" size={16} />
                                                ) : (
                                                    <Sparkles size={16} />
                                                )}
                                                生成报告解读
                                            </button>
                                        )}
                                    </>
                            ) : (
                                        <button 
                                            onClick={() => handleShowQRCode(assessment)}
                                            disabled={isGeneratingShareLink}
                                            className="px-4 py-2 border border-border bg-white text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-slate-50 transition-colors disabled:opacity-50"
                                        >
                                    <QrCode size={16} /> 测试二维码
                                    </button>
                            )}
                        </div>
                    </div>
                    ))
                ) : (
                    <div className="text-center py-10 text-text-sub">
                        暂无测评记录
                    </div>
                )}
            </div>

            {/* Modals */}
            <NewAssessmentModal
                isOpen={isNewModalOpen}
                onClose={() => setIsNewModalOpen(false)}
                onSubmit={handleCreateAssessment}
                isCreating={isCreating}
            />

            <LinkGeneratedModal
                isOpen={isLinkModalOpen}
                onClose={() => setIsLinkModalOpen(false)}
                link={generatedLink}
                title={modalConfig.title}
                subtitle={modalConfig.subtitle}
            />
        </DashboardLayout>
    );
};

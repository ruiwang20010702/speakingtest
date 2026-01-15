import React, { useEffect, useState, useRef } from 'react';
import { ArrowLeft, Loader2, Share2, Edit3 } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { testsApi, type TestReport, type Interpretation } from '../../api';
import { LinkGeneratedModal } from '../Assessment/components/LinkGeneratedModal';
import { PhoneMockup } from '../../components/PhoneMockup';
import { EditReportModal } from './components/EditReportModal';

export const ReportPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const iframeKey = useRef(0);

    const [report, setReport] = useState<TestReport | null>(null);
    const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [shareUrl, setShareUrl] = useState('');
    const [previewLoading, setPreviewLoading] = useState(true);
    const [sharing, setSharing] = useState(false);
    const [isShareModalOpen, setIsShareModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);

    useEffect(() => {
        if (id) {
            loadData();
        }
    }, [id]);

    const loadData = async () => {
        if (!id) return;
        try {
            setLoading(true);
            setPreviewLoading(true);
            
            // Load report info, interpretation, and generate share link in parallel
            const [reportRes, shareRes, interpRes] = await Promise.all([
                testsApi.getReport(parseInt(id)),
                testsApi.generateShareLink(parseInt(id)),
                testsApi.getInterpretation(parseInt(id)).catch(() => null)
            ]);
            
            setReport(reportRes.data);
            setShareUrl(shareRes.data.share_url);
            if (interpRes) {
                setInterpretation(interpRes.data);
            }
        } catch (err: any) {
            console.error('Failed to load report:', err);
            setError(err.response?.data?.detail || '加载报告失败');
        } finally {
            setLoading(false);
            // Give iframe a moment to start loading
            setTimeout(() => setPreviewLoading(false), 500);
        }
    };

    const handleShare = () => {
        if (shareUrl) {
            setIsShareModalOpen(true);
        }
    };

    const handleEdit = () => {
        setIsEditModalOpen(true);
    };

    const handleEditSaved = () => {
        // Reload data and refresh iframe
        iframeKey.current += 1;
        loadData();
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
                        <h1 className="text-3xl font-bold text-text-main">测评报告预览</h1>
                        <p className="text-text-sub text-sm mt-1">
                            {report.student_name} · {report.level} - {report.unit}
                            {report.total_score !== undefined && (
                                <span className="ml-2 text-primary font-medium">
                                    总分: {report.total_score.toFixed(1)}
                                </span>
                            )}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleEdit}
                        className="px-4 py-2 border border-border bg-white text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-slate-50 transition-colors"
                    >
                        <Edit3 size={18} />
                        <span>编辑报告</span>
                    </button>
                <button
                    onClick={handleShare}
                        disabled={sharing || !shareUrl}
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
                                    </div>
                                    
            {/* Phone Preview */}
            <div className="flex justify-center py-8">
                <PhoneMockup 
                    key={iframeKey.current}
                    src={shareUrl} 
                    loading={previewLoading}
                    title={`${report.student_name} 的测评报告`}
                />
            </div>

            {/* Share Modal */}
            <LinkGeneratedModal
                isOpen={isShareModalOpen}
                onClose={() => setIsShareModalOpen(false)}
                link={shareUrl}
                title="报告链接已生成"
                subtitle="请分享给家长"
            />

            {/* Edit Modal */}
            {report && (
                <EditReportModal
                    isOpen={isEditModalOpen}
                    onClose={() => setIsEditModalOpen(false)}
                    testId={parseInt(id!)}
                    report={report}
                    interpretation={interpretation}
                    onSaved={handleEditSaved}
                />
            )}
        </DashboardLayout>
    );
};

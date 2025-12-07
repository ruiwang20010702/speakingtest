/**
 * 历史记录页面 - 51Talk 新设计
 * 显示学生的所有测试记录
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getHistory } from '../services/api';
import type { TestResult } from '../types';
import { ArrowLeft, Calendar, FileText } from 'lucide-react';

export default function HistoryPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const studentName = searchParams.get('student') || '';

    const [records, setRecords] = useState<TestResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadHistory();
    }, [studentName]);

    const loadHistory = async () => {
        try {
            const data = await getHistory(studentName || undefined);
            setRecords(data);
        } catch (err) {
            setError('加载历史记录失败');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
    };

    const getScoreColor = (score: number, max: number = 60) => {
        const percentage = (score / max) * 100;
        if (percentage >= 80) return 'text-green-600';
        if (percentage >= 60) return 'text-yellow-600';
        return 'text-red-600';
    };

    const getScoreBgColor = (score: number, max: number = 60) => {
        const percentage = (score / max) * 100;
        if (percentage >= 80) return 'bg-green-50 border-green-200';
        if (percentage >= 60) return 'bg-yellow-50 border-yellow-200';
        return 'bg-red-50 border-red-200';
    };

    if (loading) {
        return (
            <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
                <div className="absolute inset-0 bg-[#00B4EE]">
                    <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                        </div>
                <div className="relative z-10 min-h-screen flex items-center justify-center">
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-8 text-center">
                        <div className="w-16 h-16 border-4 border-[#FDE700] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-gray-600">加载历史记录中...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
            {/* Blue Background with decorative elements */}
            <div className="absolute inset-0 bg-[#00B4EE]">
                <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                <div className="absolute bottom-0 left-0 w-48 h-32">
                    <div className="absolute bottom-4 left-0 w-24 h-24 bg-white rounded-full -translate-x-1/3" />
                    <div className="absolute bottom-8 left-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute bottom-12 left-6 w-16 h-16 bg-white rounded-full" />
                </div>
                <div className="absolute top-0 right-0 w-48 h-32">
                    <div className="absolute top-4 right-0 w-24 h-24 bg-white rounded-full translate-x-1/3" />
                    <div className="absolute top-8 right-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute top-12 right-6 w-16 h-16 bg-white rounded-full" />
                </div>
                <div className="absolute bottom-0 right-0 w-40 h-40 bg-[#FDE700] translate-x-1/4 translate-y-1/4" style={{ clipPath: 'polygon(0 100%, 100% 100%, 100% 0)' }} />
            </div>

            {/* Content */}
            <div className="relative z-10 p-3 pb-6 min-h-screen">
                <div className="max-w-md mx-auto">
                    {/* Header */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-3">
                        <div className="flex items-center gap-3 mb-2">
                            <button
                                onClick={() => navigate('/')}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <ArrowLeft className="w-5 h-5 text-gray-700" />
                            </button>
                            <div className="flex-1">
                                <h1 className="text-lg font-semibold text-gray-900">历史报告</h1>
                            </div>
                        </div>
                        {studentName && (
                            <p className="text-gray-600 text-sm pl-11">
                                学生: {studentName}
                            </p>
                        )}
                </div>

                    {/* Error Message */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 mb-3">
                            <p className="text-red-700">{error}</p>
                        </div>
                    )}

                    {/* Empty State */}
                    {!error && records.length === 0 && (
                        <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-8 text-center">
                            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                            <p className="text-gray-500 mb-4">暂无历史报告</p>
                            <button 
                                onClick={() => navigate('/')} 
                                className="py-3 px-6 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all"
                            >
                                开始测试
                            </button>
                        </div>
                    )}

                    {/* Reports List */}
                    {!error && records.length > 0 && (
                        <div className="space-y-3">
                            {records.map((record) => (
                                <div
                                    key={record.id}
                                    className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 hover:shadow-xl transition-all cursor-pointer"
                                    onClick={() => navigate(`/result?id=${record.id}`)}
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Calendar className="w-4 h-4 text-[#00B4EE]" />
                                                <span className="text-gray-600 text-sm">
                                                    {formatDate(record.created_at)}
                                                </span>
                                            </div>
                                            <p className="text-gray-900 font-medium">
                                                {record.student_name}
                                            </p>
                                            <p className="text-gray-600 text-sm">
                                                {record.level} - {record.unit}
                                            </p>
                                        </div>
                                        <div className={`px-3 py-1 rounded-full border ${getScoreBgColor(record.total_score)}`}>
                                            <span className={`font-semibold ${getScoreColor(record.total_score)}`}>
                                                {record.total_score}分
                                        </span>
                                    </div>
                                    </div>

                                    {/* Star Rating */}
                                    <div className="flex items-center gap-1 mb-3">
                                        {[1, 2, 3, 4, 5].map((star) => (
                                            <span key={star} className={`text-lg ${star <= record.star_rating ? '' : 'opacity-30'}`}>
                                                ⭐
                                            </span>
                                        ))}
                                    </div>

                                    {/* Part Scores */}
                                    <div className="grid grid-cols-3 gap-2 mb-3">
                                        {record.part_scores.map((part) => (
                                            <div key={part.part_number} className="bg-gray-50 rounded-lg p-2 text-center">
                                                <p className="text-xs text-gray-500">Part {part.part_number}</p>
                                                <p className="font-semibold text-[#00B4EE]">
                                                    {part.score}/{part.max_score}
                                                </p>
                                            </div>
                                        ))}
                                    </div>

                                    <button className="w-full py-2 bg-[#FDE700] text-gray-900 font-medium rounded-lg hover:shadow-md transition-all text-sm">
                                        查看报告
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Back Button */}
                    <div className="mt-4">
                        <button
                            onClick={() => navigate('/')}
                            className="w-full py-4 bg-white/95 backdrop-blur text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all border border-gray-200"
                        >
                            返回首页
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

/**
 * 详细评估反馈页面 - 报告第2页
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getResultById } from '../services/api';
import type { TestResult } from '../types';
import { FileText, CheckCircle, XCircle } from 'lucide-react';
import logoImage from '../assets/51talk-logo.png';

export default function FeedbackPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const resultId = searchParams.get('id');

    const [result, setResult] = useState<TestResult | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (resultId) {
            loadResult(parseInt(resultId));
        }
    }, [resultId]);

    const loadResult = async (id: number) => {
        try {
            const data = await getResultById(id);
            setResult(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
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
                        <p className="text-gray-600">加载中...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!result) {
        return (
            <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
                <div className="absolute inset-0 bg-[#00B4EE]">
                    <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                </div>
                <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-8 text-center max-w-md">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">未找到报告</h2>
                        <button 
                            onClick={() => navigate('/')} 
                            className="w-full py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all"
                        >
                            返回首页
                        </button>
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
            <div className="relative z-10 p-4 pb-6">
                <div className="max-w-md mx-auto">
                    {/* Header */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="flex items-center gap-2 flex-1">
                                <FileText className="w-6 h-6 text-[#00B4EE]" />
                                <h1 className="text-lg font-semibold text-gray-900">详细评估反馈</h1>
                            </div>
                            <img 
                                src={logoImage} 
                                alt="51Talk Logo" 
                                className="h-8 rounded-lg"
                            />
                        </div>
                    </div>

                    {/* Part Feedbacks */}
                    {result.part_scores.map((part) => (
                        <div key={part.part_number} className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                            <h2 className="text-[#00B4EE] font-semibold mb-3">
                                Part {part.part_number} 反馈:
                            </h2>
                            <div className="text-sm text-gray-700 mb-4">
                                <p>{part.feedback || '暂无详细反馈'}</p>
                            </div>

                            {part.correct_items && part.correct_items.length > 0 && (
                                <div className="flex items-start gap-2 mb-2">
                                    <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <p className="text-sm">
                                            <span className="text-green-700 font-medium">正确词汇:</span>
                                            <span className="text-gray-600"> {part.correct_items.join(', ')}</span>
                                        </p>
                                    </div>
                                </div>
                            )}
                            
                            {part.incorrect_items && part.incorrect_items.length > 0 && (
                                <div className="flex items-start gap-2">
                                    <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <p className="text-sm">
                                            <span className="text-red-700 font-medium">
                                                {part.part_number === 2 ? '重读错误' : '需要改进'}:
                                            </span>
                                            <span className="text-gray-600"> {part.incorrect_items.join(', ')}</span>
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Action Buttons */}
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            onClick={() => navigate(`/result?id=${result.id}`)}
                            className="py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <span className="text-sm">上一页</span>
                        </button>
                        <button
                            onClick={() => navigate(`/report/suggestion?id=${result.id}`)}
                            className="py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <span className="text-sm">进入下一页</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}


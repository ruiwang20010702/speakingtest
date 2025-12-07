/**
 * 详细口语测试报告页面 - 51Talk 新设计
 * 包含详细评估反馈和学习建议
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getResultById } from '../services/api';
import type { TestResult } from '../types';
import { FileText, CheckCircle, XCircle, Lightbulb, BookOpen, Home, ArrowLeft, Printer } from 'lucide-react';
import logoImage from '../assets/51talk-logo.png';

export default function DetailedReportPage() {
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

    // 生成学习建议
    const generateSuggestions = () => {
        if (!result) return [];
        
        const suggestions = [];
        const part1 = result.part_scores.find(p => p.part_number === 1);
        const part2 = result.part_scores.find(p => p.part_number === 2);
        const part3 = result.part_scores.find(p => p.part_number === 3);

        if ((part1?.score || 0) < 16) {
            suggestions.push('建议加强词汇发音练习，特别注意元音和辅音的准确性');
        }
        if ((part2?.score || 0) < 12) {
            suggestions.push('建议加强自然拼读专项练习，巩固phonics规则，提高单词拼读的准确性');
        }
        if ((part3?.score || 0) < 20) {
            suggestions.push('建议每天坚持朗读练习，提高整句输出的连贯性和流畅度');
        }

        suggestions.push('建议定期进行单元复习课，强化知识点，确保学习内容的系统性和连贯性');
        suggestions.push('建议多进行口语表达练习，增强自信心，可以通过角色扮演、情景对话等形式提升口语能力');

        return suggestions.slice(0, 5);
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

    const suggestions = generateSuggestions();

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
                            <button
                                onClick={() => navigate(-1)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <ArrowLeft className="w-5 h-5 text-gray-700" />
                            </button>
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
                        <p className="text-gray-600 text-sm pl-11">
                            {result.student_name} | {result.level} - {result.unit}
                        </p>
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
                                            <span className="text-green-700 font-medium">正确项目:</span>
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
                                            <span className="text-red-700 font-medium">需要改进:</span>
                                            <span className="text-gray-600"> {part.incorrect_items.join(', ')}</span>
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Score indicator */}
                            <div className="mt-3 pt-3 border-t border-gray-100">
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-500 text-sm">得分</span>
                                    <span className="text-[#00B4EE] font-semibold">
                                        {part.score} / {part.max_score}
                                    </span>
                                </div>
                                <div className="mt-1 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                    <div 
                                        className="bg-[#FDE700] h-full rounded-full transition-all"
                                        style={{ width: `${(part.score / part.max_score) * 100}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Learning Suggestions */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Lightbulb className="w-6 h-6 text-[#FDE700]" />
                            <h2 className="text-lg font-semibold text-gray-900">学习建议</h2>
                </div>

                        <div className="space-y-3">
                            {suggestions.map((suggestion, index) => (
                                <div key={index} className="flex items-start gap-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-[#FDE700] text-gray-900 rounded-full flex items-center justify-center text-sm font-semibold">
                                        {index + 1}
                                    </div>
                                    <div className="flex-1 pt-1">
                                        <p className="text-gray-700 text-sm">{suggestion}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Additional Tips */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                        <div className="flex items-center gap-2 mb-3">
                            <BookOpen className="w-6 h-6 text-[#00B4EE]" />
                            <h2 className="text-lg font-semibold text-gray-900">温馨提示</h2>
                        </div>
                        <div className="space-y-2 text-sm text-gray-700">
                            <p>• 建议每天坚持学习20-30分钟，保持学习的连续性</p>
                            <p>• 课前预习和课后复习同样重要，能够提高学习效率</p>
                            <p>• 遇到困难不要气馁，多与老师和同学交流</p>
                            <p>• 保持积极的学习态度，相信自己一定能够进步</p>
                        </div>
                </div>

                    {/* API Cost Section */}
                {(result.total_tokens || result.api_cost) && (
                        <div className="bg-gradient-to-r from-[#FDE700] to-[#FFD700] rounded-2xl shadow-lg p-4 mb-4">
                            <h3 className="text-gray-900 font-semibold mb-3 flex items-center gap-2">
                                <span className="text-xl">💰</span>
                                API 成本统计
                            </h3>
                            <div className="bg-white/90 rounded-xl p-3 space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Token 使用量:</span>
                                    <span className="font-medium">{result.total_tokens?.toLocaleString() || 0} tokens</span>
                            </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">API 成本:</span>
                                    <span className="font-medium">
                                    ${result.api_cost?.toFixed(4) || '0.0000'} USD
                                </span>
                            </div>
                                <p className="text-gray-500 text-xs mt-2">
                                    💡 本次测试使用 Gemini 2.5 Flash 模型进行AI评分，成本极低
                                </p>
                            </div>
                        </div>
                )}

                    {/* Action Buttons */}
                    <div className="grid grid-cols-3 gap-3">
                        <button
                            onClick={() => navigate('/')}
                            className="py-3 bg-white text-gray-700 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <Home className="w-4 h-4" />
                            <span className="text-sm">首页</span>
                    </button>
                        <button
                            onClick={() => window.print()}
                            className="py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <Printer className="w-4 h-4" />
                            <span className="text-sm">打印</span>
                    </button>
                        <button
                            onClick={() => navigate(`/result?id=${result.id}`)}
                            className="py-3 bg-white text-[#00B4EE] font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <FileText className="w-4 h-4" />
                            <span className="text-sm">总览</span>
                    </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

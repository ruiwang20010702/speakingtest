/**
 * 学习建议页面 - 报告第3页
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getResultById } from '../services/api';
import type { TestResult } from '../types';
import { Lightbulb, BookOpen } from 'lucide-react';

export default function SuggestionPage() {
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
        // Part 1: 词汇朗读, Part 2: 问答
        const part1 = result.part_scores.find(p => p.part_number === 1);
        const part2 = result.part_scores.find(p => p.part_number === 2);

        if ((part1?.score || 0) < 16) {
            suggestions.push('建议加强词汇发音练习，特别注意元音和辅音的准确性');
        }
        if ((part2?.score || 0) < 20) {
            suggestions.push('建议每天坚持朗读练习，提高整句输出的连贯性和流畅度');
        }

        suggestions.push('建议定期进行单元复习课，强化知识点，确保学习内容的系统性和连贯性');
        suggestions.push('建议针对发音薄弱环节进行专项训练，特别注意元音和辅音的区分，以及单词的轻重音');
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

                    {/* Action Buttons */}
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            onClick={() => navigate(`/report/feedback?id=${result.id}`)}
                            className="py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <span className="text-sm">上一页</span>
                        </button>
                        <button
                            onClick={() => navigate('/')}
                            className="py-3 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <span className="text-sm">返回首页</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}


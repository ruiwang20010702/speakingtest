/**
 * 结果页面 - 51Talk 新设计
 * 显示测试评分结果和雷达图
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getHistory } from '../services/api';
import type { TestResult } from '../types';
import { Award, TrendingUp } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import logoImage from '../assets/51talk-logo.png';

export default function ResultPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const resultId = searchParams.get('id');

    const [result, setResult] = useState<TestResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedSubject, setSelectedSubject] = useState<string>('');
    const [animatedScores, setAnimatedScores] = useState<number[]>([]);

    useEffect(() => {
        loadResult();
    }, [resultId]);

    // 动画进度条
    useEffect(() => {
        if (result) {
            const radarData = getRadarData();
            const duration = 1000;
            const steps = 60;
            const interval = duration / steps;
            let currentStep = 0;

            const timer = setInterval(() => {
                currentStep++;
                const progress = currentStep / steps;

                setAnimatedScores(radarData.map((item) =>
                    Math.floor(item.score * progress)
                ));

                if (currentStep >= steps) {
                    clearInterval(timer);
                    setAnimatedScores(radarData.map((item) => item.score));
                }
            }, interval);

            return () => clearInterval(timer);
        }
    }, [result]);

    const loadResult = async () => {
        if (!resultId) {
            setError('缺少测试结果ID');
            setLoading(false);
            return;
        }

        try {
            const results = await getHistory('');
            const foundResult = results.find(r => r.id === parseInt(resultId));

            if (foundResult) {
                setResult(foundResult);
            } else {
                setError('未找到测试结果');
            }
        } catch (err) {
            setError('加载结果失败');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // 根据分数生成简短评价
    const getShortEvaluation = (score: number) => {
        if (score >= 90) return '优秀 - 继续保持';
        if (score >= 80) return '良好 - 可以继续练习';
        if (score >= 70) return '中等 - 需要加强练习';
        if (score >= 60) return '待提升 - 建议多加练习';
        return '需努力 - 加油练习';
    };

    const getRadarData = () => {
        if (!result) return [];

        // 从 part_scores 中计算各项得分百分比
        const part1Score = result.part_scores.find(p => p.part_number === 1);
        const part2Score = result.part_scores.find(p => p.part_number === 2);
        const part3Score = result.part_scores.find(p => p.part_number === 3);

        const vocabScore = part1Score ? Math.round((part1Score.score / part1Score.max_score) * 100) : 0;
        const phonicsScore = part2Score ? Math.round((part2Score.score / part2Score.max_score) * 100) : 0;
        const sentenceScore = part3Score ? Math.round((part3Score.score / part3Score.max_score) * 100) : 0;
        const fluencyScore = result.fluency_score ? Math.round(result.fluency_score * 10) : 70;
        const pronunciationScore = result.pronunciation_score ? Math.round(result.pronunciation_score * 10) : 75;
        const confidenceScore = result.confidence_score ? Math.round(result.confidence_score * 10) : 80;

        return [
            {
                subject: '词汇',
                score: vocabScore,
                fullMark: 100,
                evaluation: getShortEvaluation(vocabScore)
            },
            {
                subject: '自然拼读',
                score: phonicsScore,
                fullMark: 100,
                evaluation: getShortEvaluation(phonicsScore)
            },
            {
                subject: '整句输出',
                score: sentenceScore,
                fullMark: 100,
                evaluation: getShortEvaluation(sentenceScore)
            },
            {
                subject: '流畅度',
                score: fluencyScore,
                fullMark: 100,
                evaluation: getShortEvaluation(fluencyScore)
            },
            {
                subject: '发音',
                score: pronunciationScore,
                fullMark: 100,
                evaluation: getShortEvaluation(pronunciationScore)
            },
            {
                subject: '自信度',
                score: confidenceScore,
                fullMark: 100,
                evaluation: getShortEvaluation(confidenceScore)
            },
        ];
    };

    const radarData = getRadarData();

    // 自定义雷达图标签
    const CustomTick = ({ payload, x, y, cx, cy }: any) => {
        const isSelected = selectedSubject === payload.value;
        const angle = Math.atan2(y - cy, x - cx);
        let offset = 35;
        if (payload.value === '词汇' || payload.value === '流畅度') {
            offset = 18;
        }
        const labelX = x + Math.cos(angle) * offset;
        const labelY = y + Math.sin(angle) * offset;

        const width = isSelected ? 72 : 60;
        const height = isSelected ? 24 : 20;
        const fontSize = isSelected ? 14 : 12;

        return (
            <g>
                <rect
                    x={labelX - width / 2}
                    y={labelY - height / 2}
                    width={width}
                    height={height}
                    rx={4}
                    fill={isSelected ? '#00B4EE' : 'white'}
                    stroke="#00B4EE"
                    strokeWidth={1}
                    style={{ cursor: 'pointer', transition: 'all 0.2s ease-in-out' }}
                    onClick={() => setSelectedSubject(isSelected ? '' : payload.value)}
                />
                <text
                    x={labelX}
                    y={labelY + (isSelected ? 5 : 4)}
                    textAnchor="middle"
                    fill="black"
                    fontSize={fontSize}
                    style={{ cursor: 'pointer', transition: 'all 0.2s ease-in-out', fontWeight: isSelected ? '600' : '400' }}
                    onClick={() => setSelectedSubject(isSelected ? '' : payload.value)}
                >
                    {payload.value}
                </text>
            </g>
        );
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
                        <p className="text-gray-600">正在加载结果...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !result) {
        return (
            <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
                <div className="absolute inset-0 bg-[#00B4EE]">
                    <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                </div>
                <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-8 text-center max-w-md">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">❌ {error || '加载失败'}</h2>
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
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <Award className="w-8 h-8 text-[#FDE700]" />
                                <h1 className="text-xl font-semibold text-gray-900">口语测试报告</h1>
                            </div>
                            <img
                                src={logoImage}
                                alt="51Talk Logo"
                                className="h-10 rounded-lg"
                            />
                        </div>
                        <p className="text-gray-600 text-sm">学生: {result.student_name}</p>
                        <p className="text-gray-600 text-sm">{result.level} - {result.unit}</p>
                        <p className="text-gray-500 text-xs mt-1">
                            {new Date(result.created_at).toLocaleDateString('zh-CN', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            })}
                        </p>
                    </div>


                    {/* Radar Chart */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-[#00B4EE]" />
                            能力雷达图
                        </h2>
                        <div onClick={(e) => {
                            const target = e.target as HTMLElement;
                            const text = target.textContent;
                            if (text && radarData.some(item => item.subject === text)) {
                                setSelectedSubject(selectedSubject === text ? '' : text);
                            }
                        }}>
                            <ResponsiveContainer width="100%" height={280}>
                                <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                                    <PolarGrid stroke="#00B4EE" strokeWidth={1} />
                                    <PolarAngleAxis
                                        dataKey="subject"
                                        tick={CustomTick}
                                    />
                                    <PolarRadiusAxis
                                        angle={90}
                                        domain={[0, 100]}
                                        tick={false}
                                        tickCount={6}
                                    />
                                    <Radar
                                        name="得分"
                                        dataKey="score"
                                        stroke="#00B4EE"
                                        fill="#00B4EE"
                                        fillOpacity={0.5}
                                        strokeWidth={2}
                                    />
                                </RadarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Evaluation bubble */}
                        {selectedSubject && (
                            <div className="mt-3 bg-white border-l-4 border-[#00B4EE] rounded-lg p-3 shadow-sm animate-in">
                                <p className="text-sm text-gray-700">
                                    <span className="font-medium text-gray-900">{selectedSubject}：</span>
                                    {radarData.find(item => item.subject === selectedSubject)?.evaluation}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Comprehensive Assessment */}
                    <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg p-4 mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">综合评价</h2>
                        <div className="space-y-3">
                            {radarData.map((item, index) => (
                                <div key={index} className="flex items-center gap-3">
                                    <div className="flex-shrink-0 w-20">
                                        <span className="text-gray-700 text-sm">{item.subject}</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                                                <div
                                                    className="bg-[#FDE700] h-full rounded-full transition-all"
                                                    style={{ width: `${animatedScores[index] || 0}%` }}
                                                />
                                            </div>
                                            <span className="text-sm font-medium text-[#00B4EE] w-10 text-right">
                                                {animatedScores[index] || 0}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-4 p-3 bg-[#00B4EE]/10 rounded-xl">
                            <p className="text-sm text-gray-700">
                                该学生在本次口语测试中表现{result.star_rating >= 4 ? '优秀' : result.star_rating >= 3 ? '良好' : '有待提升'}。
                                {result.star_rating >= 4 && '流畅度和发音能力突出。'}
                                建议继续加强{result.star_rating < 4 ? '整句输出和' : ''}自信度的训练，保持良好的学习状态。
                            </p>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-6">
                        <button
                            onClick={() => navigate(`/report/feedback?id=${result.id}`)}
                            className="w-full py-4 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all flex items-center justify-center gap-2 shadow-md"
                        >
                            <span className="text-lg">进入下一页</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

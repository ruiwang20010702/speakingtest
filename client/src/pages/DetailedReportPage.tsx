/**
 * 详细口语测试报告页面
 * 51Talk 风格报告，包含雷达图、详细评估和学习建议
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getResultById } from '../services/api';
import RadarChart from '../components/RadarChart';
import type { TestResult } from '../types';
import './DetailedReportPage.css';

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

    if (loading || !result) {
        return <div className="detailed-report-page loading">加载中...</div>;
    }

    // 从测试结果计算6维度数据
    const part1 = result.part_scores.find(p => p.part_number === 1);
    const part2 = result.part_scores.find(p => p.part_number === 2);
    const part3 = result.part_scores.find(p => p.part_number === 3);

    const radarData = {
        vocabulary: part1?.score || 0,
        phonics: part2?.score || 0,
        sentences: part3?.score || 0,
        // 使用 Gemini AI 评估的真实分数（如果没有则使用计算值）
        fluency: result.fluency_score || Math.min(10, Math.round((result.total_score / 60) * 10)),
        pronunciation: result.pronunciation_score || Math.min(10, Math.round(((part1?.score || 0) / 20) * 10)),
        confidence: result.confidence_score || Math.min(10, Math.round(((part3?.score || 0) / 24) * 10))
    };

    // 生成学习建议
    const generateSuggestions = () => {
        const suggestions = [];

        if ((part1?.score || 0) < 16) {
            suggestions.push('重点练习词汇发音，特别注意元音和辅音的准确性');
        }
        if ((part2?.score || 0) < 12) {
            suggestions.push('加强自然拼读训练，多做拼读练习');
        }
        if ((part3?.score || 0) < 20) {
            suggestions.push('提高整句输出能力，多进行对话练习');
        }

        if (suggestions.length === 0) {
            suggestions.push('继续保持良好的学习状态');
            suggestions.push('可以挑战更高难度的内容');
            suggestions.push('多进行实际对话练习');
        }

        return suggestions;
    };

    const suggestions = generateSuggestions();

    // 能力评估
    const getSkillLevel = (score: number, max: number) => {
        const percentage = (score / max) * 100;
        if (percentage >= 90) return '优秀 - 可以自行练习';
        if (percentage >= 75) return '良好 - 可以自行练习';
        if (percentage >= 60) return '及格 - 需要指导';
        return '需要加强';
    };

    return (
        <div className="detailed-report-page">
            <div className="report-container">
                {/* 报告头部 */}
                <div className="report-header">
                    <div className="logo-section">
                        <img src="/assets/51talk-logo.png" alt="51Talk" className="brand-logo" />
                        <h1>口语测试报告</h1>
                        <img src="/assets/monkey-avatar.png" alt="小猴" className="monkey-avatar" />
                    </div>
                    <div className="student-info">
                        <div className="info-row">
                            <span className="label">学生名:</span>
                            <span className="value">{result.student_name}</span>
                        </div>
                        <div className="info-row">
                            <span className="label">在读等级:</span>
                            <span className="value level-badge">{result.level.toUpperCase()} - {result.unit}</span>
                        </div>
                        <div className="info-row">
                            <span className="label">测试日期:</span>
                            <span className="value">
                                {new Date(result.created_at).toLocaleDateString('zh-CN')}
                            </span>
                        </div>
                    </div>
                </div>

                {/* 雷达图和能力评级 */}
                <div className="assessment-section">
                    <div className="radar-section">
                        <h3>能力雷达图</h3>
                        <RadarChart data={radarData} />
                    </div>

                    <div className="skills-evaluation">
                        <h3>Level {result.level === 'level1' ? '1' : result.level} 等级需要具备的能力</h3>
                        <div className="skills-table">
                            <div className="skill-row">
                                <span className="skill-name">词汇:</span>
                                <span className="skill-level">{getSkillLevel(part1?.score || 0, 20)}</span>
                            </div>
                            <div className="skill-row">
                                <span className="skill-name">自然拼读:</span>
                                <span className="skill-level">{getSkillLevel(part2?.score || 0, 16)}</span>
                            </div>
                            <div className="skill-row">
                                <span className="skill-name">整句输出:</span>
                                <span className="skill-level">{getSkillLevel(part3?.score || 0, 24)}</span>
                            </div>
                            <div className="skill-row">
                                <span className="skill-name">流畅度:</span>
                                <span className="skill-level">{getSkillLevel(radarData.fluency, 10)}</span>
                            </div>
                            <div className="skill-row">
                                <span className="skill-name">发音:</span>
                                <span className="skill-level">{getSkillLevel(radarData.pronunciation, 10)}</span>
                            </div>
                            <div className="skill-row">
                                <span className="skill-name">自信度:</span>
                                <span className="skill-level">{getSkillLevel(radarData.confidence, 10)}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 学习建议 */}
                <div className="suggestions-section">
                    <h3>🎯 学习建议</h3>
                    {suggestions.map((suggestion, index) => (
                        <div key={index} className="suggestion-item">
                            <span className="suggestion-number">学习建议 {index + 1}:</span>
                            <span className="suggestion-text">{suggestion}</span>
                        </div>
                    ))}
                </div>

                {/* 详细反馈 */}
                <div className="feedback-section">
                    <h3>📋 详细评估反馈</h3>
                    {result.part_scores.map(part => (
                        <div key={part.part_number} className="feedback-item">
                            <h4>Part {part.part_number} 反馈:</h4>
                            <p>{part.feedback}</p>
                            {part.correct_items.length > 0 && (
                                <div className="items-list">
                                    <strong>✅ 正确项目:</strong> {part.correct_items.join(', ')}
                                </div>
                            )}
                            {part.incorrect_items.length > 0 && (
                                <div className="items-list error">
                                    <strong>❌ 需要改进:</strong> {part.incorrect_items.join(', ')}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* 分数详情 */}
                <div className="score-details">
                    <h3>📊 分数详情</h3>
                    <table className="score-table">
                        <thead>
                            <tr>
                                <th>类别</th>
                                <th>分数</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>词汇</td>
                                <td>{part1?.score || 0}</td>
                            </tr>
                            <tr>
                                <td>自然拼读</td>
                                <td>{part2?.score || 0}</td>
                            </tr>
                            <tr>
                                <td>整句输出</td>
                                <td>{part3?.score || 0}</td>
                            </tr>
                            <tr>
                                <td>流畅度</td>
                                <td>{radarData.fluency}</td>
                            </tr>
                            <tr>
                                <td>发音</td>
                                <td>{radarData.pronunciation}</td>
                            </tr>
                            <tr>
                                <td>自信度</td>
                                <td>{radarData.confidence}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                {/* API成本统计 */}
                {(result.total_tokens || result.api_cost) && (
                    <div className="cost-section">
                        <h3>💰 API 成本统计</h3>
                        <div className="cost-grid">
                            <div className="cost-item">
                                <span className="cost-label">Token 使用量:</span>
                                <span className="cost-value">{result.total_tokens?.toLocaleString() || 0} tokens</span>
                            </div>
                            <div className="cost-item">
                                <span className="cost-label">API 成本:</span>
                                <span className="cost-value">
                                    ${result.api_cost?.toFixed(4) || '0.0000'} USD
                                    {result.api_cost && result.api_cost < 0.01 && (
                                        <span className="cost-note"> (约 ¥{(result.api_cost * 7.2).toFixed(3)})</span>
                                    )}
                                </span>
                            </div>
                            <div className="cost-item full-width">
                                <span className="cost-label">💡 提示:</span>
                                <span className="cost-description">
                                    本次测试使用了Gemini 2.5 Flash模型进行AI评分，成本极低。
                                    Token使用量包括了音频处理和文本生成。
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* 其他建议 */}
                <div className="other-suggestions">
                    <h3>💡 其他建议</h3>
                    <p>
                        根据本次测试结果，建议学生在日常学习中注重英语口语的练习，提高英语口语能力。
                        建议家长鼓励学生多开口说英语，每日坚持15-20分钟的口语练习，未来的你一定会感谢现在的自己。
                    </p>
                    {result.star_rating >= 4 && (
                        <p className="highlight">
                            ✨ 本次测试表现优秀！从此步入卓越模式，并扎实有所提升的阶阶续续培养习惯，左上方的阙值诀窍会提供最佳学习建议！
                        </p>
                    )}
                </div>

                {/* 操作按钮 */}
                <div className="report-actions">
                    <button onClick={() => window.print()} className="btn btn-primary">
                        🖨️ 打印报告
                    </button>
                    <button onClick={() => navigate('/history')} className="btn btn-secondary">
                        📚 返回记录
                    </button>
                    <button onClick={() => navigate('/')} className="btn btn-secondary">
                        🏠 返回首页
                    </button>
                </div>
            </div>
        </div>
    );
}

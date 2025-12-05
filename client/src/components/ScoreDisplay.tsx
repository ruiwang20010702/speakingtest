/**
 * 结果展示组件
 * 显示星级评分和详细分数
 */
import type { TestResult } from '../types';
import './ScoreDisplay.css';

interface ScoreDisplayProps {
    result: TestResult;
}

export default function ScoreDisplay({ result }: ScoreDisplayProps) {
    const renderStars = (rating: number) => {
        return (
            <div className="stars">
                {[1, 2, 3, 4, 5].map(star => (
                    <span key={star} className={star <= rating ? 'star' : 'star empty'}>
                        ⭐
                    </span>
                ))}
            </div>
        );
    };

    const getScoreColor = (score: number, maxScore: number) => {
        const percentage = (score / maxScore) * 100;
        if (percentage >= 90) return '#10b981'; // 绿色
        if (percentage >= 70) return '#3b82f6'; // 蓝色
        if (percentage >= 50) return '#f59e0b'; // 橙色
        return '#ef4444'; // 红色
    };

    return (
        <div className="score-display">
            {/* 总分和星级 */}
            <div className="total-score-section">
                <div className="score-circle">
                    <svg viewBox="0 0 200 200" className="progress-ring">
                        <circle
                            cx="100"
                            cy="100"
                            r="90"
                            fill="none"
                            stroke="#e5e7eb"
                            strokeWidth="12"
                        />
                        <circle
                            cx="100"
                            cy="100"
                            r="90"
                            fill="none"
                            stroke="#6366f1"
                            strokeWidth="12"
                            strokeDasharray={`${(result.total_score / 60) * 565} 565`}
                            strokeDashoffset="0"
                            transform="rotate(-90 100 100)"
                            className="progress-circle"
                        />
                    </svg>
                    <div className="score-text">
                        <div className="score-number">{result.total_score}</div>
                        <div className="score-max">/60</div>
                    </div>
                </div>

                <div className="rating-section">
                    {renderStars(result.star_rating)}
                    <p className="rating-text">
                        {result.star_rating === 5 && '杰出！发音准确，表达流畅'}
                        {result.star_rating === 4 && '优秀！发音良好，偶有小错'}
                        {result.star_rating === 3 && '良好！基本正确，需改进'}
                        {result.star_rating === 2 && '中等！需要更多练习'}
                        {result.star_rating === 1 && '需努力！加油练习'}
                    </p>
                </div>
            </div>

            {/* 分项得分 */}
            <div className="part-scores">
                {result.part_scores.map(partScore => (
                    <div key={partScore.part_number} className="part-score-card">
                        <h3>Part {partScore.part_number}</h3>
                        <div className="part-score-bar">
                            <div
                                className="part-score-fill"
                                style={{
                                    width: `${(partScore.score / partScore.max_score) * 100}%`,
                                    background: getScoreColor(partScore.score, partScore.max_score)
                                }}
                            />
                        </div>
                        <div className="part-score-text">
                            {partScore.score} / {partScore.max_score}
                        </div>

                        {partScore.feedback && (
                            <div className="feedback">
                                <p><strong>反馈：</strong></p>
                                <p>{partScore.feedback}</p>
                            </div>
                        )}

                        {partScore.correct_items?.length > 0 && (
                            <div className="items-list correct">
                                <p><strong>✓ 正确项目：</strong></p>
                                <div className="items">{partScore.correct_items.join(', ')}</div>
                            </div>
                        )}

                        {partScore.incorrect_items?.length > 0 && (
                            <div className="items-list incorrect">
                                <p><strong>✗ 需要改进：</strong></p>
                                <div className="items">{partScore.incorrect_items.join(', ')}</div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

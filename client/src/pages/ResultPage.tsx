/**
 * 结果页面
 * 显示测试评分结果
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getHistory } from '../services/api';
import ScoreDisplay from '../components/ScoreDisplay';
import type { TestResult } from '../types';
import './ResultPage.css';

export default function ResultPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const resultId = searchParams.get('id');

    const [result, setResult] = useState<TestResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadResult();
    }, [resultId]);

    const loadResult = async () => {
        if (!resultId) {
            setError('缺少测试结果ID');
            setLoading(false);
            return;
        }

        try {
            // 由于我们没有单独的获取单个结果的API，我们使用历史记录API
            // 然后找到对应的结果
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

    if (loading) {
        return (
            <div className="result-page">
                <div className="container">
                    <div className="card">
                        <div className="loading-container">
                            <span className="loading"></span>
                            <p>正在加载结果...</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !result) {
        return (
            <div className="result-page">
                <div className="container">
                    <div className="card">
                        <h2>❌ {error || '加载失败'}</h2>
                        <button onClick={() => navigate('/')} className="btn btn-primary">
                            返回首页
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="result-page">
            <div className="container">
                <div className="result-header">
                    <h1>🎉 测试完成！</h1>
                    <p className="result-info">
                        {result.student_name} | {result.level} {result.unit} |
                        {new Date(result.created_at).toLocaleDateString('zh-CN')}
                    </p>
                </div>

                <div className="card result-card">
                    <ScoreDisplay result={result} />

                    <div className="action-buttons">
                        <button
                            onClick={() => navigate(`/detailed-report?id=${result.id}`)}
                            className="btn btn-primary"
                        >
                            📊 查看详细报告
                        </button>
                        <button
                            onClick={() => navigate('/')}
                            className="btn btn-secondary"
                        >
                            重新测试
                        </button>
                        <button
                            onClick={() => navigate(`/history?student=${encodeURIComponent(result.student_name)}`)}
                            className="btn btn-secondary"
                        >
                            查看历史记录
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

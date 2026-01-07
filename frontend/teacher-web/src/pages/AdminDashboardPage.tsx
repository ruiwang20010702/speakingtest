import { useState, useEffect } from 'react';
import { adminApi, type OverviewStats, type FunnelStats, type CostStats } from '../api';
import { useAuthStore } from '../stores/authStore';
import './AdminDashboardPage.css';

export default function AdminDashboardPage() {
    const { teacherName } = useAuthStore();
    const [overview, setOverview] = useState<OverviewStats | null>(null);
    const [funnel, setFunnel] = useState<FunnelStats | null>(null);
    const [cost, setCost] = useState<CostStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [overviewRes, funnelRes, costRes] = await Promise.all([
                adminApi.getOverview(),
                adminApi.getFunnel(),
                adminApi.getCost()
            ]);
            setOverview(overviewRes.data);
            setFunnel(funnelRes.data);
            setCost(costRes.data);
        } catch (err) {
            console.error(err);
            setError('加载数据失败');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="loading">加载中...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
        <div className="admin-dashboard">
            <header className="page-header">
                <div className="header-left">
                    <button className="btn-back" onClick={() => window.history.back()} style={{ marginRight: '10px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>
                        ←
                    </button>
                    <h1>运营看板</h1>
                    <span className="teacher-name">欢迎，{teacherName || '管理员'}</span>
                </div>
            </header>

            <div className="dashboard-content">
                {/* Overview Cards */}
                <section className="stats-section">
                    <h2>数据概览</h2>
                    <div className="stats-grid">
                        <div className="stat-card">
                            <span className="stat-label">学生总数</span>
                            <span className="stat-value">{overview?.total_students}</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-label">测评总数</span>
                            <span className="stat-value">{overview?.total_tests}</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-label">分享次数</span>
                            <span className="stat-value">{overview?.total_shares}</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-label">家长打开</span>
                            <span className="stat-value">{overview?.total_opens}</span>
                        </div>
                    </div>
                </section>

                {/* Funnel Chart (Simplified as Bars) */}
                <section className="stats-section">
                    <h2>转化漏斗</h2>
                    <div className="funnel-chart">
                        <div className="funnel-step">
                            <div className="funnel-bar" style={{ width: '100%' }}>
                                <span className="step-label">扫码进入</span>
                                <span className="step-value">{funnel?.scanned}</span>
                            </div>
                        </div>
                        <div className="funnel-step">
                            <div className="funnel-bar" style={{ width: `${funnel?.scanned ? (funnel.completed / funnel.scanned) * 100 : 0}%` }}>
                                <span className="step-label">完成测评</span>
                                <span className="step-value">{funnel?.completed}</span>
                            </div>
                            <span className="conversion-rate">
                                {funnel?.scanned ? ((funnel.completed / funnel.scanned) * 100).toFixed(1) : 0}%
                            </span>
                        </div>
                        <div className="funnel-step">
                            <div className="funnel-bar" style={{ width: `${funnel?.completed ? (funnel.shared / funnel.completed) * 100 : 0}%` }}>
                                <span className="step-label">老师分享</span>
                                <span className="step-value">{funnel?.shared}</span>
                            </div>
                            <span className="conversion-rate">
                                {funnel?.completed ? ((funnel.shared / funnel.completed) * 100).toFixed(1) : 0}%
                            </span>
                        </div>
                        <div className="funnel-step">
                            <div className="funnel-bar" style={{ width: `${funnel?.shared ? (funnel.opened / funnel.shared) * 100 : 0}%` }}>
                                <span className="step-label">家长打开</span>
                                <span className="step-value">{funnel?.opened}</span>
                            </div>
                            <span className="conversion-rate">
                                {funnel?.shared ? ((funnel.opened / funnel.shared) * 100).toFixed(1) : 0}%
                            </span>
                        </div>
                    </div>
                </section>

                {/* Cost Estimate */}
                <section className="stats-section">
                    <h2>成本估算</h2>
                    <div className="cost-card">
                        <div className="cost-row">
                            <span>总测评次数</span>
                            <span>{cost?.total_tests}</span>
                        </div>
                        <div className="cost-row highlight">
                            <span>预估 API 成本</span>
                            <span>¥ {cost?.estimated_cost_cny.toFixed(2)}</span>
                        </div>
                        <p className="cost-note">* 基于 Xunfei (Part 1) + Qwen (Part 2) 当前单价估算</p>
                    </div>
                </section>
            </div>
        </div>
    );
}

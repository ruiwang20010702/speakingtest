import { useState, useEffect } from 'react';
import { adminApi, type OverviewStats, type FunnelStats, type CostStats } from '../api';
import Layout from '../components/Layout';

export default function AdminDashboardPage() {
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

    if (loading) {
        return (
            <Layout title="运营看板" showBack>
                <div className="flex flex-col items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
                    <p className="text-gray-500">数据加载中...</p>
                </div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout title="运营看板" showBack>
                <div className="text-center py-10 text-red-500 bg-white rounded-xl shadow-sm border border-red-100">{error}</div>
            </Layout>
        );
    }

    return (
        <Layout title="运营看板" showBack>
            <div className="space-y-8">
                {/* Overview Cards */}
                <section>
                    <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <span className="bg-primary/10 w-8 h-8 rounded-lg flex items-center justify-center text-primary text-sm">📊</span>
                        数据概览
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                            <span className="text-gray-500 text-sm font-medium mb-2">学生总数</span>
                            <span className="text-4xl font-bold text-gray-900">{overview?.total_students || 0}</span>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                            <span className="text-gray-500 text-sm font-medium mb-2">测评总数</span>
                            <span className="text-4xl font-bold text-primary">{overview?.total_tests || 0}</span>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                            <span className="text-gray-500 text-sm font-medium mb-2">分享次数</span>
                            <span className="text-4xl font-bold text-blue-600">{overview?.total_shares || 0}</span>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                            <span className="text-gray-500 text-sm font-medium mb-2">家长打开</span>
                            <span className="text-4xl font-bold text-emerald-600">{overview?.total_opens || 0}</span>
                        </div>
                    </div>
                </section>

                <div className="grid lg:grid-cols-2 gap-8">
                    {/* Funnel Chart */}
                    <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm h-full">
                        <h2 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <span className="bg-orange-50 w-8 h-8 rounded-lg flex items-center justify-center text-orange-500 text-sm">📉</span>
                            转化漏斗
                        </h2>
                        
                        <div className="space-y-6">
                            {[
                                { label: '扫码进入', value: funnel?.scanned || 0, max: funnel?.scanned || 1, color: 'bg-primary' },
                                { label: '完成测评', value: funnel?.completed || 0, max: funnel?.scanned || 1, color: 'bg-blue-500' },
                                { label: '老师分享', value: funnel?.shared || 0, max: funnel?.completed || 1, color: 'bg-indigo-500' },
                                { label: '家长打开', value: funnel?.opened || 0, max: funnel?.shared || 1, color: 'bg-emerald-500' }
                            ].map((step, idx, arr) => {
                                const prevStep = idx > 0 ? arr[idx-1] : null;
                                const conversionRate = prevStep && prevStep.value > 0 
                                    ? ((step.value / prevStep.value) * 100).toFixed(1) 
                                    : '0.0';
                                const width = step.max > 0 ? (step.value / arr[0].value) * 100 : 0;

                                return (
                                    <div key={step.label} className="relative">
                                        <div className="flex justify-between text-sm font-medium mb-2">
                                            <span className="text-gray-700">{step.label}</span>
                                            <div className="flex items-center gap-3">
                                                {idx > 0 && (
                                                    <span className="text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
                                                        转化率 {conversionRate}%
                                                    </span>
                                                )}
                                                <span className="text-gray-900 font-bold">{step.value}</span>
                                            </div>
                                        </div>
                                        <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
                                            <div 
                                                className={`h-full rounded-full ${step.color} transition-all duration-1000 ease-out`}
                                                style={{ width: `${width}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* Cost Estimate */}
                    <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm h-full flex flex-col">
                        <h2 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <span className="bg-green-50 w-8 h-8 rounded-lg flex items-center justify-center text-green-600 text-sm">💰</span>
                            成本估算
                        </h2>
                        
                        <div className="flex-1 flex flex-col justify-center">
                            <div className="bg-gray-50 rounded-xl p-6 border border-gray-100 mb-4">
                                <div className="flex justify-between items-center mb-4 pb-4 border-b border-gray-200">
                                    <span className="text-gray-600">总测评次数</span>
                                    <span className="font-mono font-bold text-xl">{cost?.total_tests || 0}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-gray-900 font-bold">预估 API 成本</span>
                                    <span className="font-mono font-bold text-2xl text-red-600">
                                        ¥ {(cost?.estimated_cost_cny || 0).toFixed(2)}
                                    </span>
                                </div>
                            </div>
                            
                            <p className="text-xs text-gray-400 leading-relaxed bg-blue-50/50 p-4 rounded-lg">
                                * 成本估算基于当前 Xunfei (Part 1) + Qwen (Part 2) 的 API 单价。
                                <br/>
                                * 实际账单请以云厂商控制台为准。
                            </p>
                        </div>
                    </section>
                </div>
            </div>
        </Layout>
    );
}

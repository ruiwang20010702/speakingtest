import React, { useEffect, useState } from 'react';
import { Loader2, Users, FileText, Share2, Eye, DollarSign, TrendingUp, AlertTriangle, ArrowRight, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type OverviewStats, type FunnelStats, type CostStats } from '../../api';

export const AdminDashboardPage: React.FC = () => {
    const navigate = useNavigate();
    const [overview, setOverview] = useState<OverviewStats | null>(null);
    const [funnel, setFunnel] = useState<FunnelStats | null>(null);
    const [cost, setCost] = useState<CostStats | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadDashboardData();
    }, []);

    const loadDashboardData = async () => {
        setIsLoading(true);
        setError('');
        try {
            const [overviewRes, funnelRes, costRes] = await Promise.all([
                adminApi.getOverview(),
                adminApi.getFunnel(),
                adminApi.getCost(),
            ]);
            setOverview(overviewRes.data);
            setFunnel(funnelRes.data);
            setCost(costRes.data);
        } catch (err: any) {
            console.error('Failed to load dashboard data:', err);
            setError(err.response?.data?.detail || '加载数据失败');
        } finally {
            setIsLoading(false);
        }
    };

    // Calculate conversion rates
    const getConversionRate = (from: number, to: number) => {
        if (from === 0) return 0;
        return Math.round((to / from) * 100);
    };

    if (isLoading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-3 text-lg">加载中...</span>
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">管理员看板</h1>
                    <p className="text-text-sub mt-1">全局数据概览与监控</p>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">
                    {error}
                </div>
            )}

            {/* Overview Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4 mb-8">
                <div className="bg-surface rounded-xl p-5 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                            <Users size={24} className="text-blue-600" />
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-text-main">{overview?.total_students || 0}</p>
                            <p className="text-sm text-text-sub">学生总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-5 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center">
                            <FileText size={24} className="text-green-600" />
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-text-main">{overview?.total_tests || 0}</p>
                            <p className="text-sm text-text-sub">测评总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-5 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center">
                            <Share2 size={24} className="text-purple-600" />
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-text-main">{overview?.total_shares || 0}</p>
                            <p className="text-sm text-text-sub">分享次数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-5 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
                            <Eye size={24} className="text-amber-600" />
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-text-main">{overview?.total_opens || 0}</p>
                            <p className="text-sm text-text-sub">打开次数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-5 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-cyan-100 flex items-center justify-center">
                            <Clock size={24} className="text-cyan-600" />
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-text-main">{overview?.pending_followups || 0}</p>
                            <p className="text-sm text-text-sub">待跟进</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Funnel & Cost Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Conversion Funnel */}
                <div className="lg:col-span-2 bg-surface rounded-2xl p-6 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-lg font-semibold text-text-main flex items-center gap-2">
                            <TrendingUp size={20} className="text-primary" />
                            转化漏斗
                        </h2>
                    </div>
                    
                    {funnel && (
                        <div className="space-y-4">
                            {/* Funnel Steps */}
                            <div className="flex items-center gap-2">
                                {/* Step 1: Scanned */}
                                <div className="flex-1 bg-blue-50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-blue-700">{funnel.scanned}</p>
                                    <p className="text-sm text-blue-600">扫码进入</p>
                                </div>
                                <ArrowRight size={20} className="text-gray-300 shrink-0" />
                                
                                {/* Step 2: Completed */}
                                <div className="flex-1 bg-green-50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-green-700">{funnel.completed}</p>
                                    <p className="text-sm text-green-600">完成测评</p>
                                    <p className="text-xs text-green-500 mt-1">
                                        {getConversionRate(funnel.scanned, funnel.completed)}%
                                    </p>
                                </div>
                                <ArrowRight size={20} className="text-gray-300 shrink-0" />
                                
                                {/* Step 3: Shared */}
                                <div className="flex-1 bg-purple-50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-purple-700">{funnel.shared}</p>
                                    <p className="text-sm text-purple-600">老师分享</p>
                                    <p className="text-xs text-purple-500 mt-1">
                                        {getConversionRate(funnel.completed, funnel.shared)}%
                                    </p>
                                </div>
                                <ArrowRight size={20} className="text-gray-300 shrink-0" />
                                
                                {/* Step 4: Opened */}
                                <div className="flex-1 bg-amber-50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-amber-700">{funnel.opened}</p>
                                    <p className="text-sm text-amber-600">家长打开</p>
                                    <p className="text-xs text-amber-500 mt-1">
                                        {getConversionRate(funnel.shared, funnel.opened)}%
                                    </p>
                                </div>
                            </div>

                            {/* Overall Funnel Bar */}
                            <div className="mt-6">
                                <div className="flex items-center justify-between text-sm text-text-sub mb-2">
                                    <span>整体转化率</span>
                                    <span className="font-semibold text-primary">
                                        {getConversionRate(funnel.scanned, funnel.opened)}%
                                    </span>
                                </div>
                                <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-blue-500 via-green-500 to-amber-500 rounded-full transition-all duration-500"
                                        style={{ width: `${getConversionRate(funnel.scanned, funnel.opened)}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Cost Stats */}
                <div className="bg-surface rounded-2xl p-6 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-lg font-semibold text-text-main flex items-center gap-2">
                            <DollarSign size={20} className="text-green-600" />
                            成本统计
                        </h2>
                    </div>
                    
                    {cost && (
                        <div className="space-y-6">
                            <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl">
                                <p className="text-4xl font-bold text-green-700">
                                    ¥{cost.estimated_cost_cny.toFixed(2)}
                                </p>
                                <p className="text-sm text-green-600 mt-1">预估总成本</p>
                            </div>
                            
                            <div className="space-y-3">
                                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-text-sub">测评次数</span>
                                    <span className="font-semibold text-text-main">{cost.total_tests}</span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-text-sub">单次成本</span>
                                    <span className="font-semibold text-text-main">
                                        ¥{cost.total_tests > 0 ? (cost.estimated_cost_cny / cost.total_tests).toFixed(4) : '0.00'}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-text-sub">月度预估</span>
                                    <span className="font-semibold text-text-main">
                                        ¥{(cost.estimated_cost_cny * 4).toFixed(2)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <button
                    onClick={() => navigate('/admin/teachers')}
                    className="bg-surface rounded-xl p-4 border border-gray-100 shadow-sm hover:border-primary/30 hover:shadow-md transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                            <Users size={20} className="text-blue-600" />
                        </div>
                        <div>
                            <p className="font-semibold text-text-main">老师管理</p>
                            <p className="text-xs text-text-sub">查看老师列表</p>
                        </div>
                    </div>
                </button>
                <button
                    onClick={() => navigate('/admin/questions')}
                    className="bg-surface rounded-xl p-4 border border-gray-100 shadow-sm hover:border-primary/30 hover:shadow-md transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center group-hover:bg-green-200 transition-colors">
                            <FileText size={20} className="text-green-600" />
                        </div>
                        <div>
                            <p className="font-semibold text-text-main">题库管理</p>
                            <p className="text-xs text-text-sub">管理测评题目</p>
                        </div>
                    </div>
                </button>
                <button
                    onClick={() => navigate('/admin/audit-logs')}
                    className="bg-surface rounded-xl p-4 border border-gray-100 shadow-sm hover:border-primary/30 hover:shadow-md transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                            <FileText size={20} className="text-purple-600" />
                        </div>
                        <div>
                            <p className="font-semibold text-text-main">系统日志</p>
                            <p className="text-xs text-text-sub">查看操作记录</p>
                        </div>
                    </div>
                </button>
                <button
                    onClick={() => navigate('/admin/failed-tasks')}
                    className="bg-surface rounded-xl p-4 border border-gray-100 shadow-sm hover:border-primary/30 hover:shadow-md transition-all text-left group"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center group-hover:bg-red-200 transition-colors">
                            <AlertTriangle size={20} className="text-red-600" />
                        </div>
                        <div>
                            <p className="font-semibold text-text-main">失败任务</p>
                            <p className="text-xs text-text-sub">{overview?.failed_tasks || 0} 个待处理</p>
                        </div>
                    </div>
                </button>
            </div>
        </DashboardLayout>
    );
};

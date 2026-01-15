import React, { useEffect, useState } from 'react';
import { Loader2, RefreshCw, AlertTriangle, Clock, BookOpen, FileText } from 'lucide-react';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type FailedTaskItem } from '../../api';

export const FailedTasksPage: React.FC = () => {
    const [tasks, setTasks] = useState<FailedTaskItem[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [retryingId, setRetryingId] = useState<number | null>(null);
    const [regeneratingId, setRegeneratingId] = useState<number | null>(null);

    useEffect(() => {
        loadTasks();
    }, []);

    const loadTasks = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await adminApi.getFailedTasks();
            setTasks(response.data.items);
            setTotal(response.data.total);
        } catch (err: any) {
            console.error('Failed to load failed tasks:', err);
            setError(err.response?.data?.detail || '加载失败任务列表失败');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRetry = async (testId: number) => {
        setRetryingId(testId);
        try {
            const response = await adminApi.retryTask(testId);
            if (response.data.success) {
                // Remove from list or reload
                loadTasks();
            }
        } catch (err: any) {
            console.error('Failed to retry task:', err);
            alert(err.response?.data?.detail || '重试任务失败');
        } finally {
            setRetryingId(null);
        }
    };

    const handleRegenerate = async (testId: number) => {
        setRegeneratingId(testId);
        try {
            const response = await adminApi.regenerateReport(testId);
            if (response.data.success) {
                alert(`${response.data.message}`);
                loadTasks();
            }
        } catch (err: any) {
            console.error('Failed to regenerate report:', err);
            alert(err.response?.data?.detail || '重新生成报告失败');
        } finally {
            setRegeneratingId(null);
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getRetryCountColor = (count: number) => {
        if (count >= 3) return 'bg-red-100 text-red-700';
        if (count >= 2) return 'bg-orange-100 text-orange-700';
        if (count >= 1) return 'bg-yellow-100 text-yellow-700';
        return 'bg-gray-100 text-gray-700';
    };

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">失败任务</h1>
                    <p className="text-text-sub mt-1">查看和重试失败的测评任务</p>
                </div>
                <button
                    onClick={loadTasks}
                    disabled={isLoading}
                    className="px-4 py-2 bg-gray-100 text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                    <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
                    刷新
                </button>
            </div>

            {/* Summary Card */}
            <div className="bg-surface rounded-xl p-6 border border-gray-100 mb-8">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                        <AlertTriangle size={24} className="text-red-600" />
                    </div>
                    <div>
                        <p className="text-3xl font-bold text-text-main">{total}</p>
                        <p className="text-sm text-text-sub">失败任务总数</p>
                    </div>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">
                    {error}
                </div>
            )}

            {/* Tasks List */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            ) : tasks.length > 0 ? (
                <div className="space-y-4">
                    {tasks.map((task) => (
                        <div
                            key={task.test_id}
                            className="bg-surface rounded-2xl p-6 shadow-sm border border-gray-100 hover:border-red-200 transition-colors"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    {/* Header */}
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                                            <AlertTriangle size={20} className="text-red-600" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-text-main">
                                                测评 #{task.test_id}
                                            </h3>
                                            <p className="text-sm text-text-sub">
                                                {task.student_name || `学生 ID: ${task.student_id}`}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Details Grid */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                        <div className="flex items-center gap-2 text-sm">
                                            <BookOpen size={14} className="text-text-sub" />
                                            <span className="text-text-sub">Level/Unit:</span>
                                            <span className="font-medium text-text-main">{task.level} - {task.unit}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm">
                                            <Clock size={14} className="text-text-sub" />
                                            <span className="text-text-sub">创建时间:</span>
                                            <span className="font-medium text-text-main">{formatDate(task.created_at)}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm">
                                            <RefreshCw size={14} className="text-text-sub" />
                                            <span className="text-text-sub">重试次数:</span>
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getRetryCountColor(task.retry_count)}`}>
                                                {task.retry_count} / 3
                                            </span>
                                        </div>
                                        {task.updated_at && (
                                            <div className="flex items-center gap-2 text-sm">
                                                <Clock size={14} className="text-text-sub" />
                                                <span className="text-text-sub">更新时间:</span>
                                                <span className="font-medium text-text-main">{formatDate(task.updated_at)}</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Failure Reason */}
                                    {task.failure_reason && (
                                        <div className="bg-red-50 rounded-lg p-3 text-sm">
                                            <p className="text-red-700">
                                                <span className="font-medium">失败原因: </span>
                                                {task.failure_reason}
                                            </p>
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="ml-4 flex flex-col gap-2">
                                    <button
                                        onClick={() => handleRegenerate(task.test_id)}
                                        disabled={regeneratingId === task.test_id || task.retry_count >= 5}
                                        className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {regeneratingId === task.test_id ? (
                                            <>
                                                <Loader2 size={16} className="animate-spin" />
                                                生成中...
                                            </>
                                        ) : task.retry_count >= 5 ? (
                                            <>
                                                <AlertTriangle size={16} />
                                                已达上限
                                            </>
                                        ) : (
                                            <>
                                                <FileText size={16} />
                                                重新生成报告
                                            </>
                                        )}
                                    </button>
                                    <button
                                        onClick={() => handleRetry(task.test_id)}
                                        disabled={retryingId === task.test_id || task.retry_count >= 3}
                                        className="px-4 py-2 bg-gray-100 text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {retryingId === task.test_id ? (
                                            <>
                                                <Loader2 size={16} className="animate-spin" />
                                                重试中...
                                            </>
                                        ) : task.retry_count >= 3 ? (
                                            <>
                                                <AlertTriangle size={16} />
                                                重试上限
                                            </>
                                        ) : (
                                            <>
                                                <RefreshCw size={16} />
                                                仅重试 Part2
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-surface rounded-2xl p-12 text-center">
                    <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-text-main mb-2">没有失败任务</h3>
                    <p className="text-text-sub">所有测评任务运行正常</p>
                </div>
            )}
        </DashboardLayout>
    );
};

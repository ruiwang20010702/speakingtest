import React, { useEffect, useState } from 'react';
import { Loader2, ChevronLeft, ChevronRight, User, Clock, MapPin } from 'lucide-react';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type AuditLogItem } from '../../api';

// Action type labels
const ACTION_LABELS: Record<string, string> = {
    'CREATE_QUESTION': '创建题目',
    'UPDATE_QUESTION': '更新题目',
    'DELETE_QUESTION': '删除题目',
    'BATCH_CREATE_QUESTIONS': '批量创建题目',
    'GENERATE_TOKEN': '生成入口码',
    'VIEW_REPORT': '查看报告',
    'GENERATE_SHARE_LINK': '生成分享链接',
    'GENERATE_INTERPRETATION': '生成报告解读',
    'RETRY_TASK': '重试任务',
};

// Action type colors
const ACTION_COLORS: Record<string, string> = {
    'CREATE_QUESTION': 'bg-green-100 text-green-700',
    'UPDATE_QUESTION': 'bg-blue-100 text-blue-700',
    'DELETE_QUESTION': 'bg-red-100 text-red-700',
    'BATCH_CREATE_QUESTIONS': 'bg-green-100 text-green-700',
    'GENERATE_TOKEN': 'bg-purple-100 text-purple-700',
    'VIEW_REPORT': 'bg-gray-100 text-gray-700',
    'GENERATE_SHARE_LINK': 'bg-indigo-100 text-indigo-700',
    'GENERATE_INTERPRETATION': 'bg-amber-100 text-amber-700',
    'RETRY_TASK': 'bg-orange-100 text-orange-700',
};

export const AuditLogPage: React.FC = () => {
    const [logs, setLogs] = useState<AuditLogItem[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [limit] = useState(20);
    const [actionFilter, setActionFilter] = useState<string>('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadLogs();
    }, [page, actionFilter]);

    const loadLogs = async () => {
        setIsLoading(true);
        setError('');
        try {
            const params: { action?: string; page: number; limit: number } = { page, limit };
            if (actionFilter) {
                params.action = actionFilter;
            }
            const response = await adminApi.getAuditLogs(params);
            setLogs(response.data.items);
            setTotal(response.data.total);
        } catch (err: any) {
            console.error('Failed to load audit logs:', err);
            setError(err.response?.data?.detail || '加载审计日志失败');
        } finally {
            setIsLoading(false);
        }
    };

    const totalPages = Math.ceil(total / limit);

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    const getActionLabel = (action: string) => ACTION_LABELS[action] || action;
    const getActionColor = (action: string) => ACTION_COLORS[action] || 'bg-gray-100 text-gray-700';

    // Get unique actions for filter
    const uniqueActions = Object.keys(ACTION_LABELS);

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">系统日志</h1>
                    <p className="text-text-sub mt-1">查看关键操作审计日志</p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex gap-4 mb-6">
                <div className="flex-1 max-w-xs">
                    <label className="block text-sm font-medium text-text-sub mb-2">操作类型</label>
                    <select
                        value={actionFilter}
                        onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
                        className="input-field"
                    >
                        <option value="">全部操作</option>
                        {uniqueActions.map(action => (
                            <option key={action} value={action}>{ACTION_LABELS[action]}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">
                    {error}
                </div>
            )}

            {/* Logs Table */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            ) : (
                <>
                    <div className="bg-surface rounded-2xl shadow-sm overflow-hidden mb-6">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b border-gray-100">
                                <tr>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">时间</th>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">操作人</th>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">操作类型</th>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">目标</th>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">IP 地址</th>
                                    <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">详情</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {logs.length > 0 ? (
                                    logs.map((log) => (
                                        <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2 text-sm text-text-sub">
                                                    <Clock size={14} />
                                                    {formatDate(log.created_at)}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                                        <User size={14} className="text-primary" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-text-main">
                                                            {log.operator_email || `用户 ${log.operator_id}`}
                                                        </p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getActionColor(log.action)}`}>
                                                    {getActionLabel(log.action)}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                {log.target_type && log.target_id ? (
                                                    <span className="text-sm text-text-sub">
                                                        {log.target_type} #{log.target_id}
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-text-sub/50">-</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                {log.client_ip ? (
                                                    <div className="flex items-center gap-1 text-sm text-text-sub">
                                                        <MapPin size={14} />
                                                        {log.client_ip}
                                                    </div>
                                                ) : (
                                                    <span className="text-sm text-text-sub/50">-</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                {log.details ? (
                                                    <button
                                                        onClick={() => alert(JSON.stringify(log.details, null, 2))}
                                                        className="text-sm text-primary hover:underline"
                                                    >
                                                        查看详情
                                                    </button>
                                                ) : (
                                                    <span className="text-sm text-text-sub/50">-</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-20 text-center text-text-sub">
                                            暂无审计日志
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between">
                            <p className="text-sm text-text-sub">
                                共 {total} 条记录，第 {page} / {totalPages} 页
                            </p>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronLeft size={20} />
                                </button>
                                <div className="flex items-center gap-1">
                                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                        let pageNum;
                                        if (totalPages <= 5) {
                                            pageNum = i + 1;
                                        } else if (page <= 3) {
                                            pageNum = i + 1;
                                        } else if (page >= totalPages - 2) {
                                            pageNum = totalPages - 4 + i;
                                        } else {
                                            pageNum = page - 2 + i;
                                        }
                                        return (
                                            <button
                                                key={pageNum}
                                                onClick={() => setPage(pageNum)}
                                                className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                                                    page === pageNum
                                                        ? 'bg-primary text-white'
                                                        : 'hover:bg-gray-100 text-text-sub'
                                                }`}
                                            >
                                                {pageNum}
                                            </button>
                                        );
                                    })}
                                </div>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronRight size={20} />
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </DashboardLayout>
    );
};

import React, { useEffect, useState, useCallback } from 'react';
import { Search, Loader2, Plus, X, UserPlus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { StatCard } from '../Dashboard/components/StatCard';
import { StudentCard } from '../Dashboard/components/StudentCard';
import { studentsApi, adminApi } from '../../api';
import type { Student } from '../../types';

export const StudentListPage: React.FC = () => {
    const [students, setStudents] = useState<Student[]>([]);
    const [stats, setStats] = useState({
        totalStudents: 0,
        totalTests: 0,
        pendingFollowups: 0
    });
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    // 导入学生相关状态
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [importStudentId, setImportStudentId] = useState('');
    const [isImporting, setIsImporting] = useState(false);
    const [importMessage, setImportMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const loadData = useCallback(async () => {
        try {
            const [studentsRes, statsRes] = await Promise.all([
                studentsApi.list(1, 500), // 获取所有学生（前端搜索需要）
                adminApi.getOverview()
            ]);

            // Map API data to UI types (分页响应格式：items 数组)
            const mappedStudents: Student[] = studentsRes.data.items.map(s => ({
                id: s.external_user_id || String(s.user_id),  // Display external ID, fallback to internal
                internalId: String(s.user_id),                 // Internal ID for API calls
                name: s.student_name,
                grade: s.cur_grade || '未设置',
                level: s.cur_level_desc || 'N/A',
                currentUnit: s.main_last_buy_unit_name || 'N/A',
                status: 'active'
            }));

            setStudents(mappedStudents);
            setStats({
                totalStudents: statsRes.data.total_students,
                totalTests: statsRes.data.total_tests,
                pendingFollowups: statsRes.data.pending_followups
            });
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    // 导入学生
    const handleImport = async () => {
        if (!importStudentId.trim()) {
            setImportMessage({ type: 'error', text: '请输入学生ID' });
            return;
        }

        const studentIdNum = Number(importStudentId.trim());
        if (isNaN(studentIdNum) || studentIdNum <= 0) {
            setImportMessage({ type: 'error', text: '请输入有效的学生ID（数字）' });
            return;
        }

        setIsImporting(true);
        setImportMessage(null);

        try {
            const response = await studentsApi.import(studentIdNum);
            const data = response.data as { student_name: string; is_new: boolean; message: string };
            
            setImportMessage({
                type: 'success',
                text: data.is_new 
                    ? `成功添加新学生: ${data.student_name}` 
                    : `学生 ${data.student_name} 已存在，信息已更新`
            });
            
            // 清空输入并刷新列表
            setImportStudentId('');
            await loadData();
            
            // 2秒后关闭弹窗
            setTimeout(() => {
                setIsImportModalOpen(false);
                setImportMessage(null);
            }, 2000);
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            let errorMsg = '导入失败，请稍后重试';
            
            if (typeof detail === 'string') {
                errorMsg = detail;
            } else if (detail?.message) {
                errorMsg = detail.message;
            }
            
            setImportMessage({ type: 'error', text: errorMsg });
        } finally {
            setIsImporting(false);
        }
    };

    // 关闭弹窗时重置状态
    const closeModal = () => {
        setIsImportModalOpen(false);
        setImportStudentId('');
        setImportMessage(null);
    };

    const filteredStudents = students.filter(s =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.id.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">工作台</h1>
                    <p className="text-text-sub mt-1">管理您的学生信息</p>
                </div>
                <button 
                    onClick={() => setIsImportModalOpen(true)}
                    className="btn-primary flex items-center gap-2 shadow-klein hover:shadow-lg transition-shadow"
                >
                    <Plus size={20} />
                    <span>添加学生</span>
                </button>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <StatCard
                    title="学生总数"
                    value={stats.totalStudents}
                    subtext="在读学生"
                    icon="users"
                />
                <StatCard
                    title="总测评数"
                    value={stats.totalTests}
                    subtext="累计测评"
                    icon="book"
                />
                <StatCard
                    title="待跟进"
                    value={stats.pendingFollowups}
                    subtext="未完成测评"
                    icon="alert"
                />
            </div>

            {/* Search Bar */}
            <div className="mb-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-sub/50" size={18} />
                    <input
                        type="text"
                        placeholder="搜索学生姓名或ID..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input-field pl-10"
                    />
                </div>
            </div>

            {/* Student Grid */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
                {filteredStudents.length > 0 ? (
                    filteredStudents.map(student => (
                        <StudentCard key={student.id} student={student} />
                    ))
                ) : (
                    <div className="col-span-full text-center py-20 text-text-sub">
                        <p>未找到匹配 "{searchQuery}" 的学生</p>
                    </div>
                )}
            </div>
            )}

            {/* 添加学生弹窗 */}
            <AnimatePresence>
                {isImportModalOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
                        onClick={(e) => e.target === e.currentTarget && closeModal()}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                        <UserPlus size={20} className="text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-bold text-text-main">添加学生</h3>
                                        <p className="text-xs text-text-sub">通过学生ID从CRM导入</p>
                                    </div>
                                </div>
                                <button
                                    onClick={closeModal}
                                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                >
                                    <X size={20} className="text-text-sub" />
                                </button>
                            </div>

                            {/* Content */}
                            <div className="p-6">
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-text-main mb-2">
                                            学生ID
                                        </label>
                                        <input
                                            type="text"
                                            value={importStudentId}
                                            onChange={(e) => setImportStudentId(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && !isImporting && handleImport()}
                                            placeholder="请输入学生ID（如：12345678）"
                                            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                                            disabled={isImporting}
                                            autoFocus
                                        />
                                        <p className="mt-2 text-xs text-text-sub">
                                            提示：输入您名下学生的ID，系统将自动从CRM获取学生信息
                                        </p>
                                    </div>

                                    {/* 消息提示 */}
                                    <AnimatePresence>
                                        {importMessage && (
                                            <motion.div
                                                initial={{ opacity: 0, y: -10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: -10 }}
                                                className={`p-3 rounded-xl text-sm ${
                                                    importMessage.type === 'success'
                                                        ? 'bg-green-50 text-green-700 border border-green-100'
                                                        : 'bg-red-50 text-red-700 border border-red-100'
                                                }`}
                                            >
                                                {importMessage.text}
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="flex gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50/50">
                                <button
                                    onClick={closeModal}
                                    className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-text-main font-medium hover:bg-gray-100 transition-colors"
                                    disabled={isImporting}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleImport}
                                    disabled={isImporting || !importStudentId.trim()}
                                    className="flex-1 btn-primary py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isImporting ? (
                                        <>
                                            <Loader2 size={18} className="animate-spin" />
                                            <span>导入中...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Plus size={18} />
                                            <span>添加学生</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </DashboardLayout>
    );
};

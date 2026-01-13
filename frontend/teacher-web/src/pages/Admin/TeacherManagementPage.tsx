import React, { useEffect, useState } from 'react';
import { Search, Loader2, Users, FileText, Share2, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type TeacherSummary } from '../../api';

export const TeacherManagementPage: React.FC = () => {
    const navigate = useNavigate();
    const [teachers, setTeachers] = useState<TeacherSummary[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadTeachers();
    }, []);

    const loadTeachers = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await adminApi.getTeachers();
            setTeachers(response.data);
        } catch (err: any) {
            console.error('Failed to load teachers:', err);
            setError(err.response?.data?.detail || '加载老师列表失败');
        } finally {
            setIsLoading(false);
        }
    };

    const filteredTeachers = teachers.filter(t =>
        t.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Calculate totals
    const totalStudents = teachers.reduce((sum, t) => sum + t.student_count, 0);
    const totalTests = teachers.reduce((sum, t) => sum + t.test_count, 0);
    const totalShares = teachers.reduce((sum, t) => sum + t.share_count, 0);

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">老师管理</h1>
                    <p className="text-text-sub mt-1">查看所有老师及其学生分布情况</p>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Users size={20} className="text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{teachers.length}</p>
                            <p className="text-xs text-text-sub">老师总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                            <Users size={20} className="text-green-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{totalStudents}</p>
                            <p className="text-xs text-text-sub">学生总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                            <FileText size={20} className="text-blue-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{totalTests}</p>
                            <p className="text-xs text-text-sub">测评总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                            <Share2 size={20} className="text-purple-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{totalShares}</p>
                            <p className="text-xs text-text-sub">分享总数</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Search Bar */}
            <div className="mb-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-sub/50" size={18} />
                    <input
                        type="text"
                        placeholder="搜索老师邮箱..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input-field pl-10"
                    />
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">
                    {error}
                </div>
            )}

            {/* Teachers Table */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            ) : (
                <div className="bg-surface rounded-2xl shadow-sm overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">老师邮箱</th>
                                <th className="text-center px-6 py-4 text-sm font-semibold text-text-sub">学生数</th>
                                <th className="text-center px-6 py-4 text-sm font-semibold text-text-sub">测评数</th>
                                <th className="text-center px-6 py-4 text-sm font-semibold text-text-sub">分享数</th>
                                <th className="text-right px-6 py-4 text-sm font-semibold text-text-sub">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredTeachers.length > 0 ? (
                                filteredTeachers.map((teacher) => (
                                    <tr
                                        key={teacher.user_id}
                                        className="hover:bg-gray-50 transition-colors cursor-pointer"
                                        onClick={() => navigate(`/admin/teachers/${teacher.user_id}`)}
                                    >
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                                                    <span className="text-primary font-semibold">
                                                        {teacher.email.charAt(0).toUpperCase()}
                                                    </span>
                                                </div>
                                                <span className="font-medium text-text-main">{teacher.email}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium bg-green-100 text-green-700">
                                                {teacher.student_count}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                                                {teacher.test_count}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-700">
                                                {teacher.share_count}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                                                <ChevronRight size={20} className="text-text-sub" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={5} className="px-6 py-20 text-center text-text-sub">
                                        {searchQuery ? `未找到匹配 "${searchQuery}" 的老师` : '暂无老师数据'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </DashboardLayout>
    );
};

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Users, FileText, Share2, CheckCircle } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type TeacherDetail } from '../../api';

export const TeacherDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [teacher, setTeacher] = useState<TeacherDetail | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (id) {
            loadTeacherDetail();
        }
    }, [id]);

    const loadTeacherDetail = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await adminApi.getTeacherDetail(Number(id));
            setTeacher(response.data);
        } catch (err: any) {
            console.error('Failed to load teacher detail:', err);
            setError(err.response?.data?.detail || '加载老师详情失败');
        } finally {
            setIsLoading(false);
        }
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

    if (error || !teacher) {
        return (
            <DashboardLayout>
                <div className="text-center py-20">
                    <p className="text-red-500 text-lg mb-4">{error || '老师不存在'}</p>
                    <button
                        onClick={() => navigate('/admin/teachers')}
                        className="px-4 py-2 bg-primary text-white rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-primary/90 transition-colors mx-auto"
                    >
                        <ArrowLeft size={16} /> 返回老师列表
                    </button>
                </div>
            </DashboardLayout>
        );
    }

    const completionRate = teacher.test_count > 0 
        ? Math.round((teacher.completed_tests / teacher.test_count) * 100) 
        : 0;

    return (
        <DashboardLayout>
            {/* Back Button */}
            <button
                onClick={() => navigate('/admin/teachers')}
                className="mb-6 px-4 py-2 bg-gray-100 text-text-main rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-gray-200 transition-colors"
            >
                <ArrowLeft size={16} /> 返回老师列表
            </button>

            {/* Header */}
            <div className="bg-surface rounded-2xl p-6 shadow-sm mb-8">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-primary text-2xl font-bold">
                            {teacher.email.charAt(0).toUpperCase()}
                        </span>
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-text-main">{teacher.email}</h1>
                        <p className="text-text-sub">用户 ID: {teacher.user_id}</p>
                    </div>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                            <Users size={20} className="text-green-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{teacher.student_count}</p>
                            <p className="text-xs text-text-sub">学生数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                            <FileText size={20} className="text-blue-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{teacher.test_count}</p>
                            <p className="text-xs text-text-sub">测评总数</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                            <CheckCircle size={20} className="text-emerald-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{completionRate}%</p>
                            <p className="text-xs text-text-sub">完成率</p>
                        </div>
                    </div>
                </div>
                <div className="bg-surface rounded-xl p-4 border border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                            <Share2 size={20} className="text-purple-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-main">{teacher.share_count}</p>
                            <p className="text-xs text-text-sub">分享数</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Students List */}
            <div className="bg-surface rounded-2xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                    <h2 className="text-lg font-semibold text-text-main">学生列表</h2>
                </div>
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-100">
                        <tr>
                            <th className="text-left px-6 py-3 text-sm font-semibold text-text-sub">学生姓名</th>
                            <th className="text-center px-6 py-3 text-sm font-semibold text-text-sub">用户 ID</th>
                            <th className="text-center px-6 py-3 text-sm font-semibold text-text-sub">测评数</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {teacher.students.length > 0 ? (
                            teacher.students.map((student) => (
                                <tr key={student.user_id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                                                <span className="text-gray-600 font-medium text-sm">
                                                    {student.student_name?.charAt(0) || '?'}
                                                </span>
                                            </div>
                                            <span className="font-medium text-text-main">
                                                {student.student_name || '未知'}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-center text-text-sub">
                                        {student.user_id}
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                                            {student.test_count}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={3} className="px-6 py-12 text-center text-text-sub">
                                    暂无学生数据
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </DashboardLayout>
    );
};

import React, { useEffect, useState } from 'react';
import { Search, Loader2, Users, FileText, Share2, ChevronRight, ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { adminApi, type TeacherSummary } from '../../api';

const PAGE_SIZE = 20;

export const TeacherManagementPage: React.FC = () => {
    const navigate = useNavigate();
    const [teachers, setTeachers] = useState<TeacherSummary[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    
    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalTeachers, setTotalTeachers] = useState(0);
    const [totalStudents, setTotalStudents] = useState(0);
    const [totalTests, setTotalTests] = useState(0);
    const [totalShares, setTotalShares] = useState(0);

    useEffect(() => {
        loadTeachers(currentPage);
    }, [currentPage]);

    const loadTeachers = async (page: number) => {
        setIsLoading(true);
        setError('');
        try {
            const response = await adminApi.getTeachers(page, PAGE_SIZE);
            const data = response.data;
            setTeachers(data.items);
            setTotalTeachers(data.total);
            setTotalPages(Math.ceil(data.total / PAGE_SIZE));
            setTotalStudents(data.total_students);
            setTotalTests(data.total_tests);
            setTotalShares(data.total_shares);
        } catch (err: any) {
            console.error('Failed to load teachers:', err);
            setError(err.response?.data?.detail || '加载老师列表失败');
        } finally {
            setIsLoading(false);
        }
    };

    const filteredTeachers = teachers.filter(t =>
        t.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.ss_crm_name && t.ss_crm_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.ss_dept4_name && t.ss_dept4_name.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    const handlePageChange = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
            setSearchQuery(''); // Reset search when changing page
        }
    };

    // Generate page numbers to display
    const getPageNumbers = () => {
        const pages: (number | string)[] = [];
        const maxVisible = 5;
        
        if (totalPages <= maxVisible + 2) {
            // Show all pages if total is small
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            // Always show first page
            pages.push(1);
            
            if (currentPage > 3) {
                pages.push('...');
            }
            
            // Show pages around current
            const start = Math.max(2, currentPage - 1);
            const end = Math.min(totalPages - 1, currentPage + 1);
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            
            if (currentPage < totalPages - 2) {
                pages.push('...');
            }
            
            // Always show last page
            if (totalPages > 1) {
                pages.push(totalPages);
            }
        }
        
        return pages;
    };

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
                            <p className="text-2xl font-bold text-text-main">{totalTeachers}</p>
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
                            <p className="text-xs text-text-sub">本页学生数</p>
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
                            <p className="text-xs text-text-sub">本页测评数</p>
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
                            <p className="text-xs text-text-sub">本页分享数</p>
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
                        placeholder="在当前页搜索老师姓名、邮箱或部门..."
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
                <>
                <div className="bg-surface rounded-2xl shadow-sm overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">老师</th>
                                <th className="text-left px-6 py-4 text-sm font-semibold text-text-sub">部门</th>
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
                                                        {(teacher.ss_crm_name || teacher.email).charAt(0).toUpperCase()}
                                                    </span>
                                                </div>
                                                <div>
                                                    <p className="font-medium text-text-main">
                                                        {teacher.ss_crm_name || teacher.email}
                                                    </p>
                                                    {teacher.ss_crm_name && (
                                                        <p className="text-xs text-text-sub">{teacher.email}</p>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-left">
                                            <span className="text-sm text-text-sub">
                                                {teacher.ss_dept4_name || '-'}
                                            </span>
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
                                    <td colSpan={6} className="px-6 py-20 text-center text-text-sub">
                                        {searchQuery ? `未找到匹配 "${searchQuery}" 的老师` : '暂无老师数据'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between mt-6 px-2">
                            <p className="text-sm text-text-sub">
                                显示第 {(currentPage - 1) * PAGE_SIZE + 1} - {Math.min(currentPage * PAGE_SIZE, totalTeachers)} 条，共 {totalTeachers} 条
                            </p>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => handlePageChange(currentPage - 1)}
                                    disabled={currentPage === 1}
                                    className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronLeft size={18} />
                                </button>
                                
                                {getPageNumbers().map((page, index) => (
                                    typeof page === 'number' ? (
                                        <button
                                            key={index}
                                            onClick={() => handlePageChange(page)}
                                            className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                                                currentPage === page
                                                    ? 'bg-primary text-white'
                                                    : 'border border-gray-200 hover:bg-gray-50 text-text-main'
                                            }`}
                                        >
                                            {page}
                                        </button>
                                    ) : (
                                        <span key={index} className="px-2 text-text-sub">
                                            {page}
                                        </span>
                                    )
                                ))}
                                
                                <button
                                    onClick={() => handlePageChange(currentPage + 1)}
                                    disabled={currentPage === totalPages}
                                    className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronRight size={18} />
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </DashboardLayout>
    );
};

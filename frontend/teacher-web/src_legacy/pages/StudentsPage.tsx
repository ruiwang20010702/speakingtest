import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentsApi, type StudentListItem } from '../api';
import { useAuthStore } from '../stores/authStore';
import Layout from '../components/Layout';

export default function StudentsPage() {
    const navigate = useNavigate();
    const { role } = useAuthStore();
    const isAdmin = role === 'admin';

    const [students, setStudents] = useState<StudentListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');

    // Import modal state
    const [showImport, setShowImport] = useState(false);
    const [importId, setImportId] = useState('');
    const [importing, setImporting] = useState(false);

    useEffect(() => {
        loadStudents();
    }, []);

    const loadStudents = async () => {
        try {
            const response = await studentsApi.list();
            setStudents(response.data);
        } catch (err) {
            setError('加载学生列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleImport = async () => {
        if (!importId) return;

        setImporting(true);
        try {
            await studentsApi.import(parseInt(importId));
            setShowImport(false);
            setImportId('');
            loadStudents();
        } catch (err: unknown) {
            console.error(err);
            const error = err as any;
            let msg = '导入失败';
            if (error.response?.data?.detail) {
                const detail = error.response.data.detail;
                if (typeof detail === 'string') {
                    msg = detail;
                } else if (Array.isArray(detail)) {
                    msg = detail.map((d: any) => d.msg).join(', ');
                } else if (typeof detail === 'object') {
                    msg = JSON.stringify(detail);
                }
            }
            alert(msg);
        } finally {
            setImporting(false);
        }
    };

    // Calculate stats
    const stats = {
        total: students.length,
        active: students.length,
        tested: students.filter(s => s.cur_level_desc).length
    };

    const filteredStudents = students.filter((s) =>
        s.student_name.toLowerCase().includes(search.toLowerCase()) ||
        s.external_user_id?.toLowerCase().includes(search.toLowerCase()) ||
        (role === 'admin' && (
            s.teacher_name?.toLowerCase().includes(search.toLowerCase()) ||
            s.ss_crm_name?.toLowerCase().includes(search.toLowerCase())
        ))
    );

    const pageActions = (
        <>
                        {isAdmin && (
                            <button
                                onClick={() => navigate('/admin/dashboard')}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
                >
                    <span className="text-lg">📊</span>
                    <span>运营看板</span>
                            </button>
                        )}
                        <button
                            onClick={() => setShowImport(true)}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover shadow-sm transition-all shadow-primary/20"
                        >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                <span>导入学生</span>
                        </button>
        </>
    );

    return (
        <Layout 
            title={isAdmin ? '系统管理' : '我的学生'} 
            actions={pageActions}
        >
            {/* Dashboard Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                    <span className="text-gray-500 text-sm font-medium mb-2">学生总数</span>
                    <span className="text-4xl font-bold text-gray-900">{stats.total}</span>
                    </div>
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                    <span className="text-gray-500 text-sm font-medium mb-2">本周测评</span>
                    <span className="text-4xl font-bold text-gray-900 flex items-baseline gap-1">
                        0 <span className="text-sm font-normal text-gray-400">次</span>
                    </span>
                </div>
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                    <span className="text-gray-500 text-sm font-medium mb-2">待跟进</span>
                    <span className="text-4xl font-bold text-emerald-600 flex items-baseline gap-1">
                        0 <span className="text-sm font-normal text-emerald-400">人</span>
                    </span>
                    </div>
                </div>

                {/* Search Bar */}
            <div className="relative mb-8 max-w-2xl mx-auto">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <input
                        type="text"
                    className="block w-full pl-11 pr-4 py-4 bg-white border border-gray-200 rounded-xl leading-5 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all shadow-sm text-base"
                        placeholder={isAdmin ? "搜索学生姓名/ID/老师/CRM账号..." : "搜索学生姓名或ID..."}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>

            {/* Student List */}
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
                    <p className="text-gray-500">加载中...</p>
                    </div>
                ) : error ? (
                <div className="text-center py-10 bg-red-50 text-red-600 rounded-xl border border-red-100">
                        {error}
                    </div>
                ) : filteredStudents.length === 0 ? (
                <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-200">
                    <p className="text-gray-500 text-lg mb-4">暂无学生</p>
                        <button
                            onClick={() => setShowImport(true)}
                        className="text-primary hover:text-primary-hover font-medium underline underline-offset-4"
                        >
                            导入第一个学生
                        </button>
                    </div>
                ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredStudents.map((student) => (
                            <div
                                key={student.user_id}
                                onClick={() => navigate(`/students/${student.user_id}`)}
                            className="group bg-white rounded-xl border border-gray-100 p-5 shadow-sm hover:shadow-lg hover:border-primary/20 transition-all cursor-pointer relative overflow-hidden"
                        >
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white flex items-center justify-center text-xl font-bold shadow-md shadow-primary/20">
                                        {student.student_name.charAt(0)}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-900 group-hover:text-primary transition-colors flex items-center gap-2">
                                            {student.student_name}
                                            {isAdmin && student.teacher_name && (
                                                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500 border border-gray-200">
                                                    {student.teacher_name}
                                                </span>
                                            )}
                                        </h3>
                                        <p className="text-sm text-gray-500 font-mono">ID: {student.external_user_id || student.user_id}</p>
                                    </div>
                                </div>
                                <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center text-gray-300 group-hover:bg-primary group-hover:text-white transition-all transform group-hover:translate-x-1">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </div>
                            </div>

                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {student.cur_grade && (
                                    <span className="px-2.5 py-1 rounded-md bg-gray-50 text-gray-600 text-xs font-medium border border-gray-100">
                                                    {student.cur_grade}
                                                </span>
                                            )}
                                            {student.cur_level_desc && (
                                    <span className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 text-xs font-medium border border-blue-100">
                                                    {student.cur_level_desc}
                                                </span>
                                            )}
                                        {student.main_last_buy_unit_name && (
                                    <span className="px-2.5 py-1 rounded-md bg-yellow-50 text-yellow-700 text-xs font-medium border border-yellow-100 max-w-full truncate" title={student.main_last_buy_unit_name}>
                                        {student.main_last_buy_unit_name}
                                    </span>
                                        )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

            {/* Import Modal */}
            {showImport && (
                <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div 
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all scale-100" 
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6 border-b border-gray-100">
                            <h2 className="text-xl font-bold text-gray-900">导入学生</h2>
                            <p className="text-sm text-gray-500 mt-1">输入 CRM 中的学生 ID，系统将自动同步档案</p>
                        </div>
                        
                        <div className="p-6">
                            <input
                                type="text"
                                placeholder="请输入学生 ID (例如: 59329899)"
                                value={importId}
                                onChange={(e) => setImportId(e.target.value.replace(/\D/g, ''))}
                                disabled={importing}
                                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-gray-900 placeholder:text-gray-400 text-lg tracking-wide font-mono"
                                autoFocus
                            />
                        </div>

                        <div className="p-6 pt-0 flex gap-3 bg-gray-50/50">
                            <button
                                className="flex-1 px-4 py-3 border border-gray-200 text-gray-700 font-medium rounded-xl hover:bg-white hover:border-gray-300 hover:shadow-sm transition-all disabled:opacity-50"
                                onClick={() => setShowImport(false)}
                                disabled={importing}
                            >
                                取消
                            </button>
                            <button
                                className="flex-1 px-4 py-3 bg-primary text-white font-bold rounded-xl hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all disabled:opacity-50 disabled:shadow-none"
                                onClick={handleImport}
                                disabled={importing || !importId}
                            >
                                {importing ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        导入中...
                                    </span>
                                ) : '确认导入'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentsApi, type StudentListItem } from '../api';
import { useAuthStore } from '../stores/authStore';
import './StudentsPage.css';

export default function StudentsPage() {
    const navigate = useNavigate();
    const { teacherName, role, logout } = useAuthStore();

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
                    // FastAPI validation error
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
        active: students.length, // For now, all are active
        tested: students.filter(s => s.cur_level_desc).length // Proxy for "has level" or we need test count from API
    };

    const filteredStudents = students.filter((s) =>
        s.student_name.toLowerCase().includes(search.toLowerCase()) ||
        s.external_user_id?.toLowerCase().includes(search.toLowerCase()) ||
        (role === 'admin' && (
            s.teacher_name?.toLowerCase().includes(search.toLowerCase()) ||
            s.ss_crm_name?.toLowerCase().includes(search.toLowerCase())
        ))
    );

    const isAdmin = role === 'admin';

    return (
        <div className="students-page">
            <header className="page-header">
                <div className="header-left">
                    <img src="/src/assets/logo.png" alt="51Talk" className="header-logo" />
                    <div className="header-title">
                        <h1>{isAdmin ? '系统管理' : '我的学生'}</h1>
                        <span className="teacher-name">欢迎，{teacherName || (isAdmin ? '管理员' : '老师')}</span>
                    </div>
                </div>
                <div className="header-right">
                    {isAdmin && (
                        <button className="btn-secondary" onClick={() => navigate('/admin/dashboard')} style={{ marginRight: '12px' }}>
                            📊 运营看板
                        </button>
                    )}
                    <button className="btn-import" onClick={() => setShowImport(true)}>
                        + 导入学生
                    </button>
                    <button className="btn-logout" onClick={logout}>
                        退出
                    </button>
                </div>
            </header>

            <div className="dashboard-stats">
                <div className="stat-card">
                    <span className="stat-label">学生总数</span>
                    <span className="stat-value">{stats.total}</span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">本周测评</span>
                    <span className="stat-value">0</span>
                    <span className="stat-sub">暂无数据</span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">待跟进</span>
                    <span className="stat-value">0</span>
                    <span className="stat-sub">暂无异常</span>
                </div>
            </div>

            <div className="search-bar">
                <input
                    type="text"
                    placeholder={isAdmin ? "搜索学生姓名/ID/老师/CRM账号..." : "搜索学生姓名或ID..."}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {loading ? (
                <div className="loading">加载中...</div>
            ) : error ? (
                <div className="error">{error}</div>
            ) : filteredStudents.length === 0 ? (
                <div className="empty">
                    <p>暂无学生</p>
                    <button onClick={() => setShowImport(true)}>导入第一个学生</button>
                </div>
            ) : (
                <div className="students-grid">
                    {filteredStudents.map((student) => (
                        <div
                            key={student.user_id}
                            className="student-card"
                            onClick={() => navigate(`/students/${student.user_id}`)}
                        >
                            <div className="student-avatar">
                                {student.student_name.charAt(0)}
                            </div>
                            <div className="student-info">
                                <h3>
                                    {student.student_name}
                                    {isAdmin && student.teacher_name && (
                                        <span className="teacher-tag">{student.teacher_name}</span>
                                    )}
                                </h3>
                                <div className="student-meta">
                                    <span className="meta-tag">ID: {student.external_user_id || student.user_id}</span>
                                    {student.cur_grade && <span className="meta-tag">{student.cur_grade}</span>}
                                    {student.cur_level_desc && <span className="meta-tag">{student.cur_level_desc}</span>}
                                    {student.main_last_buy_unit_name && (
                                        <span className="meta-tag unit-tag" title={student.main_last_buy_unit_name}>
                                            {student.main_last_buy_unit_name}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="student-action">
                                <span className="arrow">→</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Import Modal */}
            {showImport && (
                <div className="modal-overlay" onClick={() => setShowImport(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2>导入学生</h2>
                        <p>输入学生 ID，系统将自动从 CRM 获取信息</p>
                        <input
                            type="text"
                            placeholder="学生 ID (例如: 59329899)"
                            value={importId}
                            onChange={(e) => setImportId(e.target.value.replace(/\D/g, ''))}
                            disabled={importing}
                        />
                        <div className="modal-actions">
                            <button
                                className="btn-cancel"
                                onClick={() => setShowImport(false)}
                                disabled={importing}
                            >
                                取消
                            </button>
                            <button
                                className="btn-confirm"
                                onClick={handleImport}
                                disabled={importing || !importId}
                            >
                                {importing ? '导入中...' : '确认导入'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

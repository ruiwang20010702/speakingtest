import React, { useEffect, useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { StatCard } from '../Dashboard/components/StatCard';
import { StudentCard } from '../Dashboard/components/StudentCard';
import { studentsApi, adminApi } from '../../api';
import type { Student } from '../../types';

export const StudentListPage: React.FC = () => {
    const [students, setStudents] = useState<Student[]>([]);
    const [stats, setStats] = useState({
        totalStudents: 0,
        totalTests: 0
    });
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const [studentsRes, statsRes] = await Promise.all([
                    studentsApi.list(),
                    adminApi.getOverview()
                ]);

                // Map API data to UI types
                const mappedStudents: Student[] = studentsRes.data.map(s => ({
                    id: String(s.user_id),
                    name: s.student_name,
                    grade: s.cur_grade || '未设置',
                    level: s.cur_level_desc || 'N/A',
                    currentUnit: s.main_last_buy_unit_name || 'N/A',
                    status: 'active'
                }));

                setStudents(mappedStudents);
                setStats({
                    totalStudents: statsRes.data.total_students,
                    totalTests: statsRes.data.total_tests
                });
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
            } finally {
                setIsLoading(false);
            }
        };
        load();
    }, []);

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
                {/* 
                <button className="btn-primary flex items-center gap-2 shadow-klein hover:shadow-lg transition-shadow">
                    <Plus size={20} />
                    <span>导入学生</span>
                </button>
                */}
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
                    value="0"
                    subtext="暂无事项"
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
        </DashboardLayout>
    );
};

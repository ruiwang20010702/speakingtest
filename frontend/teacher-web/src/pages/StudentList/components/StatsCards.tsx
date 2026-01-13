import React from 'react';
import { Users, BookOpen, AlertCircle } from 'lucide-react';
import type { StatsOverview } from '../../../types';

interface StatsProps {
    stats: StatsOverview;
}

export const StatsCards: React.FC<StatsProps> = ({ stats }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div className="card-surface p-6 flex flex-col items-center justify-center text-center transition-transform hover:-translate-y-1 duration-300">
                <div className="mb-3 p-3 bg-blue-50 text-primary rounded-full">
                    <Users size={24} />
                </div>
                <h3 className="text-text-sub text-sm font-medium uppercase tracking-wider">学生总数</h3>
                <p className="text-4xl font-bold text-text-main mt-1">{stats.totalStudents}</p>
            </div>

            <div className="card-surface p-6 flex flex-col items-center justify-center text-center transition-transform hover:-translate-y-1 duration-300">
                <div className="mb-3 p-3 bg-yellow-50 text-yellow-600 rounded-full">
                    <BookOpen size={24} />
                </div>
                <h3 className="text-text-sub text-sm font-medium uppercase tracking-wider">本周测评</h3>
                <p className="text-4xl font-bold text-text-main mt-1">{stats.assessmentsThisWeek}</p>
                <span className="text-xs text-text-sub/60 mt-2">次测评</span>
            </div>

            <div className="card-surface p-6 flex flex-col items-center justify-center text-center transition-transform hover:-translate-y-1 duration-300 border-l-4 border-l-secondary">
                <div className="mb-3 p-3 bg-orange-50 text-orange-600 rounded-full">
                    <AlertCircle size={24} />
                </div>
                <h3 className="text-text-sub text-sm font-medium uppercase tracking-wider">待跟进</h3>
                <p className="text-4xl font-bold text-text-main mt-1">{stats.pendingFollowUp}</p>
                <span className="text-xs text-text-sub/60 mt-2">紧急事项</span>
            </div>
        </div>
    );
};

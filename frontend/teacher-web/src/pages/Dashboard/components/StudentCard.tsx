import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Student } from '../../../types';

interface StudentCardProps {
    student: Student;
}

export const StudentCard: React.FC<StudentCardProps> = ({ student }) => {
    const navigate = useNavigate();

    return (
        <div
            onClick={() => navigate(`/student/${student.id}`, { state: { student } })}
            className="bg-surface rounded-2xl p-6 shadow-sm hover:shadow-klein border border-transparent hover:border-primary/10 transition-all duration-300 cursor-pointer group"
        >
            <div className="flex items-start gap-4">
                {/* Avatar */}
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center text-primary font-bold text-lg shrink-0">
                    {student.name.substring(0, 2)}
                </div>

                <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-bold text-text-main truncate group-hover:text-primary transition-colors">
                        {student.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-text-sub">ID: {student.id}</span>
                        <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-text-sub font-semibold">
                            {student.level}
                        </span>
                    </div>
                    <p className="text-xs text-text-sub mt-2">{student.currentUnit}</p>
                </div>
            </div>
        </div>
    );
};

import React from 'react';
import { ArrowRight } from 'lucide-react';
import type { Student } from '../../../types';
import { useNavigate } from 'react-router-dom';

interface StudentCardProps {
    student: Student;
}

export const StudentCard: React.FC<StudentCardProps> = ({ student }) => {
    const navigate = useNavigate();

    // Generate initials for avatar
    const initials = student.name.substring(0, 2).toUpperCase();
    const bgColors = ['bg-blue-100', 'bg-indigo-100', 'bg-purple-100', 'bg-emerald-100'];
    const colorIndex = student.id.charCodeAt(student.id.length - 1) % bgColors.length;

    return (
        <div
            onClick={() => navigate(`/student/${student.internalId}`)}
            className="card-surface p-5 flex items-center justify-between cursor-pointer group hover:border-primary/30 transition-all duration-300"
        >
            <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center text-primary font-bold ${bgColors[colorIndex]}`}>
                    {initials}
                </div>
                <div>
                    <h4 className="text-lg font-bold text-text-main group-hover:text-primary transition-colors">{student.name}</h4>
                    <div className="flex items-center gap-2 mt-1">
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded font-medium">{student.id}</span>
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded font-medium">{student.grade} {student.level}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <span className="hidden md:block px-3 py-1 bg-green-50 text-green-700 text-xs rounded-full border border-green-100">
                    {student.currentUnit}
                </span>
                <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-primary group-hover:text-white transition-all duration-300 transform group-hover:translate-x-1">
                    <ArrowRight size={16} />
                </div>
            </div>
        </div>
    );
};

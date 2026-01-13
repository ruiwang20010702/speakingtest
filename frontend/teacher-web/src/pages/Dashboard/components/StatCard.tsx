import React from 'react';
import { Users, BookOpen, AlertCircle } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: string | number;
    subtext: string;
    icon: 'users' | 'book' | 'alert';
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, subtext, icon }) => {
    const icons = {
        users: Users,
        book: BookOpen,
        alert: AlertCircle
    };

    const Icon = icons[icon];

    return (
        <div className="bg-surface rounded-2xl p-6 shadow-klein border border-slate-100 hover:-translate-y-1 transition-transform duration-300">
            <div className="mb-3 p-3 bg-blue-50 text-primary rounded-full w-fit">
                <Icon size={24} />
            </div>
            <h3 className="text-text-sub text-xs font-bold uppercase tracking-widest mb-2">{title}</h3>
            <p className="text-4xl font-bold text-text-main tracking-tight">{value}</p>
            <p className="text-xs text-text-sub mt-2">{subtext}</p>
        </div>
    );
};

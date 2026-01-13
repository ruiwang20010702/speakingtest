import React from 'react';
import clsx from 'clsx';
import type { AssessmentStatus } from '../../types';

interface StatusBadgeProps {
    status: AssessmentStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
    const styles = {
        completed: 'bg-green-100 text-green-700 border-green-200',
        in_progress: 'bg-secondary/20 text-yellow-700 border-secondary/40',
        pending: 'bg-slate-100 text-slate-600 border-slate-200',
        failed: 'bg-red-50 text-red-600 border-red-100',
    };

    const labels = {
        completed: '已完成',
        in_progress: '测试中',
        pending: '待开始',
        failed: '失败'
    };

    return (
        <span className={clsx(
            'px-2.5 py-0.5 rounded-full text-xs font-semibold border',
            styles[status]
        )}>
            {labels[status]}
        </span>
    );
};

import React, { useState } from 'react';
import { X } from 'lucide-react';

interface NewAssessmentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (level: string, unit: string) => void;
    isCreating: boolean;
}

export const NewAssessmentModal: React.FC<NewAssessmentModalProps> = ({ isOpen, onClose, onSubmit, isCreating }) => {
    if (!isOpen) return null;

    const [level, setLevel] = useState('L0 (Beginner)');
    const [unit, setUnit] = useState('All Units');

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" onClick={onClose}></div>

            <div className="relative bg-surface rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-slate-50/50">
                    <h3 className="font-bold text-lg text-text-main">发起新测评</h3>
                    <button onClick={onClose} className="text-text-sub hover:text-text-main transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-5">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text-sub">选择级别</label>
                        <select
                            value={level}
                            onChange={(e) => setLevel(e.target.value)}
                            className="input-field appearance-none bg-[url('https://api.iconify.design/lucide/chevron-down.svg?color=%2394a3b8')] bg-no-repeat bg-[right_1rem_center]"
                        >
                            <option>L0 (Beginner)</option>
                            <option>L1 (Elementary)</option>
                            <option>L2 (Intermediate)</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text-sub">选择单元</label>
                        <select
                            value={unit}
                            onChange={(e) => setUnit(e.target.value)}
                            className="input-field appearance-none bg-[url('https://api.iconify.design/lucide/chevron-down.svg?color=%2394a3b8')] bg-no-repeat bg-[right_1rem_center]"
                        >
                            <option>全部单元</option>
                            <option>单元 1</option>
                            <option>单元 2</option>
                        </select>
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-border bg-slate-50/50 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-sm font-medium text-text-sub hover:bg-slate-100 transition-colors"
                    >
                        取消
                    </button>
                    <button
                        onClick={() => onSubmit(level, unit)}
                        disabled={isCreating}
                        className="btn-primary py-2 px-6 text-sm flex items-center gap-2"
                    >
                        {isCreating ? '生成中...' : '生成测评链接'}
                    </button>
                </div>
            </div>
        </div>
    );
};

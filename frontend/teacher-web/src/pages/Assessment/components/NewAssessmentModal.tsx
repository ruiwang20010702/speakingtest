import React, { useState, useMemo } from 'react';
import { X } from 'lucide-react';

interface NewAssessmentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (level: string, unit: string) => void;
    isCreating: boolean;
}

// Level 配置
const LEVEL_CONFIG: Record<string, { name: string; units: number }> = {
    'L0': { name: 'L0 (Starter)', units: 18 },
    'L1': { name: 'L1 (Beginner)', units: 18 },
    'L2': { name: 'L2 (Elementary)', units: 18 },
    'L3': { name: 'L3 (Pre-Intermediate)', units: 18 },
    'L4': { name: 'L4 (Intermediate)', units: 18 },
    'L5': { name: 'L5 (Upper-Intermediate)', units: 18 },
    'L6': { name: 'L6 (Advanced)', units: 18 },
    'L7': { name: 'L7 (Proficient)', units: 6 },
    'L8': { name: 'L8 (Expert)', units: 6 },
    'L9': { name: 'L9 (Master)', units: 6 },
};

const LEVELS = Object.keys(LEVEL_CONFIG);

export const NewAssessmentModal: React.FC<NewAssessmentModalProps> = ({ isOpen, onClose, onSubmit, isCreating }) => {
    const [level, setLevel] = useState('L0');
    const [unit, setUnit] = useState('Unit 1');

    // 根据选中的 level 动态生成单元选项
    const unitOptions = useMemo(() => {
        const config = LEVEL_CONFIG[level];
        if (!config) return [];
        
        const options: { value: string; label: string }[] = [];
        
        // 添加各个单元（移除"全部单元"选项）
        for (let i = 1; i <= config.units; i++) {
            options.push({ value: `Unit ${i}`, label: `单元 ${i}` });
        }
        
        return options;
    }, [level]);

    // 当 level 改变时，重置 unit 为第一个单元
    const handleLevelChange = (newLevel: string) => {
        setLevel(newLevel);
        setUnit('Unit 1');
    };

    if (!isOpen) return null;

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
                        <label className="block text-sm font-semibold text-text-main mb-2">
                            📚 选择级别
                        </label>
                        <div className="relative">
                            <select
                                value={level}
                                onChange={(e) => handleLevelChange(e.target.value)}
                                className="w-full px-4 py-3 pr-10 text-base font-medium text-text-main bg-white border-2 border-border rounded-xl shadow-sm appearance-none cursor-pointer transition-all hover:border-primary focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
                            >
                                {LEVELS.map(lvl => (
                                    <option key={lvl} value={lvl}>{LEVEL_CONFIG[lvl].name}</option>
                                ))}
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                <svg className="w-5 h-5 text-text-sub" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="block text-sm font-semibold text-text-main mb-2">
                            📖 选择单元
                        </label>
                        <div className="relative">
                            <select
                                value={unit}
                                onChange={(e) => setUnit(e.target.value)}
                                className="w-full px-4 py-3 pr-10 text-base font-medium text-text-main bg-white border-2 border-border rounded-xl shadow-sm appearance-none cursor-pointer transition-all hover:border-primary focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
                            >
                                {unitOptions.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                <svg className="w-5 h-5 text-text-sub" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>
                        </div>
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

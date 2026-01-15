import React, { useState, useMemo } from 'react';
import { X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    {/* Background Overlay */}
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-slate-900/60 backdrop-blur-md" 
                        onClick={onClose}
                    />

                    {/* Modal Card */}
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="relative bg-surface rounded-3xl shadow-2xl w-full max-w-md overflow-hidden border border-white/20"
                    >
                {/* Header */}
                        <div className="px-8 py-6 border-b border-border flex items-center justify-between bg-slate-50/50">
                            <div>
                                <h3 className="font-bold text-xl text-text-main">发起新测评</h3>
                                <p className="text-sm text-text-sub mt-1">请选择测评的难度级别和单元内容</p>
                            </div>
                            <button 
                                onClick={onClose} 
                                className="p-2 text-text-sub hover:bg-slate-200 hover:text-text-main rounded-full transition-all"
                            >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                        <div className="p-8 space-y-6">
                            <div className="space-y-3">
                                <label className="block text-sm font-bold text-text-main">
                                    📚 选择级别
                                </label>
                                <div className="relative">
                        <select
                            value={level}
                                        onChange={(e) => handleLevelChange(e.target.value)}
                                        className="w-full px-4 py-3.5 pr-10 text-base font-semibold text-text-main bg-white border-2 border-border rounded-2xl shadow-sm appearance-none cursor-pointer transition-all hover:border-primary focus:border-primary focus:ring-4 focus:ring-primary/10 focus:outline-none"
                                    >
                                        {LEVELS.map(lvl => (
                                            <option key={lvl} value={lvl}>{LEVEL_CONFIG[lvl].name}</option>
                                        ))}
                        </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none">
                                        <svg className="w-5 h-5 text-text-sub" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                    </div>

                            <div className="space-y-3">
                                <label className="block text-sm font-bold text-text-main">
                                    📖 选择单元
                                </label>
                                <div className="relative">
                        <select
                            value={unit}
                            onChange={(e) => setUnit(e.target.value)}
                                        className="w-full px-4 py-3.5 pr-10 text-base font-semibold text-text-main bg-white border-2 border-border rounded-2xl shadow-sm appearance-none cursor-pointer transition-all hover:border-primary focus:border-primary focus:ring-4 focus:ring-primary/10 focus:outline-none"
                        >
                                        {unitOptions.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                        </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none">
                                        <svg className="w-5 h-5 text-text-sub" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                    </div>
                </div>

                {/* Footer */}
                        <div className="px-8 py-6 border-t border-border bg-slate-50/50 flex justify-end gap-4">
                    <button
                        onClick={onClose}
                                className="px-6 py-3 rounded-xl text-base font-bold text-text-sub hover:bg-slate-200 transition-all active:scale-95"
                    >
                        取消
                    </button>
                    <button
                        onClick={() => onSubmit(level, unit)}
                        disabled={isCreating}
                                className="btn-primary py-3 px-8 text-base font-bold flex items-center gap-2 shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-1 active:translate-y-0 transition-all disabled:opacity-70 disabled:translate-y-0 disabled:shadow-none"
                    >
                                {isCreating ? (
                                    <>
                                        <Loader2 className="animate-spin" size={20} />
                                        <span>正在生成...</span>
                                    </>
                                ) : (
                                    '生成测评链接'
                                )}
                    </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};

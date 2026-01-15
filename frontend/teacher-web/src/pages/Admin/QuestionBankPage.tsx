import React, { useEffect, useState, useRef } from 'react';
import { Loader2, Plus, Edit2, Trash2, Save, X, Upload, BookOpen, ChevronDown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DashboardLayout } from '../../components/Layout/DashboardLayout';
import { questionsApi, type Question, type QuestionCreate, type QuestionUpdate } from '../../api';

// Available levels and units (can be fetched from API later)
const LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9'];
const UNITS = ['Unit 1', 'Unit 2', 'Unit 3', 'Unit 4', 'Unit 5', 'Unit 6', 'Unit 7', 'Unit 8', 'Unit 9', 'Unit 10', 'Unit 11', 'Unit 12'];

export const QuestionBankPage: React.FC = () => {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [selectedLevel, setSelectedLevel] = useState<string>('L0');
    const [selectedUnit, setSelectedUnit] = useState<string>('Unit 1');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    
    // Edit state
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<QuestionUpdate>({});
    
    // Create state
    const [isCreating, setIsCreating] = useState(false);
    const [createForm, setCreateForm] = useState<Partial<QuestionCreate>>({});
    const [createPart, setCreatePart] = useState<1 | 2>(1);
    
    // Upload state
    const [uploadingId, setUploadingId] = useState<number | null>(null);
    
    // Dropdown state
    const [isLevelDropdownOpen, setIsLevelDropdownOpen] = useState(false);
    const [isUnitDropdownOpen, setIsUnitDropdownOpen] = useState(false);
    const levelDropdownRef = useRef<HTMLDivElement>(null);
    const unitDropdownRef = useRef<HTMLDivElement>(null);
    
    // Close dropdowns when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (levelDropdownRef.current && !levelDropdownRef.current.contains(event.target as Node)) {
                setIsLevelDropdownOpen(false);
            }
            if (unitDropdownRef.current && !unitDropdownRef.current.contains(event.target as Node)) {
                setIsUnitDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        loadQuestions();
    }, [selectedLevel, selectedUnit]);

    const loadQuestions = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await questionsApi.list(selectedLevel, selectedUnit);
            setQuestions(response.data);
        } catch (err: any) {
            console.error('Failed to load questions:', err);
            setError(err.response?.data?.detail || '加载题目失败');
        } finally {
            setIsLoading(false);
        }
    };

    const handleEdit = (question: Question) => {
        setEditingId(question.id);
        setEditForm({
            question: question.question,
            translation: question.translation,
            reference_answer: question.reference_answer,
        });
    };

    const handleSaveEdit = async (id: number) => {
        try {
            await questionsApi.update(id, editForm);
            setEditingId(null);
            setEditForm({});
            loadQuestions();
        } catch (err: any) {
            console.error('Failed to update question:', err);
            alert(err.response?.data?.detail || '更新题目失败');
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除这道题目吗？')) return;
        
        try {
            await questionsApi.delete(id);
            loadQuestions();
        } catch (err: any) {
            console.error('Failed to delete question:', err);
            alert(err.response?.data?.detail || '删除题目失败');
        }
    };

    const handleCreate = async () => {
        if (!createForm.question) {
            alert('请输入题目内容');
            return;
        }
        
        const nextNo = questions.filter(q => q.part === createPart).length + 1;
        
        try {
            await questionsApi.create({
                level: selectedLevel,
                unit: selectedUnit,
                part: createPart,
                question_no: nextNo,
                question: createForm.question!,
                translation: createForm.translation,
                reference_answer: createForm.reference_answer,
            });
            setIsCreating(false);
            setCreateForm({});
            loadQuestions();
        } catch (err: any) {
            console.error('Failed to create question:', err);
            alert(err.response?.data?.detail || '创建题目失败');
        }
    };

    const handleImageUpload = async (questionId: number, file: File) => {
        setUploadingId(questionId);
        try {
            await questionsApi.uploadImage(questionId, file);
            loadQuestions();
        } catch (err: any) {
            console.error('Failed to upload image:', err);
            alert(err.response?.data?.detail || '上传图片失败');
        } finally {
            setUploadingId(null);
        }
    };

    const part1Questions = questions.filter(q => q.part === 1);
    const part2Questions = questions.filter(q => q.part === 2);

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-main tracking-tight">题库管理</h1>
                    <p className="text-text-sub mt-1">按 Level/Unit 管理测评题目</p>
                </div>
                <button
                    onClick={() => setIsCreating(true)}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus size={20} />
                    <span>新增题目</span>
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-4 mb-8">
                {/* Level Dropdown */}
                <div className="flex-1 max-w-xs" ref={levelDropdownRef}>
                    <label className="block text-sm font-medium text-text-sub mb-2">Level</label>
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => { setIsLevelDropdownOpen(!isLevelDropdownOpen); setIsUnitDropdownOpen(false); }}
                            className="w-full flex items-center justify-between px-4 py-3 bg-surface border border-gray-200 rounded-xl text-left hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        >
                            <span className="text-text-main font-medium">{selectedLevel}</span>
                            <ChevronDown 
                                size={18} 
                                className={`text-text-sub transition-transform duration-200 ${isLevelDropdownOpen ? 'rotate-180' : ''}`} 
                            />
                        </button>
                        
                        <AnimatePresence>
                            {isLevelDropdownOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute z-50 w-full mt-2 bg-surface border border-gray-200 rounded-xl shadow-xl overflow-hidden"
                                >
                                    <div className="max-h-64 overflow-y-auto py-2">
                                        {LEVELS.map(level => (
                                            <button
                                                key={level}
                                                onClick={() => { setSelectedLevel(level); setIsLevelDropdownOpen(false); }}
                                                className={`w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                                                    selectedLevel === level ? 'bg-primary/5 text-primary font-medium' : 'text-text-main'
                                                }`}
                                            >
                                                <span>{level}</span>
                                                {selectedLevel === level && <Check size={16} className="text-primary" />}
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
                
                {/* Unit Dropdown */}
                <div className="flex-1 max-w-xs" ref={unitDropdownRef}>
                    <label className="block text-sm font-medium text-text-sub mb-2">Unit</label>
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => { setIsUnitDropdownOpen(!isUnitDropdownOpen); setIsLevelDropdownOpen(false); }}
                            className="w-full flex items-center justify-between px-4 py-3 bg-surface border border-gray-200 rounded-xl text-left hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        >
                            <span className="text-text-main font-medium">{selectedUnit}</span>
                            <ChevronDown 
                                size={18} 
                                className={`text-text-sub transition-transform duration-200 ${isUnitDropdownOpen ? 'rotate-180' : ''}`} 
                            />
                        </button>
                        
                        <AnimatePresence>
                            {isUnitDropdownOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute z-50 w-full mt-2 bg-surface border border-gray-200 rounded-xl shadow-xl overflow-hidden"
                                >
                                    <div className="max-h-64 overflow-y-auto py-2">
                                        {UNITS.map(unit => (
                                            <button
                                                key={unit}
                                                onClick={() => { setSelectedUnit(unit); setIsUnitDropdownOpen(false); }}
                                                className={`w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                                                    selectedUnit === unit ? 'bg-primary/5 text-primary font-medium' : 'text-text-main'
                                                }`}
                                            >
                                                <span>{unit}</span>
                                                {selectedUnit === unit && <Check size={16} className="text-primary" />}
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">
                    {error}
                </div>
            )}

            {/* Loading State */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="animate-spin text-primary" size={40} />
                </div>
            ) : (
                <div className="space-y-8">
                    {/* Part 1: Word Reading */}
                    <div className="bg-surface rounded-2xl shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-100 bg-blue-50">
                            <div className="flex items-center gap-2">
                                <BookOpen size={20} className="text-blue-600" />
                                <h2 className="text-lg font-semibold text-blue-900">Part 1: 词汇朗读</h2>
                                <span className="ml-auto text-sm text-blue-600">{part1Questions.length} 题</span>
                            </div>
                        </div>
                        <div className="divide-y divide-gray-100">
                            {part1Questions.length > 0 ? (
                                part1Questions.map((q) => (
                                    <div key={q.id} className="p-4 hover:bg-gray-50 transition-colors">
                                        {editingId === q.id ? (
                                            <div className="space-y-3">
                                                <input
                                                    type="text"
                                                    value={editForm.question || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, question: e.target.value })}
                                                    className="input-field"
                                                    placeholder="单词/短语"
                                                />
                                                <input
                                                    type="text"
                                                    value={editForm.translation || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, translation: e.target.value })}
                                                    className="input-field"
                                                    placeholder="中文翻译"
                                                />
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleSaveEdit(q.id)}
                                                        className="px-3 py-1.5 bg-green-500 text-white rounded-lg text-sm flex items-center gap-1"
                                                    >
                                                        <Save size={14} /> 保存
                                                    </button>
                                                    <button
                                                        onClick={() => { setEditingId(null); setEditForm({}); }}
                                                        className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg text-sm flex items-center gap-1"
                                                    >
                                                        <X size={14} /> 取消
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex items-center gap-4">
                                                <span className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
                                                    {q.question_no}
                                                </span>
                                                {q.image_url && (
                                                    <img src={q.image_url} alt="" className="w-12 h-12 object-cover rounded-lg" />
                                                )}
                                                <div className="flex-1">
                                                    <p className="font-medium text-text-main">{q.question}</p>
                                                    {q.translation && (
                                                        <p className="text-sm text-text-sub">{q.translation}</p>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <label className="cursor-pointer">
                                                        <input
                                                            type="file"
                                                            accept="image/*"
                                                            className="hidden"
                                                            onChange={(e) => {
                                                                const file = e.target.files?.[0];
                                                                if (file) handleImageUpload(q.id, file);
                                                            }}
                                                        />
                                                        <span className="p-2 hover:bg-gray-100 rounded-lg transition-colors inline-flex">
                                                            {uploadingId === q.id ? (
                                                                <Loader2 size={16} className="animate-spin text-gray-500" />
                                                            ) : (
                                                                <Upload size={16} className="text-gray-500" />
                                                            )}
                                                        </span>
                                                    </label>
                                                    <button
                                                        onClick={() => handleEdit(q)}
                                                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                                    >
                                                        <Edit2 size={16} className="text-gray-500" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(q.id)}
                                                        className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                                                    >
                                                        <Trash2 size={16} className="text-red-500" />
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="p-8 text-center text-text-sub">
                                    暂无 Part 1 题目
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Part 2: Q&A */}
                    <div className="bg-surface rounded-2xl shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-100 bg-green-50">
                            <div className="flex items-center gap-2">
                                <BookOpen size={20} className="text-green-600" />
                                <h2 className="text-lg font-semibold text-green-900">Part 2: 问答表达</h2>
                                <span className="ml-auto text-sm text-green-600">{part2Questions.length} 题</span>
                            </div>
                        </div>
                        <div className="divide-y divide-gray-100">
                            {part2Questions.length > 0 ? (
                                part2Questions.map((q) => (
                                    <div key={q.id} className="p-4 hover:bg-gray-50 transition-colors">
                                        {editingId === q.id ? (
                                            <div className="space-y-3">
                                                <input
                                                    type="text"
                                                    value={editForm.question || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, question: e.target.value })}
                                                    className="input-field"
                                                    placeholder="问题"
                                                />
                                                <textarea
                                                    value={editForm.reference_answer || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, reference_answer: e.target.value })}
                                                    className="input-field min-h-[80px]"
                                                    placeholder="参考答案"
                                                />
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleSaveEdit(q.id)}
                                                        className="px-3 py-1.5 bg-green-500 text-white rounded-lg text-sm flex items-center gap-1"
                                                    >
                                                        <Save size={14} /> 保存
                                                    </button>
                                                    <button
                                                        onClick={() => { setEditingId(null); setEditForm({}); }}
                                                        className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg text-sm flex items-center gap-1"
                                                    >
                                                        <X size={14} /> 取消
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex items-start gap-4">
                                                <span className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-semibold text-sm shrink-0">
                                                    {q.question_no}
                                                </span>
                                                <div className="flex-1">
                                                    <p className="font-medium text-text-main">{q.question}</p>
                                                    {q.reference_answer && (
                                                        <p className="text-sm text-text-sub mt-1 bg-gray-50 p-2 rounded-lg">
                                                            参考答案: {q.reference_answer}
                                                        </p>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => handleEdit(q)}
                                                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                                    >
                                                        <Edit2 size={16} className="text-gray-500" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(q.id)}
                                                        className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                                                    >
                                                        <Trash2 size={16} className="text-red-500" />
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="p-8 text-center text-text-sub">
                                    暂无 Part 2 题目
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Create Modal */}
            {isCreating && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-lg mx-4 shadow-xl">
                        <h3 className="text-xl font-bold text-text-main mb-4">新增题目</h3>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-text-sub mb-2">题目类型</label>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setCreatePart(1)}
                                        className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                                            createPart === 1 
                                                ? 'bg-blue-500 text-white' 
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                        }`}
                                    >
                                        Part 1: 词汇朗读
                                    </button>
                                    <button
                                        onClick={() => setCreatePart(2)}
                                        className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                                            createPart === 2 
                                                ? 'bg-green-500 text-white' 
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                        }`}
                                    >
                                        Part 2: 问答表达
                                    </button>
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-sm font-medium text-text-sub mb-2">
                                    {createPart === 1 ? '单词/短语' : '问题'}
                                </label>
                                <input
                                    type="text"
                                    value={createForm.question || ''}
                                    onChange={(e) => setCreateForm({ ...createForm, question: e.target.value })}
                                    className="input-field"
                                    placeholder={createPart === 1 ? '输入单词或短语' : '输入问题'}
                                />
                            </div>
                            
                            {createPart === 1 && (
                                <div>
                                    <label className="block text-sm font-medium text-text-sub mb-2">中文翻译</label>
                                    <input
                                        type="text"
                                        value={createForm.translation || ''}
                                        onChange={(e) => setCreateForm({ ...createForm, translation: e.target.value })}
                                        className="input-field"
                                        placeholder="输入中文翻译"
                                    />
                                </div>
                            )}
                            
                            {createPart === 2 && (
                                <div>
                                    <label className="block text-sm font-medium text-text-sub mb-2">参考答案</label>
                                    <textarea
                                        value={createForm.reference_answer || ''}
                                        onChange={(e) => setCreateForm({ ...createForm, reference_answer: e.target.value })}
                                        className="input-field min-h-[100px]"
                                        placeholder="输入参考答案"
                                    />
                                </div>
                            )}
                        </div>
                        
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => { setIsCreating(false); setCreateForm({}); }}
                                className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleCreate}
                                className="flex-1 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors"
                            >
                                创建
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </DashboardLayout>
    );
};

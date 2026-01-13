import React, { useState, useEffect } from 'react';
import { questionsApi, type Question, type QuestionCreate } from '../api';
import Layout from '../components/Layout';

const LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'];
const UNITS = ['All', 'Unit 1-4', 'Unit 5-8'];

const QuestionsPage: React.FC = () => {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedLevel, setSelectedLevel] = useState<string>('L0');
    const [selectedUnit, setSelectedUnit] = useState<string>('All');

    // Modal state
    const [showModal, setShowModal] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
    const [formData, setFormData] = useState<QuestionCreate>({
        level: 'L0',
        unit: 'All',
        part: 1,
        question_no: 1,
        question: '',
        translation: '',
        reference_answer: '',
    });
    const [uploading, setUploading] = useState(false);

    useEffect(() => {
        loadQuestions();
    }, [selectedLevel, selectedUnit]);

    const loadQuestions = async () => {
        setLoading(true);
        try {
            const res = await questionsApi.list(selectedLevel, selectedUnit === 'All' ? undefined : selectedUnit);
            setQuestions(res.data);
        } catch (error) {
            console.error('Failed to load questions:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingQuestion(null);
        setFormData({
            level: selectedLevel,
            unit: selectedUnit,
            part: 1,
            question_no: questions.length + 1,
            question: '',
            translation: '',
            reference_answer: '',
        });
        setShowModal(true);
    };

    const handleEdit = (question: Question) => {
        setEditingQuestion(question);
        setFormData({
            level: question.level,
            unit: question.unit,
            part: question.part,
            question_no: question.question_no,
            question: question.question,
            translation: question.translation || '',
            reference_answer: question.reference_answer || '',
        });
        setShowModal(true);
    };

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除这道题目吗？')) return;
        try {
            await questionsApi.delete(id);
            loadQuestions();
        } catch (error) {
            alert('删除失败');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingQuestion) {
                await questionsApi.update(editingQuestion.id, {
                    question: formData.question,
                    translation: formData.translation,
                    reference_answer: formData.reference_answer,
                });
            } else {
                await questionsApi.create(formData);
            }
            setShowModal(false);
            loadQuestions();
        } catch (error) {
            alert('保存失败');
        }
    };

    const handleImageUpload = async (questionId: number, file: File) => {
        setUploading(true);
        try {
            const res = await questionsApi.uploadImage(questionId, file);
            if (res.data.success) {
                loadQuestions();
            }
        } catch (error) {
            alert('图片上传失败');
        } finally {
            setUploading(false);
        }
    };

    const triggerImageUpload = (questionId: number) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (file) {
                handleImageUpload(questionId, file);
            }
        };
        input.click();
    };

    const pageActions = (
        <button 
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover shadow-sm transition-all shadow-primary/20"
            onClick={handleAdd}
        >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            添加题目
        </button>
    );

    return (
        <Layout title="题目管理" showBack actions={pageActions}>
            <div className="space-y-6">
                {/* Filters */}
                <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-wrap gap-4 items-center">
                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-gray-700">级别:</label>
                        <select 
                            value={selectedLevel} 
                            onChange={(e) => setSelectedLevel(e.target.value)}
                            className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none font-medium"
                        >
                        {LEVELS.map(level => (
                            <option key={level} value={level}>{level}</option>
                        ))}
                    </select>
                </div>
                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-gray-700">单元:</label>
                        <select 
                            value={selectedUnit} 
                            onChange={(e) => setSelectedUnit(e.target.value)}
                            className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none font-medium"
                        >
                        {UNITS.map(unit => (
                            <option key={unit} value={unit}>{unit}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
                        <p className="text-gray-500">题目加载中...</p>
                    </div>
            ) : (
                    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                        <th className="px-6 py-4 font-semibold text-gray-900 w-20">类型</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900 w-20">序号</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900 min-w-[200px]">题目</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900">中文翻译</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900 w-24">图片</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900 min-w-[200px]">参考答案</th>
                                        <th className="px-6 py-4 font-semibold text-gray-900 w-32 text-right">操作</th>
                            </tr>
                        </thead>
                                <tbody className="divide-y divide-gray-50">
                            {questions.map((q) => (
                                        <tr key={q.id} className={`hover:bg-gray-50/50 transition-colors ${!q.is_active ? 'opacity-50' : ''}`}>
                                            <td className="px-6 py-4">
                                                <span className={`px-2 py-1 rounded text-xs font-bold border ${
                                                    q.part === 1 
                                                        ? 'bg-blue-50 text-blue-700 border-blue-100' 
                                                        : 'bg-purple-50 text-purple-700 border-purple-100'
                                                }`}>
                                                    {q.part === 1 ? '词汇' : '问答'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 font-mono text-gray-500">{q.question_no}</td>
                                            <td className="px-6 py-4 font-medium text-gray-900">{q.question}</td>
                                            <td className="px-6 py-4 text-gray-500">{q.translation || '-'}</td>
                                            <td className="px-6 py-4">
                                        {q.image_url ? (
                                                    <div className="relative group w-10 h-10">
                                            <img
                                                src={q.image_url}
                                                alt={q.question}
                                                            className="w-10 h-10 object-cover rounded-lg border border-gray-200 cursor-pointer"
                                                onClick={() => triggerImageUpload(q.id)}
                                                        />
                                                        <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer pointer-events-none">
                                                            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                            </svg>
                                                        </div>
                                                    </div>
                                        ) : (
                                            <button
                                                        className="w-10 h-10 rounded-lg border border-dashed border-gray-300 flex items-center justify-center text-gray-400 hover:text-primary hover:border-primary hover:bg-primary/5 transition-all"
                                                onClick={() => triggerImageUpload(q.id)}
                                                disabled={uploading}
                                                        title="上传图片"
                                            >
                                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                                        </svg>
                                            </button>
                                        )}
                                    </td>
                                            <td className="px-6 py-4 text-gray-500 max-w-xs truncate" title={q.reference_answer || ''}>
                                                {q.reference_answer || '-'}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button 
                                                        className="p-1.5 text-gray-400 hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
                                                        onClick={() => handleEdit(q)}
                                                        title="编辑"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                        </svg>
                                                    </button>
                                                    <button 
                                                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                        onClick={() => handleDelete(q.id)}
                                                        title="删除"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                        </svg>
                                                    </button>
                                                </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                        </div>
                    {questions.length === 0 && (
                            <div className="text-center py-12">
                                <p className="text-gray-400 mb-2">暂无题目数据</p>
                                <button onClick={handleAdd} className="text-primary text-sm font-medium hover:underline">
                                    点击添加第一道题目
                                </button>
                            </div>
                    )}
                </div>
            )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
                        <div className="p-6 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-lg font-bold text-gray-900">{editingQuestion ? '编辑题目' : '添加题目'}</h2>
                        </div>
                        
                        <div className="p-6 overflow-y-auto flex-1">
                            <form id="questionForm" onSubmit={handleSubmit} className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">级别</label>
                                    <select
                                            className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                        value={formData.level}
                                        onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                                        disabled={!!editingQuestion}
                                    >
                                        {LEVELS.map(level => (
                                            <option key={level} value={level}>{level}</option>
                                        ))}
                                    </select>
                                </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">单元</label>
                                    <select
                                            className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                        value={formData.unit}
                                        onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                                        disabled={!!editingQuestion}
                                    >
                                        {UNITS.map(unit => (
                                            <option key={unit} value={unit}>{unit}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">类型</label>
                                    <select
                                            className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                        value={formData.part}
                                        onChange={(e) => setFormData({ ...formData, part: parseInt(e.target.value) })}
                                        disabled={!!editingQuestion}
                                    >
                                        <option value={1}>Part 1 (词汇)</option>
                                        <option value={2}>Part 2 (问答)</option>
                                    </select>
                                </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">序号</label>
                                    <input
                                        type="number"
                                            className="w-full px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                        value={formData.question_no}
                                        onChange={(e) => setFormData({ ...formData, question_no: parseInt(e.target.value) })}
                                        disabled={!!editingQuestion}
                                        min={1}
                                    />
                                </div>
                            </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1.5">题目内容 *</label>
                                <input
                                    type="text"
                                        className="w-full px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                    value={formData.question}
                                    onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                                    required
                                    placeholder={formData.part === 1 ? '输入单词，如: apple' : '输入问题，如: What is your name?'}
                                />
                            </div>

                            {formData.part === 1 && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">中文翻译</label>
                                    <input
                                        type="text"
                                            className="w-full px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                                        value={formData.translation}
                                        onChange={(e) => setFormData({ ...formData, translation: e.target.value })}
                                        placeholder="输入中文翻译，如: 苹果"
                                    />
                                </div>
                            )}

                            {formData.part === 2 && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1.5">参考答案</label>
                                    <textarea
                                            className="w-full px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none min-h-[100px]"
                                        value={formData.reference_answer}
                                        onChange={(e) => setFormData({ ...formData, reference_answer: e.target.value })}
                                            placeholder="输入参考答案或要点..."
                                    />
                                </div>
                            )}
                            </form>
                        </div>

                        <div className="p-6 border-t border-gray-100 flex gap-3 bg-gray-50/50">
                            <button 
                                type="button" 
                                className="flex-1 px-4 py-2.5 border border-gray-200 text-gray-700 font-medium rounded-xl hover:bg-white hover:border-gray-300 transition-all"
                                onClick={() => setShowModal(false)}
                            >
                                取消
                            </button>
                            <button 
                                type="submit" 
                                form="questionForm"
                                className="flex-1 px-4 py-2.5 bg-primary text-white font-bold rounded-xl hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all"
                            >
                                保存
                            </button>
                            </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default QuestionsPage;

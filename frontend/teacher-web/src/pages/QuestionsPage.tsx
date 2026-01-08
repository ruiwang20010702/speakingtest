import React, { useState, useEffect } from 'react';
import { questionsApi, type Question, type QuestionCreate } from '../api';
import './QuestionsPage.css';

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

    return (
        <div className="questions-page">
            <div className="questions-header">
                <h1>题目管理</h1>
                <button className="btn-primary" onClick={handleAdd}>+ 添加题目</button>
            </div>

            <div className="filters">
                <div className="filter-group">
                    <label>Level:</label>
                    <select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)}>
                        {LEVELS.map(level => (
                            <option key={level} value={level}>{level}</option>
                        ))}
                    </select>
                </div>
                <div className="filter-group">
                    <label>Unit:</label>
                    <select value={selectedUnit} onChange={(e) => setSelectedUnit(e.target.value)}>
                        {UNITS.map(unit => (
                            <option key={unit} value={unit}>{unit}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="loading">加载中...</div>
            ) : (
                <div className="questions-table-wrapper">
                    <table className="questions-table">
                        <thead>
                            <tr>
                                <th>Part</th>
                                <th>序号</th>
                                <th>题目</th>
                                <th>翻译</th>
                                <th>图片</th>
                                <th>参考答案</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {questions.map((q) => (
                                <tr key={q.id} className={!q.is_active ? 'inactive' : ''}>
                                    <td>{q.part === 1 ? '词汇' : '问答'}</td>
                                    <td>{q.question_no}</td>
                                    <td className="question-text">{q.question}</td>
                                    <td>{q.translation || '-'}</td>
                                    <td className="image-cell">
                                        {q.image_url ? (
                                            <img
                                                src={q.image_url}
                                                alt={q.question}
                                                className="question-image"
                                                onClick={() => triggerImageUpload(q.id)}
                                                title="点击更换图片"
                                            />
                                        ) : (
                                            <button
                                                className="btn-upload"
                                                onClick={() => triggerImageUpload(q.id)}
                                                disabled={uploading}
                                            >
                                                上传
                                            </button>
                                        )}
                                    </td>
                                    <td className="answer-text">{q.reference_answer || '-'}</td>
                                    <td className="actions">
                                        <button className="btn-edit" onClick={() => handleEdit(q)}>编辑</button>
                                        <button className="btn-delete" onClick={() => handleDelete(q.id)}>删除</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {questions.length === 0 && (
                        <div className="empty-state">暂无题目，点击"添加题目"创建</div>
                    )}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <h2>{editingQuestion ? '编辑题目' : '添加题目'}</h2>
                        <form onSubmit={handleSubmit}>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Level</label>
                                    <select
                                        value={formData.level}
                                        onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                                        disabled={!!editingQuestion}
                                    >
                                        {LEVELS.map(level => (
                                            <option key={level} value={level}>{level}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Unit</label>
                                    <select
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
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Part</label>
                                    <select
                                        value={formData.part}
                                        onChange={(e) => setFormData({ ...formData, part: parseInt(e.target.value) })}
                                        disabled={!!editingQuestion}
                                    >
                                        <option value={1}>Part 1 (词汇)</option>
                                        <option value={2}>Part 2 (问答)</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>序号</label>
                                    <input
                                        type="number"
                                        value={formData.question_no}
                                        onChange={(e) => setFormData({ ...formData, question_no: parseInt(e.target.value) })}
                                        disabled={!!editingQuestion}
                                        min={1}
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>题目 *</label>
                                <input
                                    type="text"
                                    value={formData.question}
                                    onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                                    required
                                    placeholder={formData.part === 1 ? '输入单词，如: apple' : '输入问题，如: What is your name?'}
                                />
                            </div>
                            {formData.part === 1 && (
                                <div className="form-group">
                                    <label>中文翻译</label>
                                    <input
                                        type="text"
                                        value={formData.translation}
                                        onChange={(e) => setFormData({ ...formData, translation: e.target.value })}
                                        placeholder="输入中文翻译，如: 苹果"
                                    />
                                </div>
                            )}
                            {formData.part === 2 && (
                                <div className="form-group">
                                    <label>参考答案</label>
                                    <textarea
                                        value={formData.reference_answer}
                                        onChange={(e) => setFormData({ ...formData, reference_answer: e.target.value })}
                                        placeholder="输入参考答案"
                                        rows={3}
                                    />
                                </div>
                            )}
                            <div className="modal-actions">
                                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>取消</button>
                                <button type="submit" className="btn-primary">保存</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default QuestionsPage;

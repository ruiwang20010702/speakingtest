import React, { useState, useEffect } from 'react';
import { X, Loader2, Star, Plus, Trash2, Save, RotateCcw, AlertCircle } from 'lucide-react';
import { 
  testsApi, 
  type TestReport, 
  type ReportOverrideRequest,
  type RadarScoreOverride,
  type Part1WordOverride,
  type Part2ItemOverride,
  type SuggestionOverride
} from '../../../api';

interface EditReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  testId: number;
  report: TestReport;
  onSaved: () => void;
}

type TabKey = 'basic' | 'radar' | 'part1' | 'part2' | 'suggestion';

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'basic', label: '基础信息', icon: '📋' },
  { key: 'radar', label: '五维雷达', icon: '📊' },
  { key: 'part1', label: 'Part1 词汇', icon: '📖' },
  { key: 'part2', label: 'Part2 问答', icon: '💬' },
  { key: 'suggestion', label: '学习建议', icon: '💡' },
];

export const EditReportModal: React.FC<EditReportModalProps> = ({
  isOpen,
  onClose,
  testId,
  report,
  onSaved,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('basic');
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasOverride, setHasOverride] = useState(false);

  // Form state - Basic Info
  const [studentName, setStudentName] = useState('');
  const [level, setLevel] = useState('');
  const [unit, setUnit] = useState('');
  const [part1Score, setPart1Score] = useState(0);
  const [part2Score, setPart2Score] = useState(0);
  const [totalScore, setTotalScore] = useState(0);
  const [starLevel, setStarLevel] = useState(1);

  // Form state - Radar
  const [radar, setRadar] = useState<RadarScoreOverride>({
    fluency: 0,
    pronunciation: 0,
    confidence: 0,
    vocabulary: 0,
    sentence: 0,
  });

  // Form state - Part1 Words
  const [part1Words, setPart1Words] = useState<Part1WordOverride[]>([]);

  // Form state - Part2 Items
  const [part2Items, setPart2Items] = useState<Part2ItemOverride[]>([]);

  // Form state - Suggestion
  const [suggestion, setSuggestion] = useState<SuggestionOverride>({
    highlights: [],
    weaknesses: [],
    suggestions: [],
  });

  // Load existing override data
  useEffect(() => {
    if (isOpen) {
      loadOverrideData();
    }
  }, [isOpen, testId]);

  const loadOverrideData = async () => {
    setLoading(true);
    try {
      const overrideRes = await testsApi.getReportOverride(testId);
      const override = overrideRes.data.override || {};
      const original = overrideRes.data.original;
      setHasOverride(overrideRes.data.has_override);

      // Initialize with original data (from backend), then apply override
      // Priority: override > original > fallback
      setStudentName(override.student_name || original?.student_name || report.student_name || '');
      setLevel(override.level || original?.level || report.level || '');
      setUnit(override.unit || original?.unit || report.unit || '');
      setPart1Score(override.part1_score ?? original?.part1_score ?? report.part1_score ?? 0);
      setPart2Score(override.part2_score ?? original?.part2_score ?? report.part2_score ?? 0);
      setTotalScore(override.total_score ?? original?.total_score ?? report.total_score ?? 0);
      setStarLevel(override.star_level ?? original?.star_level ?? report.star_level ?? 3);

      // Radar - use override > original > fallback
      setRadar({
        fluency: override.radar?.fluency ?? original?.radar?.fluency ?? 70,
        pronunciation: override.radar?.pronunciation ?? original?.radar?.pronunciation ?? 70,
        confidence: override.radar?.confidence ?? original?.radar?.confidence ?? 70,
        vocabulary: override.radar?.vocabulary ?? original?.radar?.vocabulary ?? 70,
        sentence: override.radar?.sentence ?? original?.radar?.sentence ?? 70,
      });

      // Part1 Words - use override > original
      if (override.part1_words?.length) {
        setPart1Words(override.part1_words);
      } else if (original?.part1_words?.length) {
        setPart1Words(original.part1_words);
      } else {
        setPart1Words([]);
      }

      // Part2 Items - use override > original > report
      if (override.part2_items?.length) {
        setPart2Items(override.part2_items);
      } else if (original?.part2_items?.length) {
        setPart2Items(original.part2_items);
      } else if (report.part2_items?.length) {
        setPart2Items(report.part2_items.map(item => ({
          question_no: item.question_no,
          score: item.score,
          feedback: item.feedback || '',
          evidence: item.evidence || '',
        })));
      } else {
        setPart2Items([]);
      }

      // Suggestion - use override > original
      setSuggestion({
        highlights: override.suggestion?.highlights || original?.suggestion?.highlights || [],
        weaknesses: override.suggestion?.weaknesses || original?.suggestion?.weaknesses || [],
        suggestions: override.suggestion?.suggestions || original?.suggestion?.suggestions || [],
      });

    } catch (err) {
      console.error('Failed to load override:', err);
    } finally {
      setLoading(false);
    }
  };

  // Auto-calculate total score
  useEffect(() => {
    const avg = (part1Score + part2Score) / 2;
    setTotalScore(Math.round(avg * 10) / 10);
  }, [part1Score, part2Score]);

  const handleSave = async () => {
    setSaving(true);
    setError('');

    try {
      const overrideData: ReportOverrideRequest = {
        student_name: studentName,
        level,
        unit,
        part1_score: part1Score,
        part2_score: part2Score,
        total_score: totalScore,
        star_level: starLevel,
        radar,
        part1_words: part1Words.length > 0 ? part1Words : undefined,
        part2_items: part2Items.length > 0 ? part2Items : undefined,
        suggestion: {
          highlights: suggestion.highlights,
          weaknesses: suggestion.weaknesses,
          suggestions: suggestion.suggestions,
        },
      };

      await testsApi.updateReport(testId, overrideData);
      onSaved();
      onClose();
    } catch (err: any) {
      console.error('Failed to save:', err);
      setError(err.response?.data?.detail || '保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('确定要重置为 AI 原始数据吗？所有手动编辑将丢失。')) {
      return;
    }
    
    setResetting(true);
    setError('');
    try {
      await testsApi.resetReportOverride(testId);
      onSaved();
      onClose();
    } catch (err: any) {
      console.error('Failed to reset:', err);
      setError(err.response?.data?.detail || '重置失败');
    } finally {
      setResetting(false);
    }
  };

  // Helper functions for list editing (reserved for future use)
  const _addListItem = (setter: React.Dispatch<React.SetStateAction<string[]>>) => {
    setter(prev => [...prev, '']);
  };

  const _updateListItem = (
    index: number,
    value: string,
    setter: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    setter(prev => prev.map((item, i) => (i === index ? value : item)));
  };

  const _removeListItem = (
    index: number,
    setter: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    setter(prev => prev.filter((_, i) => i !== index));
  };

  // Suppress unused warnings (these are helper functions for future use)
  void _addListItem;
  void _updateListItem;
  void _removeListItem;

  // Part1 word helpers
  const addPart1Word = () => {
    setPart1Words(prev => [...prev, { text: '', status: 'perfect' as const, score: 100 }]);
  };

  const updatePart1Word = (index: number, field: keyof Part1WordOverride, value: any) => {
    setPart1Words(prev => prev.map((w, i) => i === index ? { ...w, [field]: value } : w));
  };

  const removePart1Word = (index: number) => {
    setPart1Words(prev => prev.filter((_, i) => i !== index));
  };

  // Part2 item helpers
  const addPart2Item = () => {
    const nextNo = part2Items.length > 0 
      ? Math.max(...part2Items.map(i => i.question_no)) + 1 
      : 1;
    setPart2Items(prev => [...prev, { question_no: nextNo, score: 2, feedback: '', evidence: '' }]);
  };

  const updatePart2Item = (index: number, field: keyof Part2ItemOverride, value: any) => {
    setPart2Items(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item));
  };

  const removePart2Item = (index: number) => {
    setPart2Items(prev => prev.filter((_, i) => i !== index));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-text-main">编辑报告内容</h2>
            {hasOverride && (
              <span className="px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 rounded">
                已修改
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 overflow-x-auto flex-shrink-0">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-shrink-0 px-5 py-4 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-text-sub hover:text-text-main hover:bg-slate-50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-primary" size={32} />
            </div>
          ) : (
            <>
              {/* Basic Info Tab */}
              {activeTab === 'basic' && (
                <div className="space-y-6">
                  {/* Student Name */}
                  <div>
                    <label className="block text-sm font-medium text-text-main mb-2">学生姓名</label>
                    <input
                      type="text"
                      value={studentName}
                      onChange={e => setStudentName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>

                  {/* Level & Unit */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-text-main mb-2">级别</label>
                      <input
                        type="text"
                        value={level}
                        onChange={e => setLevel(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-main mb-2">单元</label>
                      <input
                        type="text"
                        value={unit}
                        onChange={e => setUnit(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                      />
                    </div>
                  </div>

                  {/* Scores */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-text-main mb-2">Part1 分数</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={part1Score}
                          onChange={e => setPart1Score(Number(e.target.value))}
                          className="flex-1 accent-primary"
                        />
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={part1Score}
                          onChange={e => setPart1Score(Math.min(100, Math.max(0, Number(e.target.value))))}
                          className="w-16 px-2 py-1 border border-gray-200 rounded text-center font-mono"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-main mb-2">Part2 分数</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={part2Score}
                          onChange={e => setPart2Score(Number(e.target.value))}
                          className="flex-1 accent-primary"
                        />
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={part2Score}
                          onChange={e => setPart2Score(Math.min(100, Math.max(0, Number(e.target.value))))}
                          className="w-16 px-2 py-1 border border-gray-200 rounded text-center font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Total Score */}
                  <div>
                    <label className="block text-sm font-medium text-text-main mb-2">
                      总分 <span className="text-text-sub font-normal">(自动计算)</span>
                    </label>
                    <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-primary to-secondary transition-all"
                        style={{ width: `${totalScore}%` }}
                      />
                    </div>
                    <p className="text-right text-lg font-bold text-primary mt-1">{totalScore}</p>
                  </div>

                  {/* Star Level */}
                  <div>
                    <label className="block text-sm font-medium text-text-main mb-2">星级评定</label>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map(lvl => (
                        <button
                          key={lvl}
                          onClick={() => setStarLevel(lvl)}
                          className={`p-1 transition-colors ${
                            lvl <= starLevel ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'
                          }`}
                        >
                          <Star size={28} fill={lvl <= starLevel ? 'currentColor' : 'none'} />
                        </button>
                      ))}
                      <span className="ml-3 text-lg font-bold">{starLevel} 星</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Radar Tab */}
              {activeTab === 'radar' && (
                <div className="space-y-6">
                  <p className="text-sm text-text-sub">调整五维雷达图的各项分数（0-100）</p>
                  
                  {[
                    { key: 'fluency' as const, label: '流利度', icon: '🎯' },
                    { key: 'pronunciation' as const, label: '发音', icon: '🗣️' },
                    { key: 'confidence' as const, label: '自信度', icon: '💪' },
                    { key: 'vocabulary' as const, label: '词汇', icon: '📚' },
                    { key: 'sentence' as const, label: '整句输出', icon: '📝' },
                  ].map(dim => (
                    <div key={dim.key}>
                      <label className="block text-sm font-medium text-text-main mb-2">
                        {dim.icon} {dim.label}
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={radar[dim.key] || 0}
                          onChange={e => setRadar(prev => ({ ...prev, [dim.key]: Number(e.target.value) }))}
                          className="flex-1 accent-primary"
                        />
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={radar[dim.key] || 0}
                          onChange={e => setRadar(prev => ({ 
                            ...prev, 
                            [dim.key]: Math.min(100, Math.max(0, Number(e.target.value))) 
                          }))}
                          className="w-16 px-2 py-1 border border-gray-200 rounded text-center font-mono"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Part1 Words Tab */}
              {activeTab === 'part1' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-text-sub">编辑 Part1 朗读单词列表</p>
                    <button
                      onClick={addPart1Word}
                      className="text-sm text-primary hover:text-primary-hover flex items-center gap-1"
                    >
                      <Plus size={16} /> 添加单词
                    </button>
                  </div>

                  {part1Words.length === 0 ? (
                    <div className="text-center py-8 text-text-sub bg-slate-50 rounded-lg">
                      暂无单词数据，点击"添加单词"开始编辑
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {part1Words.map((word, index) => (
                        <div key={index} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                          <input
                            type="text"
                            value={word.text}
                            onChange={e => updatePart1Word(index, 'text', e.target.value)}
                            placeholder="单词"
                            className="flex-1 px-3 py-1.5 border border-gray-200 rounded text-sm"
                          />
                          <select
                            value={word.status}
                            onChange={e => updatePart1Word(index, 'status', e.target.value)}
                            className="px-3 py-1.5 border border-gray-200 rounded text-sm"
                          >
                            <option value="perfect">✅ 完美</option>
                            <option value="unclear">⚠️ 模糊</option>
                            <option value="failed">❌ 错误</option>
                          </select>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={word.score || 0}
                            onChange={e => updatePart1Word(index, 'score', Number(e.target.value))}
                            className="w-16 px-2 py-1.5 border border-gray-200 rounded text-center font-mono text-sm"
                          />
                          <button
                            onClick={() => removePart1Word(index)}
                            className="p-1.5 text-gray-400 hover:text-red-500"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Part2 Items Tab */}
              {activeTab === 'part2' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-text-sub">编辑 Part2 问答详情</p>
                    <button
                      onClick={addPart2Item}
                      className="text-sm text-primary hover:text-primary-hover flex items-center gap-1"
                    >
                      <Plus size={16} /> 添加题目
                    </button>
                  </div>

                  {part2Items.length === 0 ? (
                    <div className="text-center py-8 text-text-sub bg-slate-50 rounded-lg">
                      暂无题目数据
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {part2Items.map((item, index) => (
                        <div key={index} className="p-4 bg-slate-50 rounded-lg space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-gray-500">Q{item.question_no}</span>
                            <div className="flex items-center gap-2">
                              <select
                                value={item.score}
                                onChange={e => updatePart2Item(index, 'score', Number(e.target.value))}
                                className={`px-3 py-1 rounded text-sm font-medium ${
                                  item.score === 2 ? 'bg-emerald-100 text-emerald-700' :
                                  item.score === 1 ? 'bg-amber-100 text-amber-700' :
                                  'bg-rose-100 text-rose-700'
                                }`}
                              >
                                <option value={2}>S - 优秀</option>
                                <option value={1}>A - 良好</option>
                                <option value={0}>B - 需努力</option>
                              </select>
                              <button
                                onClick={() => removePart2Item(index)}
                                className="p-1.5 text-gray-400 hover:text-red-500"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>
                          <div>
                            <label className="text-xs text-text-sub">学生回答</label>
                            <textarea
                              value={item.evidence || ''}
                              onChange={e => updatePart2Item(index, 'evidence', e.target.value)}
                              placeholder="学生的回答内容..."
                              rows={2}
                              className="w-full mt-1 px-3 py-2 border border-gray-200 rounded text-sm resize-none"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-text-sub">AI 反馈</label>
                            <textarea
                              value={item.feedback || ''}
                              onChange={e => updatePart2Item(index, 'feedback', e.target.value)}
                              placeholder="对学生回答的评价..."
                              rows={2}
                              className="w-full mt-1 px-3 py-2 border border-gray-200 rounded text-sm resize-none"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Suggestion Tab */}
              {activeTab === 'suggestion' && (
                <div className="space-y-6">
                  {/* Highlights */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-text-main">✨ 表现亮点</label>
                      <button
                        onClick={() => setSuggestion(prev => ({
                          ...prev,
                          highlights: [...(prev.highlights || []), '']
                        }))}
                        className="text-xs text-primary flex items-center gap-1"
                      >
                        <Plus size={14} /> 添加
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(suggestion.highlights || []).map((item, index) => (
                        <div key={index} className="flex gap-2">
                          <input
                            type="text"
                            value={item}
                            onChange={e => {
                              const newHighlights = [...(suggestion.highlights || [])];
                              newHighlights[index] = e.target.value;
                              setSuggestion(prev => ({ ...prev, highlights: newHighlights }));
                            }}
                            placeholder="输入亮点..."
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                          />
                          <button
                            onClick={() => {
                              const newHighlights = (suggestion.highlights || []).filter((_, i) => i !== index);
                              setSuggestion(prev => ({ ...prev, highlights: newHighlights }));
                            }}
                            className="p-2 text-gray-400 hover:text-red-500"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Weaknesses */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-text-main">💪 待提升点</label>
                      <button
                        onClick={() => setSuggestion(prev => ({
                          ...prev,
                          weaknesses: [...(prev.weaknesses || []), '']
                        }))}
                        className="text-xs text-primary flex items-center gap-1"
                      >
                        <Plus size={14} /> 添加
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(suggestion.weaknesses || []).map((item, index) => (
                        <div key={index} className="flex gap-2">
                          <input
                            type="text"
                            value={item}
                            onChange={e => {
                              const newWeaknesses = [...(suggestion.weaknesses || [])];
                              newWeaknesses[index] = e.target.value;
                              setSuggestion(prev => ({ ...prev, weaknesses: newWeaknesses }));
                            }}
                            placeholder="输入待提升点..."
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                          />
                          <button
                            onClick={() => {
                              const newWeaknesses = (suggestion.weaknesses || []).filter((_, i) => i !== index);
                              setSuggestion(prev => ({ ...prev, weaknesses: newWeaknesses }));
                            }}
                            className="p-2 text-gray-400 hover:text-red-500"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Suggestions */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-text-main">📝 学习建议</label>
                      <button
                        onClick={() => setSuggestion(prev => ({
                          ...prev,
                          suggestions: [...(prev.suggestions || []), '']
                        }))}
                        className="text-xs text-primary flex items-center gap-1"
                      >
                        <Plus size={14} /> 添加
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(suggestion.suggestions || []).map((item, index) => (
                        <div key={index} className="flex gap-2">
                          <input
                            type="text"
                            value={item}
                            onChange={e => {
                              const newSuggestions = [...(suggestion.suggestions || [])];
                              newSuggestions[index] = e.target.value;
                              setSuggestion(prev => ({ ...prev, suggestions: newSuggestions }));
                            }}
                            placeholder="输入建议..."
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                          />
                          <button
                            onClick={() => {
                              const newSuggestions = (suggestion.suggestions || []).filter((_, i) => i !== index);
                              setSuggestion(prev => ({ ...prev, suggestions: newSuggestions }));
                            }}
                            className="p-2 text-gray-400 hover:text-red-500"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600 mb-3">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              disabled={resetting || !hasOverride}
              className="px-4 py-2 text-text-sub hover:text-red-600 flex items-center gap-2 disabled:opacity-50 transition-colors"
            >
              {resetting ? <Loader2 className="animate-spin" size={16} /> : <RotateCcw size={16} />}
              <span>重置为原始数据</span>
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                disabled={saving}
                className="px-4 py-2 text-text-sub hover:text-text-main transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary flex items-center gap-2 px-5 py-2"
              >
                {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                <span>保存修改</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

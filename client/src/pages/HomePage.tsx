/**
 * 首页 - 学生信息和测试选择
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLevels } from '../services/api';
import type { Level } from '../types';
import './HomePage.css';

export default function HomePage() {
    const navigate = useNavigate();
    const [studentName, setStudentName] = useState('');
    const [level, setLevel] = useState('level1');
    const [unit, setUnit] = useState('unit1-3');
    const [levels, setLevels] = useState<Level[]>([]);

    useEffect(() => {
        loadLevels();
    }, []);

    const loadLevels = async () => {
        try {
            const data = await getLevels();
            setLevels(data.levels);
        } catch (error) {
            console.error('Failed to load levels:', error);
        }
    };

    const handleStart = () => {
        if (!studentName.trim()) {
            alert('请输入学生姓名');
            return;
        }

        navigate(`/test?student=${encodeURIComponent(studentName)}&level=${level}&unit=${unit}`);
    };

    return (
        <div className="home-page">
            <div className="container">
                <div className="card home-card">
                    <h1>🎤 学生口语测试系统</h1>
                    <p className="subtitle">基于 Gemini 2.5 Flash AI 的智能评分系统</p>

                    <div className="form-group">
                        <label>学生姓名</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="请输入姓名"
                            value={studentName}
                            onChange={(e) => setStudentName(e.target.value)}
                            autoFocus
                        />
                    </div>

                    <div className="form-group">
                        <label>选择级别</label>
                        <select
                            className="input"
                            value={level}
                            onChange={(e) => setLevel(e.target.value)}
                        >
                            {levels.map(lv => (
                                <option key={lv.id} value={lv.id}>{lv.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>选择单元</label>
                        <select
                            className="input"
                            value={unit}
                            onChange={(e) => setUnit(e.target.value)}
                        >
                            <option value="unit1-3">Unit 1-3</option>
                            <option value="unit4-8">Unit 4-8</option>
                        </select>
                    </div>

                    <button onClick={handleStart} className="btn btn-primary btn-large">
                        开始测试 →
                    </button>

                    {studentName && (
                        <div className="history-link">
                            <button
                                onClick={() => navigate(`/history?student=${encodeURIComponent(studentName)}`)}
                                className="btn btn-secondary"
                            >
                                查看 {studentName} 的历史记录
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

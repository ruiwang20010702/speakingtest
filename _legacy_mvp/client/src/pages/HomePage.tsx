/**
 * 首页 - 学生信息和测试选择 (51Talk 新设计)
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLevels } from '../services/api';
import type { Level } from '../types';
import { User, Layers, BookOpen, History } from 'lucide-react';
import logoImage from '../assets/51talk-logo.png';

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

    const isFormValid = studentName.trim() && level && unit;

    return (
        <div className="min-h-screen relative overflow-hidden">
            {/* Blue Background with decorative elements */}
            <div className="absolute inset-0 bg-[#00B4EE]">
                {/* Top left yellow circle */}
                <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                {/* Bottom left white cloud */}
                <div className="absolute bottom-0 left-0 w-48 h-32">
                    <div className="absolute bottom-4 left-0 w-24 h-24 bg-white rounded-full -translate-x-1/3" />
                    <div className="absolute bottom-8 left-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute bottom-12 left-6 w-16 h-16 bg-white rounded-full" />
                </div>
                {/* Top right white cloud */}
                <div className="absolute top-0 right-0 w-48 h-32">
                    <div className="absolute top-4 right-0 w-24 h-24 bg-white rounded-full translate-x-1/3" />
                    <div className="absolute top-8 right-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute top-12 right-6 w-16 h-16 bg-white rounded-full" />
                </div>
                {/* Bottom right yellow decoration */}
                <div className="absolute bottom-0 right-0 w-40 h-40 bg-[#FDE700] translate-x-1/4 translate-y-1/4" style={{ clipPath: 'polygon(0 100%, 100% 100%, 100% 0)' }} />
            </div>

            {/* Content */}
            <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    <div className="bg-white/95 backdrop-blur rounded-3xl shadow-2xl p-8">
                        {/* Logo */}
                        <div className="text-center mb-6">
                            <img 
                                src={logoImage} 
                                alt="51Talk Logo" 
                                className="h-16 mx-auto rounded-2xl shadow-lg"
                            />
                        </div>

                        {/* Header */}
                        <div className="text-center mb-8">
                            <h1 className="text-2xl font-semibold text-gray-900 mb-2">口语测试</h1>
                            <p className="text-gray-500">请填写您的信息开始测试</p>
                        </div>

                        {/* Form */}
                        <form onSubmit={(e) => { e.preventDefault(); handleStart(); }} className="space-y-6">
                            {/* Student Name */}
                            <div>
                                <label htmlFor="name" className="block text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <User className="w-4 h-4 text-[#00B4EE]" />
                                        <span>学生姓名</span>
                                    </div>
                                </label>
                        <input
                            type="text"
                                    id="name"
                            value={studentName}
                            onChange={(e) => setStudentName(e.target.value)}
                                    placeholder="请输入您的姓名"
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00B4EE] focus:border-transparent transition-all"
                            autoFocus
                        />
                    </div>

                            {/* Level Selection */}
                            <div>
                                <label htmlFor="level" className="block text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <Layers className="w-4 h-4 text-[#00B4EE]" />
                                        <span>选择级别</span>
                                    </div>
                                </label>
                        <select
                                    id="level"
                            value={level}
                            onChange={(e) => setLevel(e.target.value)}
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00B4EE] focus:border-transparent transition-all appearance-none cursor-pointer"
                        >
                                    {levels.map((lv) => (
                                        <option key={lv.id} value={lv.id}>
                                            {lv.name}
                                        </option>
                            ))}
                        </select>
                    </div>

                            {/* Unit Selection */}
                            <div>
                                <label htmlFor="unit" className="block text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <BookOpen className="w-4 h-4 text-[#00B4EE]" />
                                        <span>选择单元</span>
                                    </div>
                                </label>
                        <select
                                    id="unit"
                            value={unit}
                            onChange={(e) => setUnit(e.target.value)}
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00B4EE] focus:border-transparent transition-all appearance-none cursor-pointer"
                        >
                            <option value="unit1-3">Unit 1-3</option>
                            <option value="unit4-8">Unit 4-8</option>
                        </select>
                    </div>

                            {/* Submit Button */}
                            <button
                                type="submit"
                                disabled={!isFormValid}
                                className="w-full py-4 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none active:scale-[0.98]"
                            >
                                开始测试
                            </button>
                        </form>

                        {/* History Button - only show when name is entered */}
                        {studentName.trim() && (
                            <div className="mt-4">
                                <button
                                    type="button"
                                onClick={() => navigate(`/history?student=${encodeURIComponent(studentName)}`)}
                                    className="w-full py-3 bg-white border-2 border-[#00B4EE] text-[#00B4EE] font-medium rounded-xl hover:bg-[#00B4EE]/10 transition-all flex items-center justify-center gap-2"
                            >
                                    <History className="w-5 h-5" />
                                    <span>查阅历史报告</span>
                            </button>
                        </div>
                    )}
                    </div>

                    <p className="text-center text-white mt-6 text-sm drop-shadow-lg">
                        测试包含三个部分，请确保在安静的环境中完成
                    </p>
                </div>
            </div>
        </div>
    );
}

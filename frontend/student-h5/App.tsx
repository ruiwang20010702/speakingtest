import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import EntryPage from './pages/EntryPage';
import HomePage from './pages/HomePage';
import TestPage from './pages/TestPage';
import ResultPage from './pages/ResultPage';
import { Level, TestResult } from './types';
import { evaluateTest } from './services/api';

// Wrapper for TestPage to handle props from localStorage/API
const TestContainer: React.FC = () => {
  const studentName = localStorage.getItem('studentName') || 'Student';
  const level = (localStorage.getItem('level') as Level) || 'L0'; // Default to L0 for testing
  const unit = localStorage.getItem('unit') || 'All'; // Default to All for L0
  const [submitting, setSubmitting] = React.useState(false);

  // 存储 Part 1 评分 Promise，以便在 Part 2 完成后 await
  const part1PromiseRef = React.useRef<Promise<void> | null>(null);

  // Part 1 完成后立即调用（静默后台评分）
  const handlePart1Complete = async (audio: Blob, part1Questions: { text: string }[]) => {
    try {
      const testIdStr = localStorage.getItem('testId');
      if (!testIdStr) throw new Error('No test ID found');
      const testId = parseInt(testIdStr);

      const { submitPart1 } = await import('./services/api');
      // 直接使用传入的题目列表，避免重复请求
      const part1Text = part1Questions.map(q => q.text).join(' ');

      // 创建 Promise 并存储引用（静默执行，不显示状态）
      part1PromiseRef.current = submitPart1(testId, audio, part1Text)
        .then(() => {
          console.log('Part 1 evaluation completed');
        })
        .catch((err) => {
          console.error('Part 1 evaluation failed:', err);
        });

    } catch (error) {
      console.error('Part 1 submission failed:', error);
    }
  };

  // Part 2 完成后调用
  const handleComplete = async (audios: Blob[]) => {
    if (submitting) return;
    setSubmitting(true);

    try {
      const testIdStr = localStorage.getItem('testId');
      if (!testIdStr) throw new Error('No test ID found');
      const testId = parseInt(testIdStr);

      const { submitPart2 } = await import('./services/api');

      // 1. 提交 Part 2
      if (audios[1]) {
        console.log('Submitting Part 2...');
        await submitPart2(testId, audios[1]);
      }

      // 2. 等待 Part 1 完成（如果还在处理中）
      if (part1PromiseRef.current) {
        console.log('Waiting for Part 1 to complete...');
        await part1PromiseRef.current;
      }

      // 3. 跳转到结果页
      window.location.href = '/result';

    } catch (error) {
      console.error('Submission failed:', error);
      alert('提交失败，请重试');
      setSubmitting(false);
    }
  };

  if (submitting) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white">
        <div className="w-12 h-12 border-4 border-[#1CB0F6] border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-[#1E293B] font-bold">正在上传评测结果...</p>
      </div>
    );
  }

  return (
    <TestPage
      studentName={studentName}
      level={level}
      unit={unit}
      onExit={() => window.location.href = '/'}
      onComplete={handleComplete}
      onPart1Complete={handlePart1Complete}
    />
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="antialiased min-h-screen overflow-hidden">
        <Routes>
          {/* Entry Route: /s/:token */}
          <Route path="/s/:token" element={<EntryPage />} />

          {/* Main Test Route */}
          <Route path="/test" element={<TestContainer />} />

          {/* Result Route */}
          <Route path="/result" element={<ResultPage onRestart={() => window.location.href = '/'} part1Score={20} />} />

          {/* Fallback for dev/demo */}
          <Route path="/" element={<HomePage onStart={() => { }} />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;

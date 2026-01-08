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

  const handleComplete = async (audios: Blob[]) => {
    if (submitting) return;
    setSubmitting(true);

    try {
      const testIdStr = localStorage.getItem('testId');
      if (!testIdStr) throw new Error('No test ID found');
      const testId = parseInt(testIdStr);

      // 1. Fetch questions to get reference text for Part 1
      // Note: In a real app, we might want to pass this from TestPage or store it in context
      const { getQuestions, submitPart1, submitPart2 } = await import('./services/api');
      const questions = await getQuestions(level, unit);

      // Part 1 is the first 20 words
      const part1Text = questions.slice(0, 20).map(q => q.text).join(' ');

      // 2. Submit Part 1
      if (audios[0]) {
        console.log('Submitting Part 1...');
        await submitPart1(testId, audios[0], part1Text);
      }

      // 3. Submit Part 2
      if (audios[1]) {
        console.log('Submitting Part 2...');
        await submitPart2(testId, audios[1]);
      }

      // 4. Navigate to result
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

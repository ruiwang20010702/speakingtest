import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import EntryPage from './pages/EntryPage';
import HomePage from './pages/HomePage';
import TestPage from './pages/TestPage';
import ResultPage from './pages/ResultPage';
import { Level, TestResult } from './types';

// Check if we're in development mode
const isDev = import.meta.env.DEV;

// Error page component for invalid access
const InvalidAccessPage: React.FC = () => {
  // Clear any stale data (token 不再存储在 localStorage，已改用 httpOnly Cookie)
  React.useEffect(() => {
    localStorage.removeItem('studentName');
    localStorage.removeItem('level');
    localStorage.removeItem('unit');
    localStorage.removeItem('testId');
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#002FA7] p-6">
      <div className="text-white text-center">
        <div className="text-6xl mb-4">🔒</div>
        <h1 className="text-2xl font-bold mb-2">无效的入口链接</h1>
        <p className="text-white/80 mb-4">请联系老师获取正确的测评链接</p>
        <p className="text-white/60 text-sm">链接格式: /s/your-token-here</p>
      </div>
    </div>
  );
};

// Wrapper for TestPage to handle props from localStorage/API
const TestContainer: React.FC = () => {
  // Security check: Require valid session data
  // Token 已改用 httpOnly Cookie（JS 不可见），只检查 testId 是否存在
  // 如果 API 调用返回 401，浏览器会自动处理
  const hasValidSession = localStorage.getItem('testId');
  
  if (!hasValidSession) {
    // In development, allow mock data for testing
    if (isDev) {
      console.log('[DEV] No valid session, using mock data');
      if (!localStorage.getItem('studentName')) {
        localStorage.setItem('studentName', 'Test Student');
      }
      if (!localStorage.getItem('level')) {
        localStorage.setItem('level', 'L0');
      }
      if (!localStorage.getItem('unit')) {
        localStorage.setItem('unit', 'Full Level');
      }
      if (!localStorage.getItem('testId')) {
        const tempTestId = Date.now();
        localStorage.setItem('testId', tempTestId.toString());
        console.log('[DEV] Using temporary testId:', tempTestId);
      }
    } else {
      // Production: redirect to error page
      return <InvalidAccessPage />;
    }
  }
  
  const studentName = localStorage.getItem('studentName') || 'Student';
  const level = (localStorage.getItem('level') as Level) || 'L0';
  const unit = localStorage.getItem('unit') || 'Full Level';
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
      // 直接使用传入的题目列表，用逗号分隔（配合 AI 短语识别规则）
      const part1Text = part1Questions.map(q => q.text).join(', ');

      // 创建 Promise 并存储引用（静默执行，不显示状态）
      part1PromiseRef.current = submitPart1(testId, audio, part1Text)
        .then(() => {
          if (isDev) console.log('Part 1 evaluation completed');
        })
        .catch((err) => {
          if (isDev) console.error('Part 1 evaluation failed:', err);
        });

    } catch (error) {
      if (isDev) console.error('Part 1 submission failed:', error);
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

      const { submitPart2, getTestReport } = await import('./services/api');

      // 1. 提交 Part 2
      if (audios[1]) {
        if (isDev) console.log('Submitting Part 2...');
        await submitPart2(testId, audios[1]);
      }

      // 2. 等待 Part 1 提交完成（如果还在提交中）
      if (part1PromiseRef.current) {
        if (isDev) console.log('Waiting for Part 1 submission...');
        await part1PromiseRef.current;
      }

      // 3. 轮询等待 Part 1 分数出来（最多等待 60 秒）
      if (isDev) console.log('Waiting for Part 1 score...');
      const maxWaitTime = 60000; // 60 秒
      const pollInterval = 2000; // 每 2 秒检查一次
      const startTime = Date.now();

      while (Date.now() - startTime < maxWaitTime) {
        try {
          const report = await getTestReport(testId);
          if (report.part1_score !== undefined && report.part1_score !== null) {
            if (isDev) console.log('Part 1 score ready:', report.part1_score);
            break;
          }
        } catch (e) {
          // 报告还没准备好，继续等待
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }

      // 4. 跳转到结果页
      window.location.href = '/result';

    } catch (error) {
      if (isDev) console.error('Submission failed:', error);
      alert('提交失败，请重试');
      setSubmitting(false);
    }
  };

  if (submitting) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#002FA7] p-6">
        <div className="w-16 h-16 border-4 border-[#FFF59D] border-t-transparent rounded-full animate-spin mb-6"></div>
        <p className="text-white font-black text-xl mb-2">正在生成报告...</p>
        <p className="text-white/80 font-bold text-sm text-center">
          AI 正在分析你的发音和回答<br />
          请稍等片刻 ✨
        </p>
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

          {/* Main Test Route - requires valid session */}
          <Route path="/test" element={<TestContainer />} />

          {/* Result Route */}
          <Route path="/result" element={<ResultPage onRestart={() => window.location.href = '/'} part1Score={20} />} />

          {/* Root and fallback routes */}
          {isDev ? (
            // Development: allow direct access to /test for testing
            <>
              <Route path="/" element={<Navigate to="/test" replace />} />
              <Route path="*" element={<Navigate to="/test" replace />} />
            </>
          ) : (
            // Production: show error page for invalid access
            <>
              <Route path="/" element={<InvalidAccessPage />} />
              <Route path="*" element={<InvalidAccessPage />} />
            </>
          )}
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;

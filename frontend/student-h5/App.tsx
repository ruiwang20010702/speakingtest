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

  const handleComplete = async (audios: Blob[]) => {
    // TODO: Implement real submission logic
    console.log('Test completed', audios);
    // navigate('/result');
  };

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
          {/* <Route path="/result" element={<ResultPage />} /> */}

          {/* Fallback for dev/demo */}
          <Route path="/" element={<HomePage onStart={() => { }} />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;

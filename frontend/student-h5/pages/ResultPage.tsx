import React, { useEffect, useState } from 'react';
import { Star, MessageCircle, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { getTestReport } from '../services/api';
import { FullReportResponse } from '../types';

interface ResultPageProps {
  part1Score?: number;  // Legacy prop, can be ignored if fetching from API
  onRestart: () => void;
}

const ResultPage: React.FC<ResultPageProps> = ({ onRestart }) => {
  const [report, setReport] = useState<FullReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    window.scrollTo(0, 0);
    const fetchReport = async () => {
      try {
        const testIdStr = localStorage.getItem('testId');
        if (!testIdStr) {
          throw new Error('未找到测评记录');
        }
        const data = await getTestReport(parseInt(testIdStr));
        setReport(data);
      } catch (err: any) {
        console.error('获取报告失败:', err);
        setError('获取报告失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Loader2 className="w-10 h-10 text-[#1CB0F6] animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white p-6 text-center">
        <AlertCircle className="w-16 h-16 text-red-400 mb-4" />
        <p className="text-[#1E293B] mb-6">{error}</p>
        <button onClick={onRestart} className="px-6 py-2 bg-[#1CB0F6] text-white rounded-lg font-bold">
          返回首页
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 overflow-hidden bg-white">
      <div className="w-full max-w-md flex flex-col items-center relative py-8">

        {/* Success Icon */}
        <div className="w-24 h-24 bg-[#58CC02] rounded-full flex items-center justify-center mb-8 shadow-xl animate-pop">
          <CheckCircle2 className="w-14 h-14 text-white" strokeWidth={2.5} />
        </div>

        {/* Title */}
        <h1 className="text-3xl font-black text-[#1E293B] mb-3 tracking-tight animate-pop delay-1">
          测评完成！
        </h1>

        <p className="text-[#1E293B]/60 font-bold text-base mb-10 animate-pop delay-1">
          你真棒，已完成本次口语测评
        </p>

        {/* Part 1 Score Card */}
        {report?.part1_score !== undefined && (
          <div className="w-full bg-gradient-to-br from-[#FFD200]/10 to-[#FFD200]/5 rounded-[24px] p-6 mb-4 border-2 border-[#FFD200]/30 animate-pop delay-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-[#1E293B]/60 mb-1">词汇朗读得分</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-black text-[#1E293B]">{report.part1_score}</span>
                  <span className="text-2xl font-black text-[#1E293B]/40">/100</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-[#FFD200] rounded-full flex items-center justify-center shadow-lg">
                <Star className="w-9 h-9 text-white fill-current" />
              </div>
            </div>
          </div>
        )}

        {/* AI Suggestion Card (Part 2) */}
        {report?.part2_suggestions && report.part2_suggestions.length > 0 && (
          <div className="w-full bg-indigo-50 rounded-[24px] p-6 mb-8 border-2 border-indigo-100 animate-pop delay-3">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center">
                <Star className="w-4 h-4 text-white fill-current" />
              </div>
              <h3 className="font-black text-[#1E293B]">AI 学习建议</h3>
            </div>
            <ul className="space-y-2">
              {report.part2_suggestions.map((suggestion, index) => (
                <li key={index} className="text-sm text-[#1E293B]/80 leading-relaxed flex items-start gap-2">
                  <span className="text-indigo-500 font-bold">•</span>
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Guidance Card */}
        <div className="w-full bg-[#1CB0F6]/5 rounded-[24px] p-6 mb-10 border-2 border-[#1CB0F6]/20 animate-pop delay-3">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-[#1CB0F6] rounded-full flex items-center justify-center flex-shrink-0">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="font-black text-[#1E293B] text-base mb-2">完整报告已生成</p>
              <p className="text-sm text-[#1E293B]/60 leading-relaxed">
                包含总分、星级评定与学习建议。<br />
                请联系<span className="font-bold text-[#1CB0F6]">班主任老师</span>获取详细报告。
              </p>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={onRestart}
          className="w-full py-5 bg-[#1CB0F6] text-white font-black text-xl rounded-[20px] active:scale-95 transition-all shadow-[0_6px_0_#1899D6] active:shadow-none active:translate-y-[6px] animate-pop delay-4"
        >
          完成
        </button>

        <p className="mt-6 text-center text-gray-400 font-bold text-xs uppercase tracking-widest">
          51TALK AI 口语测评系统
        </p>
      </div>
    </div>
  );
};

export default ResultPage;


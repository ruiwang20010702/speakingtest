/**
 * Custom hook for fetching and managing report data.
 */
import { useState, useEffect, useCallback } from 'react';
import { ParentReportData } from '../types';
import { fetchParentReport, getTokenFromUrl } from '../services/api';

interface UseReportDataResult {
  data: ParentReportData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

// Demo/Mock data for development when no token is provided
const MOCK_DATA: ParentReportData = {
  student: {
    name: "示例学生",
    level: "Level 2"
  },
  overall: {
    total_score: 82.5,
    star_level: 4
  },
  radar: [
    { subject: "流利度", score: 78, fullMark: 100, icon: "fluency", comment: "等级：优秀 - 整体连贯，偶有轻微停顿，节奏感较好。", tags: ["整体连贯", "偶有停顿"] },
    { subject: "发音", score: 85, fullMark: 100, icon: "pronunciation", comment: "等级：杰出 - 发音地道清晰，元音饱满，辅音准确。", tags: ["发音地道", "易于理解"] },
    { subject: "自信度", score: 90, fullMark: 100, icon: "confidence", comment: "等级：杰出 - 声音洪亮，主动表达，自信满满！", tags: ["声音洪亮", "主动分享", "自信满满"] },
    { subject: "词汇", score: 72, fullMark: 100, icon: "vocab", comment: "等级：优秀 - 绝大多数单词准确，偶有轻微错误。", tags: ["词汇良好", "偶有错误"] },
    { subject: "整句输出", score: 80, fullMark: 100, icon: "sentence", comment: "等级：杰出 - 能完整输出长句，逻辑清晰，句式多样。", tags: ["逻辑连贯", "句式多样"] }
  ],
  part1: {
    score: 85,
    words: [
      { text: "apple", status: "perfect" },
      { text: "banana", status: "perfect" },
      { text: "elephant", status: "unclear" },
      { text: "giraffe", status: "perfect" },
      { text: "helicopter", status: "failed" },
      { text: "library", status: "perfect" },
      { text: "mountain", status: "perfect" },
      { text: "restaurant", status: "unclear" },
      { text: "strawberry", status: "perfect" },
      { text: "telephone", status: "perfect" }
    ]
  },
  part2: {
    score: 80,
    best_sample: {
      question_no: 4,
      question: "What do you usually do on weekends?",
      answer: "I love playing soccer with my friends in the park on weekends.",
      score: "S",
      feedback: "发音饱满，停顿自然。自信感与语流极其出色！"
    },
    weak_sample: {
      question_no: 9,
      question: "Can you describe the elephant you saw?",
      answer: "The elephant is much bigger than the tiger we saw yesterday.",
      score: "B",
      feedback: "在长词汇上有轻微犹豫。建议多练习元音连读。"
    }
  },
  suggestion: {
    highlights: ["发音清晰，元音饱满", "自信表达，声音洪亮"],
    weaknesses: ["部分长单词需要加强"],
    plan: ["每天跟读 10 分钟标准音频", "多用完整句子回答问题", "保持自信，大声开口练习"]
  }
};

// Check if we're in development mode
const isDev = import.meta.env.DEV;

export function useReportData(): UseReportDataResult {
  const [data, setData] = useState<ParentReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const token = getTokenFromUrl();
    
    // If no token, use mock data for development only
    if (!token) {
      if (isDev) {
      console.log('[useReportData] No token found, using mock data');
      setData(MOCK_DATA);
      } else {
        // Production: show error instead of mock data
        setError('缺少报告链接参数');
        setData(null);
      }
      setIsLoading(false);
      return;
    }

    try {
      // Only log in development - NEVER log the token
      if (isDev) {
        console.log('[useReportData] Fetching report...');
      }
      const reportData = await fetchParentReport(token);
      // NEVER log report data (contains student info)
      if (isDev) {
        console.log('[useReportData] Report fetched successfully');
      }
      setData(reportData);
    } catch (err) {
      // Only log error type in development, not details
      if (isDev) {
        console.error('[useReportData] Error fetching report');
      }
      const errorMessage = err instanceof Error ? err.message : '加载失败';
      setError(errorMessage);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData
  };
}


export type Level = 'L0' | 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6';

export interface Question {
  id: string;
  type: 'word' | 'sentence' | 'qa';
  text: string;
  image?: string;
  translation?: string;
  referenceAnswer?: string;
}

export interface TestSession {
  studentName: string;
  level: Level;
  unit: string;
  startTime: number;
}

export interface TestResult {
  score: number;
  totalScore: number;
  level: Level;
  studentName: string;
  date: string;
  duration: string;
  comment: string;
  stars: number;
  // 新增：能力维度分析
  analysis: {
    accuracy: number; // 准确度
    fluency: number;  // 流利度
    vocabulary: number; // 词汇量/词汇运用
  };
}

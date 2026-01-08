
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

export interface TestItemResponse {
  question_no: number;
  score: number;
  feedback?: string;
  evidence?: string;
}

export interface FullReportResponse {
  test_id: number;
  status: string;
  student_name: string;
  level: string;
  unit: string;
  total_score?: number;
  star_level?: number;
  part1_score?: number;
  part1_fluency?: number;
  part1_pronunciation?: number;
  part2_score?: number;
  part2_transcript?: string;
  part2_items: TestItemResponse[];
  part2_suggestions: string[];
  created_at?: string;
  completed_at?: string;
}

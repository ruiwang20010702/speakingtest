export enum PageState {
  Cover = 0,
  Radar = 1,
  Vocab = 2,
  Dialogue = 3,
  LearningAdvice = 4,
  Badge = 5
}

// ============================================
// API Response Types (matches backend schema)
// ============================================

export interface StudentInfo {
  name: string;
  level: string;
}

export interface OverallScore {
  total_score: number;
  star_level: number;
}

export interface RadarDimension {
  subject: string;
  score: number;      // 0-100 scale
  fullMark: number;   // Always 100
  icon: string;       // 'fluency', 'pronunciation', 'confidence', 'vocab', 'sentence'
  comment: string;    // Level description
  tags: string[];     // Tags for this dimension
}

export interface WordStatus {
  text: string;
  status: 'perfect' | 'unclear' | 'failed';
}

export interface Part1Detail {
  score: number;
  words: WordStatus[];
}

export interface DialogueSample {
  question_no: number;
  question: string;
  answer: string;
  score: string;  // 'S', 'A', 'B', 'C'
  feedback: string;
}

export interface Part2Detail {
  score: number;
  best_sample: DialogueSample | null;
  weak_sample: DialogueSample | null;
}

export interface Suggestion {
  highlights: string[];
  weaknesses: string[];
  plan: string[];
}

export interface ParentReportData {
  student: StudentInfo;
  overall: OverallScore;
  radar: RadarDimension[];
  part1: Part1Detail;
  part2: Part2Detail;
  suggestion: Suggestion;
}

// ============================================
// Legacy Types (for backward compatibility)
// ============================================

export interface RadarData {
  subject: string;
  A: number;          // Score value (0-100)
  fullMark: number;   // Max value (100)
  icon: string;
  detailTitle?: string;
  detailContent?: string;
  tags?: string[];
  isWeakness?: boolean;
}

export type VocabWordStatus = 'perfect' | 'unclear' | 'failed';

export interface VocabWord {
  text: string;
  status: VocabWordStatus;
  phonetic?: string;
}

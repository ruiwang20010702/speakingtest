/**
 * TypeScript 类型定义
 */

export interface WordItem {
    id: number;
    word: string;
}

export interface SentenceItem {
    id: number;
    text: string;
}

export interface DialogueItem {
    id: number;
    teacher: string;
    student_options: string[];
}

export interface Part {
    part_id: number;
    part_name: string;
    type: string;
    max_score: number;
    instruction: string;
    items?: WordItem[];
    words?: WordItem[];
    sentences?: SentenceItem[];
    dialogues?: DialogueItem[];
}

export interface QuestionData {
    level: string;
    level_name: string;
    unit: string;
    unit_name: string;
    parts: Part[];
}

export interface PartScore {
    part_number: number;
    score: number;
    max_score: number;
    feedback: string;
    correct_items: string[];
    incorrect_items: string[];
}

export interface TestResult {
    id: number;
    student_name: string;
    level: string;
    unit: string;
    total_score: number;
    star_rating: number;
    fluency_score?: number;  // 流畅度 (0-10) - Gemini AI评估
    pronunciation_score?: number;  // 发音 (0-10) - Gemini AI评估
    confidence_score?: number;  // 自信度 (0-10) - Gemini AI评估
    total_tokens?: number;  // API调用总token数
    api_cost?: number;  // API调用总成本（美元）
    created_at: string;
    part_scores: PartScore[];
}

export interface Level {
    id: string;
    name: string;
}

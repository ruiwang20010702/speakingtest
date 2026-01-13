export interface Student {
    id: string;
    name: string;
    avatarUrl?: string; // Optional user avatar
    grade: string;      // e.g., "四年级"
    level: string;      // e.g., "L1"
    currentUnit: string; // e.g., "Unit 1 Food"
    status: 'active' | 'inactive';
}

export type AssessmentStatus = 'completed' | 'in_progress' | 'pending' | 'failed';

export interface Assessment {
    id: string;
    studentId: string;
    title: string;       // e.g., "L0 - All"
    level: string;
    unit: string;
    status: AssessmentStatus;
    score?: number;      // 0-100
    stars?: number;      // 0-3
    createdAt: string;   // ISO string
    completedAt?: string; // ISO string
    reportUrl?: string;
    entryUrl?: string;   // For in-progress assessments
}

export interface StatsOverview {
    totalStudents: number;
    assessmentsThisWeek: number;
    pendingFollowUp: number;
}

export interface Student {
    id: string;           // External ID for display (e.g., "stu1928409")
    internalId: string;   // Internal user_id for API calls
    name: string;
    avatarUrl?: string;   // Optional user avatar
    grade: string;        // e.g., "四年级"
    level: string;        // e.g., "L1"
    currentUnit: string;  // e.g., "Unit 1 Food"
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
    stars?: number;      // 0-5
    createdAt: string;   // ISO string
    completedAt?: string; // ISO string
    reportUrl?: string;
    entryUrl?: string;   // For in-progress assessments
    isInterpreted?: boolean;  // 是否已生成报告解读
    interpretationStatus?: 'pending' | 'generating' | 'completed' | 'failed';  // 报告解读状态
    failureReason?: string;   // 失败原因（当 status=failed 时）
    retryCount?: number;      // 重试次数
    isArchived?: boolean;     // 是否为归档数据（历史测评，超过保留期）
}

export interface StatsOverview {
    totalStudents: number;
    assessmentsThisWeek: number;
    pendingFollowUp: number;
}

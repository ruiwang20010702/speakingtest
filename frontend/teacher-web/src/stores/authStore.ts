import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../api';

interface AuthState {
    // 不再存储 token（改用 httpOnly Cookie，更安全）
    email: string | null;
    teacherName: string | null;
    role: string | null;
    isAuthenticated: boolean;

    login: (email: string, teacherName: string, role: string) => void;
    logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            email: null,
            teacherName: null,
            role: null,
            isAuthenticated: false,

            // 登录成功后调用（token 已通过 httpOnly Cookie 设置）
            login: (email, teacherName, role) => {
                set({
                    email,
                    teacherName,
                    role,
                    isAuthenticated: true,
                });
            },

            // 退出登录（调用后端清除 Cookie）
            logout: async () => {
                try {
                    await api.post('/auth/logout');
                } catch (error) {
                    // 即使后端调用失败，也清理本地状态
                    if (import.meta.env.DEV) {
                        console.error('Logout API error:', error);
                    }
                }
                set({
                    email: null,
                    teacherName: null,
                    role: null,
                    isAuthenticated: false,
                });
            },
        }),
        {
            name: 'auth-storage',
            // 只持久化非敏感的用户信息
            partialize: (state) => ({
                email: state.email,
                teacherName: state.teacherName,
                role: state.role,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

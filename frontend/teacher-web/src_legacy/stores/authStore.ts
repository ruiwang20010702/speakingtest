import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
    token: string | null;
    email: string | null;
    teacherName: string | null;
    role: string | null;
    isAuthenticated: boolean;

    login: (token: string, email: string, teacherName: string, role: string) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            token: null,
            email: null,
            teacherName: null,
            role: null,
            isAuthenticated: false,

            login: (token, email, teacherName, role) => {
                localStorage.setItem('token', token);
                set({
                    token,
                    email,
                    teacherName,
                    role,
                    isAuthenticated: true,
                });
            },

            logout: () => {
                localStorage.removeItem('token');
                set({
                    token: null,
                    email: null,
                    teacherName: null,
                    role: null,
                    isAuthenticated: false,
                });
            },
        }),
        {
            name: 'auth-storage',
        }
    )
);

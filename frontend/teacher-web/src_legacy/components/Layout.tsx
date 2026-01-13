import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import logo from '../assets/logo.png';

interface LayoutProps {
    children: React.ReactNode;
    title?: string;
    showBack?: boolean;
    actions?: React.ReactNode;
}

export default function Layout({ children, title, showBack = false, actions }: LayoutProps) {
    const navigate = useNavigate();
    const { teacherName, role, logout } = useAuthStore();
    const isAdmin = role === 'admin';

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Top Navigation Bar */}
            <header className="bg-white border-b border-border sticky top-0 z-20 shadow-sm h-16">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div 
                            className="flex items-center gap-3 cursor-pointer" 
                            onClick={() => navigate('/')}
                        >
                            <img src={logo} alt="51Talk" className="h-8 w-auto object-contain" />
                            <div className="h-5 w-px bg-gray-200 hidden sm:block"></div>
                            <h1 className="text-lg font-bold text-primary tracking-tight hidden sm:block">
                                口语测评系统 <span className="text-xs font-normal text-gray-500 ml-1">教师端</span>
                            </h1>
                        </div>
                        
                        {/* Page Title / Breadcrumb area */}
                        {title && (
                            <div className="hidden md:flex items-center text-sm font-medium text-gray-500">
                                <span className="mx-2">/</span>
                                <span className="text-gray-900">{title}</span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-4">
                        {/* User Profile */}
                        <div className="flex items-center gap-3 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
                            <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs font-bold">
                                {teacherName ? teacherName.charAt(0) : 'A'}
                            </div>
                            <span className="text-sm font-medium text-gray-700 max-w-[100px] truncate">
                                {teacherName || (isAdmin ? '管理员' : '老师')}
                            </span>
                        </div>

                        {/* Global Actions */}
                        <div className="h-5 w-px bg-gray-200"></div>
                        
                        <button 
                            onClick={logout}
                            className="text-sm text-gray-500 hover:text-red-600 transition-colors font-medium flex items-center gap-1"
                        >
                            退出
                        </button>
                    </div>
                </div>
            </header>

            {/* Page Content */}
            <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Page Header (Optional Back Button & Actions) */}
                {(showBack || actions) && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                        <div className="flex items-center gap-3">
                            {showBack && (
                                <button 
                                    onClick={() => navigate(-1)}
                                    className="p-2 -ml-2 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
                                    title="返回"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                                    </svg>
                                </button>
                            )}
                            {title && <h2 className="text-2xl font-bold text-gray-900">{title}</h2>}
                        </div>
                        
                        {actions && (
                            <div className="flex items-center gap-3">
                                {actions}
                            </div>
                        )}
                    </div>
                )}

                {children}
            </main>
        </div>
    );
}

import React, { useState, useEffect, useRef } from 'react';
import { Home, Zap, UserCircle, LogOut, ChevronUp } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../../stores/authStore';
import { systemApi } from '../../api';

type AIStatus = 'online' | 'offline' | 'checking';

export const Sidebar: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    
    // Auth state
    const { teacherName, email, role, logout } = useAuthStore();
    
    // User dropdown state
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const userMenuRef = useRef<HTMLDivElement>(null);
    
    // AI status state
    const [aiStatus, setAiStatus] = useState<AIStatus>('checking');
    const [aiMessage, setAiMessage] = useState('检查中...');
    const [aiModel, setAiModel] = useState('');

    const menuItems = [
        { icon: Home, label: '工作台', path: '/dashboard' }
    ];

    // Fetch AI status only once on mount (no polling to reduce API calls)
    useEffect(() => {
        const checkAiStatus = async () => {
            try {
                const response = await systemApi.getAiStatus();
                setAiStatus(response.data.status as AIStatus);
                setAiMessage(response.data.message);
                setAiModel(response.data.model);
            } catch (error) {
                console.error('Failed to check AI status:', error);
                setAiStatus('offline');
                setAiMessage('无法连接');
            }
        };

        checkAiStatus();
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
                setIsUserMenuOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    // Get display name
    const displayName = teacherName || email?.split('@')[0] || '用户';
    const displayRole = role === 'admin' ? '管理员' : '教师';

    // AI status indicator color
    const statusColor = {
        online: 'bg-green-400',
        offline: 'bg-red-400',
        checking: 'bg-yellow-400'
    }[aiStatus];

    return (
        <aside className="h-screen w-20 lg:w-64 bg-primary fixed left-0 top-0 flex flex-col justify-between py-6 z-50 transition-all duration-300">
            {/* Logo Area */}
            <div className="px-6 mb-10 flex items-center gap-3">
                <div className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center shrink-0">
                    <Zap size={18} className="text-primary fill-current" />
                </div>
                <h1 className="text-xl font-bold text-white tracking-tight hidden lg:block">51Talk <span className="text-white/60 font-normal text-sm">Pro</span></h1>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 space-y-2">
                {menuItems.map((item) => {
                    const isActive = location.pathname.startsWith(item.path);
                    return (
                        <button
                            key={item.path}
                            onClick={() => navigate(item.path)}
                            className={clsx(
                                "flex items-center gap-3 p-3 rounded-xl w-full transition-all duration-200 group relative",
                                isActive
                                    ? "bg-white text-primary font-bold shadow-lg"
                                    : "text-white/80 hover:bg-white/10 hover:text-white"
                            )}
                        >
                            <item.icon size={20} className={clsx(isActive ? "text-primary" : "text-white/80")} />
                            <span className="hidden lg:block">{item.label}</span>
                            {isActive && (
                                <motion.div
                                    layoutId="active-indicator"
                                    className="absolute left-0 w-1 h-6 bg-secondary rounded-r-full lg:hidden"
                                />
                            )}
                        </button>
                    )
                })}
            </nav>

            {/* Bottom Info */}
            <div className="px-4">
                {/* AI Status */}
                <div className="mb-6 px-4 py-3 bg-white/5 rounded-xl border border-white/10 hidden lg:flex items-center gap-3">
                    <div className="relative">
                        <div className={clsx("w-2.5 h-2.5 rounded-full", statusColor, aiStatus === 'checking' && "animate-pulse")}></div>
                        {aiStatus === 'online' && (
                            <div className="absolute inset-0 bg-green-400 rounded-full animate-ping opacity-20"></div>
                        )}
                    </div>
                    <div>
                        <p className="text-xs text-secondary font-medium uppercase tracking-wider">AI Engine</p>
                        <p className="text-xs text-white/60">
                            {aiModel ? `${aiModel.replace('qwen3-omni-flash', 'Qwen-Omni')} ` : ''}{aiMessage}
                        </p>
                    </div>
                </div>

                {/* User Profile with Dropdown */}
                <div className="relative" ref={userMenuRef}>
                    <button
                        onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                        className="w-full flex items-center gap-3 px-2 py-2 text-white/90 hover:bg-white/10 rounded-lg cursor-pointer transition-colors"
                    >
                        <UserCircle size={32} className="shrink-0" />
                        <div className="hidden lg:block overflow-hidden flex-1 text-left">
                            <p className="text-sm font-bold truncate">{displayName}</p>
                            <p className="text-xs text-white/50 truncate">{displayRole}</p>
                        </div>
                        <ChevronUp 
                            size={16} 
                            className={clsx(
                                "hidden lg:block text-white/50 transition-transform duration-200",
                                isUserMenuOpen ? "rotate-0" : "rotate-180"
                            )} 
                        />
                    </button>

                    {/* Dropdown Menu */}
                    <AnimatePresence>
                        {isUserMenuOpen && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 10 }}
                                transition={{ duration: 0.15 }}
                                className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl shadow-xl overflow-hidden"
                            >
                                {/* User Info */}
                                <div className="px-4 py-3 border-b border-gray-100">
                                    <p className="text-sm font-bold text-gray-900 truncate">{displayName}</p>
                                    <p className="text-xs text-gray-500 truncate">{email}</p>
                                </div>

                                {/* Logout Button */}
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 transition-colors"
                                >
                                    <LogOut size={18} />
                                    <span className="text-sm font-medium">退出登录</span>
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </aside>
    );
};

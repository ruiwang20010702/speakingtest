import React from 'react';
import { Home, Zap, UserCircle } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export const Sidebar: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { icon: Home, label: '工作台', path: '/dashboard' }
    ];

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
                        <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse"></div>
                        <div className="absolute inset-0 bg-green-400 rounded-full animate-ping opacity-20"></div>
                    </div>
                    <div>
                        <p className="text-xs text-secondary font-medium uppercase tracking-wider">AI Engine</p>
                        <p className="text-xs text-white/60">Qwen-Omni 运行中</p>
                    </div>
                </div>

                {/* User Profile */}
                <div className="flex items-center gap-3 px-2 py-2 text-white/90 hover:bg-white/10 rounded-lg cursor-pointer transition-colors">
                    <UserCircle size={32} className="shrink-0" />
                    <div className="hidden lg:block overflow-hidden">
                        <p className="text-sm font-bold truncate">Wang Rui</p>
                        <p className="text-xs text-white/50 truncate">Senior Teacher</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

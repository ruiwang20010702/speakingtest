import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';
import { authApi } from '../../api';
import { useAuthStore } from '../../stores/authStore';

export const LoginPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [code, setCode] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSendingCode, setIsSendingCode] = useState(false);
    const [countdown, setCountdown] = useState(0);
    const [error, setError] = useState<string | null>(null);

    const navigate = useNavigate();
    const login = useAuthStore((state) => state.login);

    const handleSendCode = async () => {
        if (!email || isSendingCode || countdown > 0) return;

        setError(null);
        setIsSendingCode(true);
        try {
            await authApi.sendCode(email);
            setCountdown(60);
            const timer = setInterval(() => {
                setCountdown((prev) => {
                    if (prev <= 1) {
                        clearInterval(timer);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } catch (err: any) {
            console.error('Failed to send code:', err);
            // Handle different error formats (Pydantic validation vs custom errors)
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                // Pydantic validation error format: [{loc: [...], msg: "...", type: "..."}]
                // Remove "Value error, " prefix if present
                const msg = detail[0]?.msg?.replace(/^Value error, /i, '') || '发送验证码失败，请重试';
                setError(msg);
            } else if (typeof detail === 'object' && detail?.message) {
                // Custom error format: {error: "...", message: "..."}
                setError(detail.message);
            } else if (typeof detail === 'string') {
                setError(detail);
            } else {
                setError('发送验证码失败，请重试');
            }
        } finally {
            setIsSendingCode(false);
        }
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email || !code) return;

        setError(null);
        setIsLoading(true);
        try {
            const response = await authApi.login(email, code);
            const { access_token, name, role } = response.data;
            login(access_token, email, name, role);
            navigate('/dashboard');
        } catch (err: any) {
            console.error('Login failed:', err);
            // Handle different error formats
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                const msg = detail[0]?.msg?.replace(/^Value error, /i, '') || '登录失败，请检查验证码';
                setError(msg);
            } else if (typeof detail === 'object' && detail?.message) {
                setError(detail.message);
            } else if (typeof detail === 'string') {
                setError(detail);
            } else {
                setError('登录失败，请检查验证码');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-100 via-background to-background">
            <div className="w-full max-w-md">
                {/* Brand Header */}
                <div className="text-center mb-10">
                    <div className="flex items-center justify-center gap-2 mb-2">
                        <div className="bg-secondary w-2 h-8 rounded-full"></div>
                        <h1 className="text-3xl font-bold tracking-tight text-primary">51Talk</h1>
                    </div>
                    <p className="text-text-sub font-medium">教师端</p>
                </div>

                {/* Login Card */}
                <div className="card-surface p-8 md:p-10 relative overflow-hidden group">
                    {/* Ambient Shine Effect */}
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 w-40 h-40 rounded-full bg-primary/5 blur-3xl group-hover:bg-primary/10 transition-all duration-700"></div>

                    <h2 className="text-2xl font-semibold mb-8 text-text-main relative z-10">欢迎回来</h2>
                    
                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm relative z-10">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="space-y-6 relative z-10">

                        {/* Email Input */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-text-sub ml-1" htmlFor="email">邮箱地址</label>
                            <div className="relative group/input">
                                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-sub/50 group-focus-within/input:text-primary transition-colors">
                                    <Mail size={20} />
                                </div>
                                <input
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="name@51talk.com"
                                    className="input-field pl-10"
                                    required
                                />
                            </div>
                        </div>

                        {/* Verification Code Input */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-text-sub ml-1" htmlFor="code">验证码</label>
                            <div className="flex gap-3">
                                <div className="relative flex-1 group/input">
                                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-sub/50 group-focus-within/input:text-primary transition-colors">
                                        <ShieldCheck size={20} />
                                    </div>
                                    <input
                                        id="code"
                                        type="text"
                                        value={code}
                                        onChange={(e) => setCode(e.target.value)}
                                        placeholder="6位验证码"
                                        className="input-field pl-10 tracking-widest text-center font-mono"
                                        maxLength={6}
                                        required
                                    />
                                </div>
                                <button
                                    type="button"
                                    onClick={handleSendCode}
                                    disabled={!email || isSendingCode || countdown > 0}
                                    className="px-4 py-2 min-w-[100px] rounded-lg border border-border bg-white text-primary font-medium text-sm hover:bg-slate-50 hover:border-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed group/btn"
                                >
                                    {isSendingCode ? (
                                        <Loader2 className="animate-spin mx-auto" size={18} />
                                    ) : countdown > 0 ? (
                                        <span className="font-mono text-text-sub">{countdown}s</span>
                                    ) : (
                                        "发送验证码"
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="btn-primary w-full flex items-center justify-center gap-2 group/submit"
                            >
                                {isLoading ? (
                                    <Loader2 className="animate-spin" />
                                ) : (
                                    <>
                                        <span>登录</span>
                                        <ArrowRight size={18} className="group-hover/submit:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </button>
                        </div>

                    </form>
                </div>

                {/* Footer */}
                <p className="text-center mt-8 text-sm text-text-sub/40">
                    © {new Date().getFullYear()} 51Talk. All rights reserved.
                </p>
            </div>
        </div>
    );
};

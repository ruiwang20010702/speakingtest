import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api';
import { useAuthStore } from '../stores/authStore';
import logo from '../assets/logo.png';

export default function LoginPage() {
    const navigate = useNavigate();
    const login = useAuthStore((state) => state.login);

    const [email, setEmail] = useState('');
    const [code, setCode] = useState('');
    const [step, setStep] = useState<'email' | 'code'>('email');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [countdown, setCountdown] = useState(0);

    const handleSendCode = async () => {
        if (email !== '704778107@qq.com' && !email.endsWith('@51talk.com')) {
            setError('请使用 @51talk.com 邮箱');
            return;
        }

        setLoading(true);
        setError('');

        try {
            await authApi.sendCode(email);
            setStep('code');
            if (email === '704778107@qq.com') {
                setCode('000000'); // Auto-fill dummy code for admin
                setCountdown(0);
            } else {
                setCountdown(60);
            }

            const timer = setInterval(() => {
                setCountdown((prev) => {
                    if (prev <= 1) {
                        clearInterval(timer);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || '发送验证码失败');
        } finally {
            setLoading(false);
        }
    };

    const handleLogin = async () => {
        if (code.length !== 6) {
            setError('请输入6位验证码');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await authApi.login(email, code);
            login(response.data.access_token, email, response.data.name, response.data.role);
            navigate('/');
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || '登录失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-surface p-4">
            <div className="bg-background p-8 rounded-2xl shadow-xl w-full max-w-md border border-gray-100">
                <div className="text-center mb-8">
                    <img src={logo} alt="51Talk" className="h-16 mx-auto mb-4 object-contain" />
                    <h1 className="text-2xl font-bold text-gray-900">口语测评系统</h1>
                    <p className="text-gray-500 mt-2 text-sm font-medium tracking-wide">教师端</p>
                </div>

                {step === 'email' ? (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">企业邮箱</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="yourname@51talk.com"
                                disabled={loading}
                                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-gray-900 placeholder:text-gray-400"
                            />
                        </div>

                        {error && (
                            <div className="text-red-500 text-sm bg-red-50 p-3 rounded-lg flex items-center">
                                <svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {error}
                            </div>
                        )}

                        <button
                            className="w-full bg-primary text-white font-bold py-2.5 px-4 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed shadow-sm active:scale-[0.98]"
                            onClick={handleSendCode}
                            disabled={loading || !email}
                        >
                            {loading ? '发送中...' : '获取验证码'}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">验证码</label>
                            <input
                                type="text"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="请输入6位验证码"
                                disabled={loading}
                                maxLength={6}
                                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-gray-900 placeholder:text-gray-400 tracking-widest text-center text-lg"
                            />
                            <span className="text-xs text-gray-500 mt-2 block text-center">
                                验证码已发送至 <span className="font-medium text-gray-700">{email}</span>
                                {countdown > 0 && <span className="text-primary ml-1">({countdown}s)</span>}
                            </span>
                        </div>

                        {error && (
                            <div className="text-red-500 text-sm bg-red-50 p-3 rounded-lg flex items-center">
                                <svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {error}
                            </div>
                        )}

                        <div className="space-y-3">
                            <button
                                className="w-full bg-primary text-white font-bold py-2.5 px-4 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed shadow-sm active:scale-[0.98]"
                                onClick={handleLogin}
                                disabled={loading || code.length !== 6}
                            >
                                {loading ? '登录中...' : '登录'}
                            </button>

                            <button
                                className="w-full bg-gray-50 text-gray-600 font-medium py-2.5 px-4 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                onClick={() => {
                                    setStep('email');
                                    setCode('');
                                    setError('');
                                }}
                                disabled={loading}
                            >
                                返回修改邮箱
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

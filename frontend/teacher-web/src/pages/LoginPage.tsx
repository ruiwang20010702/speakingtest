import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api';
import { useAuthStore } from '../stores/authStore';
import logo from '../assets/logo.png';
import './LoginPage.css';

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
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <img src={logo} alt="51Talk" className="login-logo" />
                    <h1>口语测评系统</h1>
                    <p>教师端</p>
                </div>

                {step === 'email' ? (
                    <div className="login-form">
                        <div className="form-group">
                            <label>企业邮箱</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="yourname@51talk.com"
                                disabled={loading}
                            />
                        </div>

                        {error && <div className="error-message">{error}</div>}

                        <button
                            className="btn-primary"
                            onClick={handleSendCode}
                            disabled={loading || !email}
                        >
                            {loading ? '发送中...' : '获取验证码'}
                        </button>
                    </div>
                ) : (
                    <div className="login-form">
                        <div className="form-group">
                            <label>验证码</label>
                            <input
                                type="text"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="请输入6位验证码"
                                disabled={loading}
                                maxLength={6}
                            />
                            <span className="hint">
                                验证码已发送至 {email}
                                {countdown > 0 && ` (${countdown}s)`}
                            </span>
                        </div>

                        {error && <div className="error-message">{error}</div>}

                        <button
                            className="btn-primary"
                            onClick={handleLogin}
                            disabled={loading || code.length !== 6}
                        >
                            {loading ? '登录中...' : '登录'}
                        </button>

                        <button
                            className="btn-secondary"
                            onClick={() => {
                                setStep('email');
                                setCode('');
                                setError('');
                            }}
                            disabled={loading}
                        >
                            返回
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import WechatGuide from '../components/WechatGuide';
import { shouldShowWechatGuide } from '../utils/browser';

interface EntryResponse {
    access_token: string;
    student_name: string;
    level: string;
    unit: string;
    test_id: number;
}

const EntryPage: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showWechatGuide, setShowWechatGuide] = useState(false);

    useEffect(() => {
        // 检测 Android 微信环境，显示跳转引导
        // 注意：必须在验证 token 之前检测，否则 token 会被消费
        if (shouldShowWechatGuide()) {
            setShowWechatGuide(true);
            setLoading(false);
            return; // 不验证 token，等用户跳转到浏览器后再验证
        }

        const verifyToken = async () => {
            try {
                // 使用 withCredentials 让浏览器接收 httpOnly Cookie
                const res = await axios.post<EntryResponse>(
                    '/api/v1/students/entry', 
                    { token },
                    { withCredentials: true }
                );
                const { student_name, level, unit, test_id } = res.data;

                // 只存储非敏感的会话信息（token 已通过 httpOnly Cookie 设置）
                localStorage.setItem('studentName', student_name);
                localStorage.setItem('level', level);
                localStorage.setItem('unit', unit);
                localStorage.setItem('testId', test_id.toString());

                // Redirect to test page
                navigate('/test');
            } catch (err: any) {
                setError(err.response?.data?.detail?.message || '无效的链接或链接已过期');
            } finally {
                setLoading(false);
            }
        };

        if (token) {
            verifyToken();
        } else {
            setError('链接无效');
            setLoading(false);
        }
    }, [token, navigate]);

    // 微信环境：显示跳转引导
    if (showWechatGuide) {
        return <WechatGuide isOpen={true} />;
    }

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-[#002FA7]">
                <Loader2 className="w-12 h-12 text-[#FFF59D] animate-spin mb-4" />
                <p className="text-white font-bold">正在进入测评...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-[#002FA7] p-6 text-center">
                <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-6">
                    <span className="text-4xl">⚠️</span>
                </div>
                <h1 className="text-2xl font-black text-white mb-2">无法进入测评</h1>
                <p className="text-white/80 mb-8">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="px-8 py-3 bg-[#FFF59D] text-[#002FA7] font-black rounded-xl shadow-[0_4px_0_#FBC02D] active:shadow-none active:translate-y-[4px] transition-all"
                >
                    重试
                </button>
            </div>
        );
    }

    return null;
};

export default EntryPage;

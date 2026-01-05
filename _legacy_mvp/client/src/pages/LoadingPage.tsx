/**
 * Loading 页面 - 评分分析中
 */
import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import logoImage from '../assets/51talk-logo.png';

export default function LoadingPage() {
    const navigate = useNavigate();
    const location = useLocation();

    // 从 state 获取结果 ID
    const resultId = location.state?.resultId;
    const error = location.state?.error;

    useEffect(() => {
        // 如果有结果 ID，跳转到结果页
        if (resultId) {
            navigate(`/result?id=${resultId}`, { replace: true });
        }
    }, [resultId, navigate]);

    return (
        <div className="min-h-screen relative overflow-hidden bg-[#00B4EE]">
            {/* 装饰元素 */}
            <div className="absolute inset-0">
                {/* 左上黄色圆 */}
                <div className="absolute top-0 left-0 w-40 h-40 bg-[#FDE700] rounded-full -translate-x-1/4 -translate-y-1/4" />
                {/* 右上白云 */}
                <div className="absolute top-0 right-0 w-48 h-32">
                    <div className="absolute top-4 right-0 w-24 h-24 bg-white rounded-full translate-x-1/3" />
                    <div className="absolute top-8 right-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute top-12 right-6 w-16 h-16 bg-white rounded-full" />
                </div>
                {/* 左下白云 */}
                <div className="absolute bottom-0 left-0 w-48 h-32">
                    <div className="absolute bottom-4 left-0 w-24 h-24 bg-white rounded-full -translate-x-1/3" />
                    <div className="absolute bottom-8 left-12 w-20 h-20 bg-white rounded-full" />
                    <div className="absolute bottom-12 left-6 w-16 h-16 bg-white rounded-full" />
                </div>
                {/* 右下黄色三角 */}
                <div className="absolute bottom-0 right-0 w-40 h-40 bg-[#FDE700] translate-x-1/4 translate-y-1/4" style={{ clipPath: 'polygon(0 100%, 100% 100%, 100% 0)' }} />
            </div>

            {/* 内容 */}
            <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
                <div className="bg-white/95 backdrop-blur rounded-3xl shadow-2xl px-12 py-10 text-center">
                    {/* Logo */}
                    <div className="mb-8">
                        <img
                            src={logoImage}
                            alt="51Talk Logo"
                            className="h-14 mx-auto rounded-2xl shadow-lg"
                        />
                    </div>

                    {/* 黄色加载动画 */}
                    <div className="mb-8">
                        <div className="relative w-16 h-16 mx-auto">
                            <div
                                className="absolute inset-0 border-4 border-transparent border-t-[#FDE700] border-r-[#FDE700] rounded-full animate-spin"
                                style={{ animationDuration: '1s' }}
                            />
                        </div>
                    </div>

                    {/* 状态文本 */}
                    <p className="text-[#00B4EE] text-base">
                        正在分析录音，预计等待 1-2 分钟
                    </p>

                    {/* 错误显示和重试按钮 */}
                    {error && (
                        <div className="mt-6">
                            <p className="text-red-500 mb-4">{error}</p>
                            <button
                                onClick={() => navigate(-1)}
                                className="px-6 py-2 bg-[#FDE700] text-gray-900 font-medium rounded-xl hover:shadow-lg transition-all"
                            >
                                返回重试
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

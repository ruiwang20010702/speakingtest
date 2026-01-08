import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';

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

    useEffect(() => {
        const verifyToken = async () => {
            try {
                const res = await axios.post<EntryResponse>('/api/v1/students/entry', { token });
                const { access_token, student_name, level, unit, test_id } = res.data;

                // Store session info
                localStorage.setItem('token', access_token);
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

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-white">
                <Loader2 className="w-12 h-12 text-[#1CB0F6] animate-spin mb-4" />
                <p className="text-[#1E293B] font-bold">正在进入测评...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-white p-6 text-center">
                <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-6">
                    <span className="text-4xl">⚠️</span>
                </div>
                <h1 className="text-2xl font-black text-[#1E293B] mb-2">无法进入测评</h1>
                <p className="text-[#1E293B]/60 mb-8">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="px-8 py-3 bg-[#1CB0F6] text-white font-black rounded-xl shadow-[0_4px_0_#1899D6] active:shadow-none active:translate-y-[4px] transition-all"
                >
                    重试
                </button>
            </div>
        );
    }

    return null;
};

export default EntryPage;

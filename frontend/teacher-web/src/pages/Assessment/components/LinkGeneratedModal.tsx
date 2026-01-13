import React from 'react';
import { CheckCircle, Copy, Download } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

interface LinkGeneratedModalProps {
    isOpen: boolean;
    onClose: () => void;
    link: string;
}

export const LinkGeneratedModal: React.FC<LinkGeneratedModalProps> = ({ isOpen, onClose, link }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" onClick={onClose}></div>

            <div className="relative bg-surface rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200 text-center">

                {/* Success Header */}
                <div className="pt-8 pb-4 px-6 flex flex-col items-center">
                    <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4 shadow-sm animate-in zoom-in duration-300">
                        <CheckCircle size={32} strokeWidth={3} />
                    </div>
                    <h3 className="font-bold text-xl text-text-main">测评链接已生成</h3>
                    <p className="text-sm text-text-sub mt-1">请分享给学生</p>
                </div>

                {/* QR Code Area */}
                <div className="mx-8 my-2 p-6 bg-white border border-border rounded-xl shadow-inner flex flex-col items-center gap-4">
                    {/* Mock QR Code */}
                    <div className="w-40 h-40 bg-white p-2 border border-slate-100 flex items-center justify-center">
                        <QRCodeSVG value={link} size={140} />
                    </div>
                    <button className="text-primary text-sm font-medium flex items-center gap-1 hover:underline">
                        <Download size={14} /> 下载二维码
                    </button>
                </div>

                {/* Link Copy Area */}
                <div className="p-6 bg-slate-50/50 space-y-4">
                    <div className="relative group">
                        <input
                            readOnly
                            value={link}
                            className="w-full pl-3 pr-10 py-2.5 text-sm bg-white border border-border rounded-lg text-text-sub font-mono truncate focus:outline-none"
                        />
                        <button
                            onClick={() => navigator.clipboard.writeText(link)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-primary hover:bg-blue-50 rounded-md transition-colors"
                            title="复制链接"
                        >
                            <Copy size={16} />
                        </button>
                    </div>

                    <button
                        onClick={onClose}
                        className="w-full py-3 rounded-lg bg-text-main text-white font-medium shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
                    >
                        完成
                    </button>
                </div>
            </div>
        </div>
    );
};

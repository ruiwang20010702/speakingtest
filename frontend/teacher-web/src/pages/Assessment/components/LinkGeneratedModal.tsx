import React from 'react';
import { CheckCircle, Copy, Download, X } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { motion, AnimatePresence } from 'framer-motion';

interface LinkGeneratedModalProps {
    isOpen: boolean;
    onClose: () => void;
    link: string;
    title?: string;
    subtitle?: string;
}

export const LinkGeneratedModal: React.FC<LinkGeneratedModalProps> = ({ 
    isOpen, 
    onClose, 
    link,
    title = "测评链接已生成",
    subtitle = "请分享给学生"
}) => {
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    {/* Background Overlay */}
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-slate-900/60 backdrop-blur-md" 
                        onClick={onClose}
                    />

                    {/* Modal Card */}
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="relative bg-surface rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden text-center border border-white/20"
                    >
                        {/* Close Button */}
                        <button 
                            onClick={onClose}
                            className="absolute right-4 top-4 p-2 text-text-sub hover:bg-slate-100 rounded-full transition-colors z-10"
                        >
                            <X size={20} />
                        </button>

                        {/* Success Header */}
                        <div className="pt-10 pb-4 px-6 flex flex-col items-center">
                            <motion.div 
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.2, type: "spring", stiffness: 500, damping: 15 }}
                                className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-6 shadow-sm shadow-green-200"
                            >
                                <CheckCircle size={40} strokeWidth={2.5} />
                            </motion.div>
                            <h3 className="font-bold text-2xl text-text-main">{title}</h3>
                            <p className="text-base text-text-sub mt-2">{subtitle}</p>
                        </div>

                        {/* QR Code Area */}
                        <div className="mx-8 my-4 p-8 bg-white border border-border rounded-2xl shadow-inner flex flex-col items-center gap-4 group">
                            <div className="bg-white p-3 border border-slate-100 rounded-lg shadow-sm group-hover:shadow-md transition-shadow">
                                <QRCodeSVG value={link} size={160} />
                            </div>
                            <button className="text-primary text-sm font-bold flex items-center gap-2 hover:bg-blue-50 px-3 py-1.5 rounded-full transition-colors">
                                <Download size={16} /> 下载二维码
                            </button>
                        </div>

                        {/* Link Copy Area */}
                        <div className="p-8 bg-slate-50/80 space-y-5 border-t border-border">
                            <div className="relative group">
                                <input
                                    readOnly
                                    value={link}
                                    className="w-full pl-4 pr-12 py-3 text-sm bg-white border border-border rounded-xl text-text-sub font-mono truncate focus:outline-none focus:border-primary transition-colors"
                                />
                                <button
                                    onClick={() => {
                                        navigator.clipboard.writeText(link);
                                        // Optional: add a temporary "Copied!" tooltip or feedback
                                    }}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-primary hover:bg-blue-50 rounded-lg transition-colors"
                                    title="复制链接"
                                >
                                    <Copy size={18} />
                                </button>
                            </div>

                            <button
                                onClick={onClose}
                                className="w-full py-4 rounded-xl bg-primary text-white font-bold text-lg shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-1 active:translate-y-0 transition-all duration-200"
                            >
                                完成
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};

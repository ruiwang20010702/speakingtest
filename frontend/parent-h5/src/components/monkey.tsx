import React from 'react';
import { motion } from 'framer-motion';

interface MonkeyProps {
  variant: 'default' | 'glasses' | 'winner';
  className?: string;
  layoutId?: string;
  imageSrc?: string; // 可选的图片路径，如果提供则使用图片而不是 SVG
}

export const Monkey: React.FC<MonkeyProps> = ({ variant, className, layoutId = "monkey", imageSrc }) => {
  // 如果提供了图片路径，使用图片
  const MonkeyContent = imageSrc ? (
    <div className={`relative ${className || 'w-48 h-48'}`}>
      <img 
        src={imageSrc} 
        alt="Monkey" 
        className="w-full h-full object-contain drop-shadow-lg"
      />
    </div>
  ) : (
    <div className={`relative w-48 h-48 ${className}`}>
      <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-lg">
        {/* Head */}
        <circle cx="100" cy="100" r="60" fill="#FBC02D" stroke="#fff" strokeWidth="4" />
        
        {/* Ears */}
        <circle cx="45" cy="90" r="20" fill="#FBC02D" stroke="#fff" strokeWidth="4" />
        <circle cx="155" cy="90" r="20" fill="#FBC02D" stroke="#fff" strokeWidth="4" />
        
        {/* Inner Ear */}
        <circle cx="45" cy="90" r="10" fill="#FFF59D" />
        <circle cx="155" cy="90" r="10" fill="#FFF59D" />

        {/* Headphones connecting band */}
        <path d="M 40 90 Q 100 20 160 90" stroke="#002FA7" strokeWidth="12" fill="none" strokeLinecap="round" />
        
        {/* Headphone Muffs */}
        <rect x="20" y="70" width="30" height="50" rx="10" fill="#002FA7" />
        <rect x="150" y="70" width="30" height="50" rx="10" fill="#002FA7" />

        {/* Face Mask Area */}
        <ellipse cx="100" cy="115" rx="45" ry="35" fill="#FFFDE7" />

        {/* Eyes */}
        <circle cx="85" cy="105" r="6" fill="#000" />
        <circle cx="115" cy="105" r="6" fill="#000" />

        {/* Mouth */}
        {variant === 'winner' ? (
           <path d="M 85 130 Q 100 145 115 130" stroke="#000" strokeWidth="3" fill="none" strokeLinecap="round" />
        ) : (
           <path d="M 90 135 Q 100 140 110 135" stroke="#000" strokeWidth="3" fill="none" strokeLinecap="round" />
        )}

        {/* T-Shirt Body (Partial) */}
        <path d="M 50 160 Q 100 220 150 160 L 150 200 L 50 200 Z" fill="#FFF59D" />

        {/* Glasses Variant */}
        {variant === 'glasses' && (
          <g>
            <circle cx="85" cy="105" r="15" stroke="#000" strokeWidth="2" fill="rgba(255,255,255,0.3)" />
            <circle cx="115" cy="105" r="15" stroke="#000" strokeWidth="2" fill="rgba(255,255,255,0.3)" />
            <line x1="100" y1="105" x2="100" y2="105" stroke="#000" strokeWidth="2" />
            <line x1="70" y1="105" x2="40" y2="90" stroke="#000" strokeWidth="2" />
            <line x1="130" y1="105" x2="160" y2="90" stroke="#000" strokeWidth="2" />
          </g>
        )}

        {/* Winner Badge/Details */}
        {variant === 'winner' && (
           <g transform="translate(130, 20)">
             <path d="M0 0 L10 10 L20 0 L10 30 Z" fill="#FFD700" stroke="#fff" strokeWidth="1" />
           </g>
        )}
      </svg>
    </div>
  );

  if (layoutId) {
    return (
      <motion.div
        layoutId={layoutId}
        transition={{
          type: "spring",
          stiffness: 300,
          damping: 30,
          mass: 0.8
        }}
      >
        {MonkeyContent}
      </motion.div>
    );
  }

  return MonkeyContent;
};


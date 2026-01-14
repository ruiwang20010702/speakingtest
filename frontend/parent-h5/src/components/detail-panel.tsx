import React from 'react';
import { motion } from 'framer-motion';
import { Award, Target, Lightbulb, Sparkles } from 'lucide-react';

interface DetailPanelProps {
  question: string;
  answer: string;
  strengths?: string[];
  issues?: string[];
  suggestion: string;
  standardAnswer: string;
  type: 'best' | 'worst';
}

export const DetailPanel: React.FC<DetailPanelProps> = ({
  question,
  answer,
  strengths,
  issues,
  suggestion,
  standardAnswer,
  type,
}) => {
  const isBest = type === 'best';
  
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="overflow-hidden space-y-1 mt-2"
    >
      <InfoBlock
        label="问题"
        content={question}
        color={isBest ? 'green' : 'red'}
      />
      
      <InfoBlock
        label="孩子的回答"
        content={answer}
        color={isBest ? 'green' : 'red'}
        italic
      />

      {isBest && strengths && (
        <InfoBlock
          label="表现亮点"
          content={`这次回答表现非常出色！${strengths.join('，')}。整体表现流畅自然，值得表扬！`}
          icon={Award}
          color="green"
          highlight
        />
      )}

      {!isBest && issues && (
        <InfoBlock
          label="需要关注"
          content={`这次回答存在一些需要改进的地方：${issues.join('，')}。建议重点练习相关语法点。`}
          icon={Target}
          color="red"
          highlight
        />
      )}

      <InfoBlock
        label="改进建议"
        content={suggestion}
        icon={Lightbulb}
        color="yellow"
        highlight
        multiline
      />

      <InfoBlock
        label="标准答案"
        content={standardAnswer}
        icon={Sparkles}
        color={isBest ? 'green' : 'red'}
        italic
      />
    </motion.div>
  );
};

interface InfoBlockProps {
  label: string;
  content: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  color: 'green' | 'red' | 'yellow';
  highlight?: boolean;
  italic?: boolean;
  multiline?: boolean;
}

const InfoBlock: React.FC<InfoBlockProps> = ({
  label,
  content,
  icon: Icon,
  color,
  highlight = false,
  italic = false,
  multiline = false,
}) => {
  const colorClasses = {
    green: {
      bg: 'bg-green-100',
      border: 'border-green-300',
      text: 'text-green-900',
      icon: 'text-green-700',
    },
    red: {
      bg: 'bg-red-100',
      border: 'border-red-300',
      text: 'text-red-900',
      icon: 'text-red-700',
    },
    yellow: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-300',
      text: 'text-yellow-900',
      icon: 'text-yellow-700',
    },
  };

  const colors = colorClasses[color];

  return (
    <div className={`
      rounded p-1 border
      ${colors.bg} ${colors.border}
    `}>
      <div className="flex items-center space-x-0.5 mb-0.5">
        {Icon && <Icon size={8} className={colors.icon} />}
        <span className={`text-[7px] font-black ${colors.text} uppercase`}>
          {label}
        </span>
      </div>
      <p className={`
        text-[8px] font-bold leading-tight ${colors.text}
        ${italic ? 'italic' : ''}
        ${multiline ? 'whitespace-pre-line' : ''}
      `}>
        {content}
      </p>
    </div>
  );
};


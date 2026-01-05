/**
 * 雷达图组件
 * 用于展示5个维度的能力评估
 */
import { useEffect, useRef } from 'react';
import './RadarChart.css';

interface RadarChartProps {
    data: {
        vocabulary: number;      // 词汇 (0-20)
        sentences: number;       // 整句输出 (0-24)
        fluency: number;         // 流畅度 (0-10)
        pronunciation: number;   // 发音 (0-10)
        confidence: number;      // 自信度 (0-10)
    };
}

export default function RadarChart({ data }: RadarChartProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // 设置画布大小
        const size = 300;
        canvas.width = size;
        canvas.height = size;

        const centerX = size / 2;
        const centerY = size / 2;
        const radius = size / 2 - 40;

        // 清空画布
        ctx.clearRect(0, 0, size, size);

        // 5个维度的标签和最大值
        const dimensions = [
            { label: '词汇', max: 20, value: data.vocabulary },
            { label: '整句输出', max: 24, value: data.sentences },
            { label: '流畅度', max: 10, value: data.fluency },
            { label: '发音', max: 10, value: data.pronunciation },
            { label: '自信度', max: 10, value: data.confidence }
        ];

        const angleStep = (Math.PI * 2) / dimensions.length;

        // 绘制背景网格（5层）
        for (let i = 1; i <= 5; i++) {
            ctx.beginPath();
            const r = (radius / 5) * i;

            dimensions.forEach((_, index) => {
                const angle = angleStep * index - Math.PI / 2;
                const x = centerX + r * Math.cos(angle);
                const y = centerY + r * Math.sin(angle);

                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.closePath();
            ctx.strokeStyle = i === 5 ? '#0088cc' : '#e0e0e0';
            ctx.lineWidth = i === 5 ? 2 : 1;
            ctx.stroke();
        }

        // 绘制轴线
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        dimensions.forEach((_, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);

            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();
        });

        // 绘制数据区域
        ctx.beginPath();
        dimensions.forEach((dim, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const ratio = dim.value / dim.max;
            const r = radius * ratio;
            const x = centerX + r * Math.cos(angle);
            const y = centerY + r * Math.sin(angle);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.closePath();

        // 填充
        ctx.fillStyle = 'rgba(255, 99, 132, 0.2)';
        ctx.fill();

        // 描边
        ctx.strokeStyle = 'rgb(255, 99, 132)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // 绘制数据点
        dimensions.forEach((dim, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const ratio = dim.value / dim.max;
            const r = radius * ratio;
            const x = centerX + r * Math.cos(angle);
            const y = centerY + r * Math.sin(angle);

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = 'rgb(255, 99, 132)';
            ctx.fill();
        });

        // 绘制标签
        ctx.fillStyle = '#333';
        ctx.font = 'bold 13px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        dimensions.forEach((dim, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const labelRadius = radius + 25;
            const x = centerX + labelRadius * Math.cos(angle);
            const y = centerY + labelRadius * Math.sin(angle);

            ctx.fillText(dim.label, x, y);
        });

    }, [data]);

    return (
        <div className="radar-chart">
            <canvas ref={canvasRef}></canvas>
        </div>
    );
}

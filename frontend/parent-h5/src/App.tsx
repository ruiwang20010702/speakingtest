import React, { useState, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Layout } from '@/components/layout';
import { Cover } from '@/pages/cover';
import { RadarPage } from '@/pages/radar';
import { VocabPage } from '@/pages/vocab';
import { DialoguePage } from '@/pages/dialogue';
import { RoadmapPage } from '@/pages/roadmap';
import { BadgePage } from '@/pages/badge';
import { PageState } from '@/types';
import { ReportProvider } from '@/context/ReportContext';

const TOTAL_PAGES = 6;

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageState>(PageState.Cover);
  const [direction, setDirection] = useState(0);
  // 防止动画过程中重复触发翻页
  const isAnimatingRef = useRef(false);

  const handleNext = () => {
    if (currentPage < TOTAL_PAGES - 1 && !isAnimatingRef.current) {
      isAnimatingRef.current = true;
      setDirection(1);
      setCurrentPage((prev) => prev + 1);
      // 动画完成后解锁
      setTimeout(() => { isAnimatingRef.current = false; }, 400);
    }
  };

  const handlePrev = () => {
    if (currentPage > 0 && !isAnimatingRef.current) {
      isAnimatingRef.current = true;
      setDirection(-1);
      setCurrentPage((prev) => prev - 1);
      // 动画完成后解锁
      setTimeout(() => { isAnimatingRef.current = false; }, 400);
    }
  };

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? '100%' : '-100%',
      opacity: 0,
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction < 0 ? '100%' : '-100%',
      opacity: 0,
    }),
  };

  const renderPage = () => {
    switch (currentPage) {
      case PageState.Cover:
        return <Cover />;
      case PageState.Radar:
        return <RadarPage />;
      case PageState.Vocab:
        return <VocabPage />;
      case PageState.Dialogue:
        return <DialoguePage />;
      case PageState.LearningAdvice:
        return <RoadmapPage />;
      case PageState.Badge:
        return <BadgePage />;
      default:
        return <Cover />;
    }
  };

  return (
    <ReportProvider>
    <Layout>
      <div className="relative w-full h-full perspective-1000">
        <AnimatePresence initial={false} custom={direction} mode="wait">
          <motion.div
            key={currentPage}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              x: { type: "spring", stiffness: 300, damping: 30 },
              opacity: { duration: 0.2 }
            }}
            className="absolute w-full h-full cursor-grab active:cursor-grabbing bg-klein"
            // 统一使用 framer-motion 的 drag 处理（同时支持触摸和鼠标）
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.15}
            dragMomentum={false}
            onDragEnd={(e, { offset, velocity }) => {
              const dragVelocity = Math.abs(velocity.x);
              
              // 向左滑动（offset.x < 0）：下一页
              if (offset.x < -60 || (offset.x < -30 && dragVelocity > 300)) {
                handleNext();
              } 
              // 向右滑动（offset.x > 0）：上一页
              else if (offset.x > 60 || (offset.x > 30 && dragVelocity > 300)) {
                handlePrev();
              }
            }}
          >
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </div>
    </Layout>
    </ReportProvider>
  );
};

export default App;


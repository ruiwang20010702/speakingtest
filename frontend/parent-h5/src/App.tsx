import React, { useState } from 'react';
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

// Calculate swipe power to determine if a swipe occurred
const swipeConfidenceThreshold = 5000;
const swipePower = (offset: number, velocity: number) => {
  // 保持方向信息：offset 和 velocity 的符号决定滑动方向
  return offset * Math.abs(velocity);
};

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageState>(PageState.Cover);
  const [direction, setDirection] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);

  const handleNext = () => {
    if (currentPage < TOTAL_PAGES - 1) {
      setDirection(1);
      setCurrentPage((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentPage > 0) {
      setDirection(-1);
      setCurrentPage((prev) => prev - 1);
    }
  };

  // 触摸事件处理（备用方案）
  const minSwipeDistance = 50;
  
  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe) {
      handleNext();
    }
    if (isRightSwipe) {
      handlePrev();
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
            // Enable Dragging for Swipe (鼠标拖拽)
            drag="x"
            dragConstraints={{ left: -200, right: 200 }}
            dragElastic={0.1}
            dragMomentum={false}
            onDragEnd={(e, { offset, velocity }) => {
              // 简化判断逻辑：主要看拖拽距离和速度
              const dragDistance = Math.abs(offset.x);
              const dragVelocity = Math.abs(velocity.x);
              
              // 向左滑动（offset.x < 0）：下一页
              if (offset.x < -80 || (offset.x < -50 && dragVelocity > 0.5)) {
                handleNext();
              } 
              // 向右滑动（offset.x > 0）：上一页
              else if (offset.x > 80 || (offset.x > 50 && dragVelocity > 0.5)) {
                handlePrev();
              }
            }}
            // 触摸事件处理（移动端备用方案）
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
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


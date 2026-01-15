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
const swipeConfidenceThreshold = 10000;
const swipePower = (offset: number, velocity: number) => {
  return Math.abs(offset) * velocity;
};

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageState>(PageState.Cover);
  const [direction, setDirection] = useState(0);

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
            // Enable Dragging for Swipe
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={1}
            onDragEnd={(e, { offset, velocity }) => {
              const swipe = swipePower(offset.x, velocity.x);

              if (swipe < -swipeConfidenceThreshold) {
                handleNext();
              } else if (swipe > swipeConfidenceThreshold) {
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


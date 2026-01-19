import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="relative w-full h-screen bg-klein overflow-hidden text-white selection:bg-baby selection:text-klein">
      {/* Noise Texture Overlay */}
      <div className="bg-noise absolute inset-0 z-50 pointer-events-none" />

      {/* Content Container */}
      <main className="relative z-10 w-full h-full flex flex-col">
        {children}
      </main>

      {/* Decorative Corner Stars */}
      <div className="absolute top-4 right-4 z-0 text-white/20 pointer-events-none">
         <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
           <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
         </svg>
      </div>
       <div className="absolute bottom-20 left-4 z-0 text-baby/20 pointer-events-none">
         <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
           <circle cx="12" cy="12" r="10" />
         </svg>
      </div>
    </div>
  );
};


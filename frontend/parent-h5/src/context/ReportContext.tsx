/**
 * Report Context - Provides report data to all pages.
 */
import React, { createContext, useContext, ReactNode } from 'react';
import { ParentReportData } from '../types';
import { useReportData } from '../hooks/useReportData';

interface ReportContextValue {
  data: ParentReportData | null;
  isLoading: boolean;
  error: string | null;
}

const ReportContext = createContext<ReportContextValue | null>(null);

interface ReportProviderProps {
  children: ReactNode;
}

export function ReportProvider({ children }: ReportProviderProps) {
  const { data, isLoading, error } = useReportData();

  return (
    <ReportContext.Provider value={{ data, isLoading, error }}>
      {children}
    </ReportContext.Provider>
  );
}

export function useReport(): ReportContextValue {
  const context = useContext(ReportContext);
  if (!context) {
    throw new Error('useReport must be used within a ReportProvider');
  }
  return context;
}

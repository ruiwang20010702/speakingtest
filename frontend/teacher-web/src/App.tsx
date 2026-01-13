import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/Login/LoginPage';
import { StudentListPage } from './pages/StudentList/StudentListPage';
import { AssessmentHistoryPage } from './pages/Assessment/AssessmentHistoryPage';
import { ReportPage } from './pages/Report/ReportPage';
import { InterpretationPage } from './pages/Interpretation/InterpretationPage';
import { AdminDashboardPage } from './pages/Admin/AdminDashboardPage';
import { TeacherManagementPage } from './pages/Admin/TeacherManagementPage';
import { TeacherDetailPage } from './pages/Admin/TeacherDetailPage';
import { QuestionBankPage } from './pages/Admin/QuestionBankPage';
import { AuditLogPage } from './pages/Admin/AuditLogPage';
import { FailedTasksPage } from './pages/Admin/FailedTasksPage';
import { useAuthStore } from './stores/authStore';

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Admin Route Component - requires admin role
function AdminRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const role = useAuthStore((state) => state.role);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <StudentListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/student/:id"
          element={
            <ProtectedRoute>
              <AssessmentHistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report/:id"
          element={
            <ProtectedRoute>
              <ReportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interpretation/:id"
          element={
            <ProtectedRoute>
              <InterpretationPage />
            </ProtectedRoute>
          }
        />
        {/* Admin Routes */}
        <Route
          path="/admin/dashboard"
          element={
            <AdminRoute>
              <AdminDashboardPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/teachers"
          element={
            <AdminRoute>
              <TeacherManagementPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/teachers/:id"
          element={
            <AdminRoute>
              <TeacherDetailPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/questions"
          element={
            <AdminRoute>
              <QuestionBankPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/audit-logs"
          element={
            <AdminRoute>
              <AuditLogPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/failed-tasks"
          element={
            <AdminRoute>
              <FailedTasksPage />
            </AdminRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;

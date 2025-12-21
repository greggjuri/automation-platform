/**
 * Main application component.
 *
 * Sets up routing for all pages with lazy loading for code splitting.
 */

import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ProtectedRoute } from './components/auth';

// Lazy load pages for code splitting
const WorkflowsPage = lazy(() => import('./pages/WorkflowsPage').then(m => ({ default: m.WorkflowsPage })));
const WorkflowDetailPage = lazy(() => import('./pages/WorkflowDetailPage').then(m => ({ default: m.WorkflowDetailPage })));
const WorkflowCreatePage = lazy(() => import('./pages/WorkflowCreatePage').then(m => ({ default: m.WorkflowCreatePage })));
const WorkflowEditPage = lazy(() => import('./pages/WorkflowEditPage').then(m => ({ default: m.WorkflowEditPage })));
const ExecutionDetailPage = lazy(() => import('./pages/ExecutionDetailPage').then(m => ({ default: m.ExecutionDetailPage })));
const SecretsPage = lazy(() => import('./pages/SecretsPage').then(m => ({ default: m.SecretsPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));

/** Loading spinner for lazy-loaded routes */
function PageLoader() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-400" />
    </div>
  );
}

/**
 * Root application component with route definitions.
 */
function App() {
  return (
    <>
      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
          },
          success: {
            iconTheme: { primary: '#22c55e', secondary: '#f1f5f9' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#f1f5f9' },
          },
        }}
      />

      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Redirect root to workflows */}
          <Route path="/" element={<Navigate to="/workflows" replace />} />

          {/* Auth routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Workflow routes */}
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/workflows/new" element={<ProtectedRoute><WorkflowCreatePage /></ProtectedRoute>} />
          <Route path="/workflows/:workflowId" element={<WorkflowDetailPage />} />
          <Route path="/workflows/:workflowId/edit" element={<ProtectedRoute><WorkflowEditPage /></ProtectedRoute>} />

          {/* Secrets routes (protected) */}
          <Route path="/secrets" element={<ProtectedRoute><SecretsPage /></ProtectedRoute>} />

          {/* Execution routes */}
          <Route
            path="/workflows/:workflowId/executions/:executionId"
            element={<ExecutionDetailPage />}
          />

          {/* 404 fallback */}
          <Route
            path="*"
            element={
              <div className="min-h-screen bg-slate-900 flex items-center justify-center">
                <div className="text-center">
                  <h1 className="text-4xl font-bold text-white">404</h1>
                  <p className="mt-2 text-slate-400">Page not found</p>
                  <a
                    href="/workflows"
                    className="mt-4 inline-block text-blue-400 hover:text-blue-300"
                  >
                    Go to Workflows
                  </a>
                </div>
              </div>
            }
          />
        </Routes>
      </Suspense>
    </>
  );
}

export default App;

/**
 * Main application component.
 *
 * Sets up routing for all pages.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import {
  WorkflowsPage,
  WorkflowDetailPage,
  WorkflowCreatePage,
  WorkflowEditPage,
  ExecutionDetailPage,
} from './pages';

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

      <Routes>
        {/* Redirect root to workflows */}
        <Route path="/" element={<Navigate to="/workflows" replace />} />

        {/* Workflow routes */}
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/new" element={<WorkflowCreatePage />} />
        <Route path="/workflows/:workflowId" element={<WorkflowDetailPage />} />
        <Route path="/workflows/:workflowId/edit" element={<WorkflowEditPage />} />

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
    </>
  );
}

export default App;

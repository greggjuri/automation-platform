/**
 * Main application component.
 *
 * Sets up routing for all pages.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { WorkflowsPage, WorkflowDetailPage, ExecutionDetailPage } from './pages';

/**
 * Root application component with route definitions.
 */
function App() {
  return (
    <Routes>
      {/* Redirect root to workflows */}
      <Route path="/" element={<Navigate to="/workflows" replace />} />

      {/* Workflow routes */}
      <Route path="/workflows" element={<WorkflowsPage />} />
      <Route path="/workflows/:workflowId" element={<WorkflowDetailPage />} />

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
  );
}

export default App;

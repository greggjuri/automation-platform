/**
 * Execution type definitions.
 *
 * These types match the backend API response format for execution resources.
 */

/** Execution status values */
export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed';

/** Step execution status values */
export type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

/**
 * Result of a single step execution.
 */
export interface ExecutionStep {
  /** Step identifier matching workflow definition */
  step_id: string;
  /** Step name from workflow definition */
  name?: string;
  /** Step type from workflow definition */
  type?: string;
  /** Current status of this step */
  status: StepStatus;
  /** ISO timestamp when step started */
  started_at: string | null;
  /** ISO timestamp when step finished */
  finished_at: string | null;
  /** Duration in milliseconds */
  duration_ms?: number | null;
  /** Input data passed to the step */
  input?: Record<string, unknown>;
  /** Output data from the step (null if failed/pending) */
  output: Record<string, unknown> | null;
  /** Error message if step failed */
  error: string | null;
}

/**
 * A workflow execution record.
 */
export interface Execution {
  /** Workflow that was executed */
  workflow_id: string;
  /** Unique execution identifier (e.g., "ex_01HQ...") */
  execution_id: string;
  /** Workflow name at time of execution */
  workflow_name?: string;
  /** Current execution status */
  status: ExecutionStatus;
  /** What triggered this execution */
  trigger_type?: string;
  /** Data from the trigger event */
  trigger_data?: Record<string, unknown>;
  /** Results for each step */
  steps: ExecutionStep[];
  /** ISO timestamp when execution started */
  started_at: string;
  /** ISO timestamp when execution finished (null if still running) */
  finished_at?: string | null;
  /** Error message if execution failed */
  error?: string | null;
}

/**
 * API response for execution list.
 */
export interface ExecutionListResponse {
  /** List of executions */
  executions: Execution[];
  /** Count of returned items */
  count: number;
  /** Pagination key for next page (undefined if no more pages) */
  last_key?: string;
}

/**
 * API response for triggering an execution.
 */
export interface ExecuteResponse {
  /** Status of the request */
  status: 'queued';
  /** Workflow that was triggered */
  workflow_id: string;
  /** Execution ID if available */
  execution_id?: string;
  /** Human-readable message */
  message: string;
}

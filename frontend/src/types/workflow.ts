/**
 * Workflow type definitions.
 *
 * These types match the backend API response format for workflow resources.
 */

/** Trigger types supported by the platform */
export type TriggerType = 'manual' | 'webhook' | 'cron' | 'poll';

/** Step action types */
export type StepType = 'http_request' | 'transform' | 'log';

/**
 * Workflow trigger configuration.
 */
export interface WorkflowTrigger {
  /** Type of trigger */
  type: TriggerType;
  /** Trigger-specific configuration */
  config: Record<string, unknown>;
}

/**
 * A single step in a workflow.
 */
export interface WorkflowStep {
  /** Unique identifier for this step */
  step_id: string;
  /** Human-readable step name */
  name: string;
  /** Type of action to execute */
  type: StepType;
  /** Step-specific configuration */
  config: Record<string, unknown>;
}

/**
 * A workflow definition.
 */
export interface Workflow {
  /** Unique workflow identifier (e.g., "wf_abc123") */
  workflow_id: string;
  /** Human-readable workflow name */
  name: string;
  /** Optional description */
  description: string;
  /** Whether the workflow is enabled */
  enabled: boolean;
  /** Trigger configuration */
  trigger: WorkflowTrigger;
  /** Ordered list of steps to execute */
  steps: WorkflowStep[];
  /** ISO timestamp of creation */
  created_at: string;
  /** ISO timestamp of last update */
  updated_at: string;
}

/**
 * API response for workflow list.
 */
export interface WorkflowListResponse {
  /** List of workflows */
  workflows: Workflow[];
  /** Total count */
  count: number;
}

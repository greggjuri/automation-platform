/**
 * Workflow type definitions.
 *
 * These types match the backend API response format for workflow resources.
 */

/** Trigger types supported by the platform */
export type TriggerType = 'manual' | 'webhook' | 'cron' | 'poll';

/** Step action types */
export type StepType = 'http_request' | 'transform' | 'log' | 'notify';

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

// =============================================================================
// Form Types (for create/edit UI)
// =============================================================================

/** Form data for creating/editing a workflow */
export interface WorkflowFormData {
  name: string;
  description: string;
  enabled: boolean;
  trigger: TriggerFormData;
  steps: StepFormData[];
}

/** Trigger configuration in form */
export interface TriggerFormData {
  type: 'manual' | 'webhook' | 'cron' | 'poll';
  config: {
    schedule?: string; // For cron type
    url?: string; // For poll type
    interval_minutes?: number; // For poll type
    content_type?: 'rss' | 'atom' | 'http'; // For poll type
  };
}

/** Step configuration in form */
export interface StepFormData {
  step_id: string;
  name: string;
  type: StepType;
  config: HttpRequestConfig | TransformConfig | LogConfig | NotifyConfig;
}

/** HTTP Request step config */
export interface HttpRequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  body?: string;
}

/** Transform step config */
export interface TransformConfig {
  template: string;
  output_key?: string;
}

/** Log step config */
export interface LogConfig {
  message: string;
  level: 'info' | 'warn' | 'error';
}

/** Notify step config */
export interface NotifyConfig {
  channel: 'discord';
  webhook_url: string;
  message: string;
  embed?: boolean;
}

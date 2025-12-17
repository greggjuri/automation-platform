/**
 * Secret types for the automation platform.
 */

/** Types of secrets that can be stored */
export type SecretType = 'discord_webhook' | 'slack_webhook' | 'api_key' | 'custom';

/** Secret metadata (no actual value exposed) */
export interface Secret {
  name: string;
  secret_type: SecretType;
  masked_value: string;
  created_at: string;
}

/** Request body for creating a secret */
export interface CreateSecretRequest {
  name: string;
  value: string;
  secret_type: SecretType;
}

/** Response from listing secrets */
export interface SecretsListResponse {
  secrets: Secret[];
  count: number;
}

/** Response from creating a secret */
export interface CreateSecretResponse extends Secret {
  message: string;
}

/** Response from deleting a secret */
export interface DeleteSecretResponse {
  message: string;
  name: string;
}

/** Secret type display information */
export const SECRET_TYPE_INFO: Record<SecretType, { label: string; placeholder: string }> = {
  discord_webhook: {
    label: 'Discord Webhook',
    placeholder: 'https://discord.com/api/webhooks/...',
  },
  slack_webhook: {
    label: 'Slack Webhook',
    placeholder: 'https://hooks.slack.com/services/...',
  },
  api_key: {
    label: 'API Key',
    placeholder: 'Your API key',
  },
  custom: {
    label: 'Custom',
    placeholder: 'Secret value',
  },
};

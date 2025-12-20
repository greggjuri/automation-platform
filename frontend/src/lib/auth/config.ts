/**
 * Cognito configuration for Automation Platform authentication
 */

export interface CognitoConfig {
  region: string;
  userPoolId: string;
  clientId: string;
}

/**
 * Get Cognito configuration from Vite environment variables
 */
export const cognitoConfig: CognitoConfig = {
  region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
};

/**
 * Check if Cognito is configured
 */
export function isCognitoConfigured(): boolean {
  return Boolean(cognitoConfig.userPoolId && cognitoConfig.clientId);
}

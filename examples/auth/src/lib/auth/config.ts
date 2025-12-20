/**
 * Cognito configuration for Golf Ghost authentication
 */

export interface CognitoConfig {
  region: string;
  userPoolId: string;
  clientId: string;
}

/**
 * Get Cognito configuration from environment variables
 */
export const cognitoConfig: CognitoConfig = {
  region: process.env.NEXT_PUBLIC_COGNITO_REGION || 'us-east-1',
  userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
  clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
};

/**
 * Check if Cognito is configured
 */
export function isCognitoConfigured(): boolean {
  return Boolean(cognitoConfig.userPoolId && cognitoConfig.clientId);
}

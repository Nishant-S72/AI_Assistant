/**
 * User Metadata
 * Edit this file to customize user information without touching component code
 */

export interface UserMetadata {
  name: string;
  email: string;
  title: string;
  company?: string;
  avatar?: {
    initials?: string;
  };
}

// Default metadata - edit these values to customize
export const userMetadata: UserMetadata = {
  name: 'Nishant',
  email: 'demo@example.com',
  title: 'Nishant',
  company: 'Your Company',
  avatar: {
    initials: 'DU',
  },
};

// Helper to get user initials
export function getUserInitials(): string {
  return userMetadata.avatar?.initials || 
    userMetadata.name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
}



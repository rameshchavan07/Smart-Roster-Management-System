/**
 * Unified API Client and Schema Exports conforming to API_DOCUMENTATION.md
 */

export * from './client';
export * from './generated/schema';
export * from './generated/client';

// Re-export existing feature endpoints for convenience
export * from './auth';
export * from './team';
export * from './brands';
export * from './rules';
export * from './leaves';
export * from './rosters';
export * from './audit';


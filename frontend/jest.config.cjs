/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/tests'],
  setupFilesAfterEnv: ['<rootDir>/tests/jest_setup.cjs'],
  testMatch: ['**/test_*.js'],
  testPathIgnorePatterns: ['/node_modules/', 'test_play_narrative_stream\\.js'],
};

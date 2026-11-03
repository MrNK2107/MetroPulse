const nextJest = require('next/jest')

const createJestConfig = nextJest({ dir: './' })

module.exports = createJestConfig({
  testEnvironment: 'jsdom',
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/e2e/', '<rootDir>/.next/'],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    // The worker client uses import.meta.url (unavailable in CommonJS tests); parse inline instead.
    '^@/lib/pulse/import/gtfsWorkerClient$': '<rootDir>/src/lib/pulse/import/gtfsWorkerClient.inline.ts',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
})

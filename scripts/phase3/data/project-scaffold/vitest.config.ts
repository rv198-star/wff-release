import { defineConfig } from "vitest/config";

const maxForks = Number(process.env.PHASE3_VITEST_MAX_FORKS ?? "2");
const boundedMaxForks = Number.isFinite(maxForks) ? Math.max(1, Math.floor(maxForks)) : 2;
const useSingleFork = boundedMaxForks === 1;

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    fileParallelism: !useSingleFork,
    pool: "forks",
    poolOptions: {
      forks: {
        singleFork: useSingleFork,
        isolate: !useSingleFork,
        minForks: 1,
        maxForks: boundedMaxForks,
      },
    },
    hookTimeout: 120000,
    testTimeout: 60000,
    passWithNoTests: false,
    reporters: ["default"],
    coverage: {
      provider: "v8",
      reportsDirectory: "coverage",
      reporter: ["text", "json-summary", "json"],
    },
  },
});

import { z } from "genkit";
import { AgentRunnerOptions, GeminiAgentRunner } from "./gemini";
import { v4 as uuid } from "uuid";
import fs from "fs/promises";
import path from "path";
import { ai } from "./genkit";
import { commandSuccess } from "./eval-actions";

export * from "./genkit";
export * from "./eval-actions";

/**
 * The schema for a test case.
 */
const TestSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  preamble: z.string().optional(),
  postamble: z.string().optional(),
  prompt: z.string(),
});

/**
 * The input schema for the runAgent flow.
 */
const RunAgentInputSchema = z.object({
  workspaceDir: z.string(),
  control: z.boolean().optional(),
  test: TestSchema,
});

/**
 * The output schema for the runAgent flow.
 */
const RunAgentOutputSchema = z.object({
  workspaceDir: z.string(),
  success: z.boolean(),
});

const POSTAMBLE = `\n=== Additional Instructions
  - check for typescript errors using \`npx tsc --noEmit\`
  - abort if you can't fix an issue after three attempts
  - do not try to directly run generated scripts to test behavior`;

async function runAgentLogic(
  input: z.infer<typeof RunAgentInputSchema>,
  strategy: "unified" | "lang",
  sideChannel: any
) {
  const { sendChunk, trace } = sideChannel;
  const invocationId = uuid().substring(0, 6);
  const agent = new GeminiAgentRunner();
  const test = input.test;
  const testId = `${invocationId}-${test.name}`;
  let success = false;

  await fs.cp(input.workspaceDir, path.resolve(testId), {
    recursive: true,
  });
  const testWorkspace = path.resolve(testId);

  // Install skills based on strategy
  const skillsRoot = path.resolve(process.cwd(), "..");
  const strategyDir = strategy === "unified" ? "skills_unified" : "skills_lang";
  const sourceSkillsDir = path.join(skillsRoot, strategyDir);

  try {
    await commandSuccess({
      workspaceDir: testWorkspace,
      payload: `gemini skills install ${sourceSkillsDir} --scope workspace`,
    });
  } catch (e) {
    console.error("Error installing skills:", e);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
  }, 180 * 1000);

  const runnerOpts: AgentRunnerOptions = {
    ai,
    workspaceDir: testWorkspace,
    signal: controller.signal,
    prompt: JSON.stringify(
      "SYSTEM CONTEXT:\nUse the available skills to perform the task.\n\nTASK:\n" +
        test.prompt +
        (test.postamble ?? POSTAMBLE)
    ),
    sendChunk,
    control: input.control,
    spanId: trace.spanId,
    traceId: trace.traceId,
  };
  console.log(`--- Running agent ---`);
  let fileContent;
  let agentResponse;
  try {
    agentResponse = await agent.run(runnerOpts);
    fileContent = await fs.readFile(
      path.resolve(testWorkspace, "src", "index.ts"),
      "utf-8"
    );
    success = true;
  } catch (e) {
    success = false;
    fileContent = "FILE NOT FOUND";
  } finally {
    clearTimeout(timeout);
  }

  await ai.run("index-content", test.prompt, async (): Promise<string> => {
    return fileContent!;
  });

  return {
    workspaceDir: testWorkspace,
    success,
  };
}

/**
 * Runs the Gemini agent with the Unified strategy.
 */
export const runAgentUnified = ai.defineFlow(
  {
    name: "runAgentUnified",
    inputSchema: RunAgentInputSchema,
    outputSchema: RunAgentOutputSchema,
  },
  async (input, sideChannel) => {
    return runAgentLogic(input, "unified", sideChannel);
  }
);

/**
 * Runs the Gemini agent with the Language-Centric strategy.
 */
export const runAgentLang = ai.defineFlow(
  {
    name: "runAgentLang",
    inputSchema: RunAgentInputSchema,
    outputSchema: RunAgentOutputSchema,
  },
  async (input, sideChannel) => {
    return runAgentLogic(input, "lang", sideChannel);
  }
);

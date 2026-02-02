import { spawn } from "child_process";
import fs from "fs/promises";
import { Genkit, StreamingCallback } from "genkit";
import path from "path";
import { parseTelemetryLog } from "./utils";

/**
 * Options for the Gemini agent runner.
 */
export interface AgentRunnerOptions {
  /** An instance of the Genkit AI client. */
  ai: Genkit;
  /** The directory where the agent will run. */
  workspaceDir: string;
  /** The prompt to send to the agent. */
  prompt: string;
  /** Whether this is a control run. */
  control?: boolean;
  /** An optional AbortSignal to cancel the agent run. */
  signal?: AbortSignal;
  /** An optional callback to stream chunks of the agent's output. */
  sendChunk?: StreamingCallback<string>;
  /** The ID of the trace for this agent run. */
  traceId: string;
  /** The ID of the span for this agent run. */
  spanId: string;
}

/**
 * The response from the Gemini agent runner.
 */
export interface AgentRunnerResponse {
  /** Whether the agent run is complete. */
  done?: boolean;
  /** The exit code of the agent process. */
  exitCode?: number;
  /** The output of the agent run. */
  output?: string;
  /** Usage information about the run, only provided on the last chunk. */
  stats?: any;
  /** The ID of the trace for this agent run. */
  traceId?: string;
}

/**
 * Prepares the Gemini environment by creating necessary directories and configuration files.
 * @param geminiDir The directory to store Gemini configuration.
 * @param artifactsDir The directory to store artifacts from the agent run.
 * @param otlpEndpoint The OTLP endpoint for telemetry.
 */
async function prepareForGemini(
  geminiDir: string,
  artifactsDir: string,
  otlpEndpoint: string
) {
  await fs.mkdir(geminiDir, { recursive: true });
  await fs.mkdir(artifactsDir, { recursive: true });
  const settingsFile = path.join(geminiDir, "settings.json");

  let settings: any = {};
  try {
    settings = JSON.parse(await fs.readFile(settingsFile, "utf-8"));
  } catch (e: any) {
    if (e.code !== "ENOENT") {
      throw e;
    }
  }

  settings.telemetry = {
    enabled: true,
    target: "local",
    otlpEndpoint,
    otlpProtocol: "http",
  };
  await fs.writeFile(settingsFile, JSON.stringify(settings, null, 2));
}

/**
 * Runs the Gemini agent as a child process.
 * @param options The options for the agent runner.
 * @param args The arguments to pass to the Gemini agent.
 * @param onChunk A callback to handle chunks of the agent's output.
 * @returns A promise that resolves with the stdout, stderr, and exit code of the agent process.
 */
async function runGemini(
  options: AgentRunnerOptions,
  args: string[],
  onChunk: (chunk: Buffer) => void
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  const child = spawn("gemini", args, {
    cwd: options.workspaceDir,
    env: {
      ...process.env,
      GEMINI_DEV_TRACING: "true",
      GEMINI_MODEL: options.control ? "gemini-2.5-flash" : undefined,
    },
    stdio: ["pipe", "pipe", "pipe"],
  });
  const stdoutChunks: Buffer[] = [];
  const stderrChunks: Buffer[] = [];

  child.stdout?.on("data", (chunk: Buffer) => {
    stdoutChunks.push(chunk);
    onChunk(chunk);
  });
  child.stderr?.on("data", (chunk: Buffer) => {
    stderrChunks.push(chunk);
    onChunk(chunk);
  });

  let exitCode: number;
  try {
    exitCode = await new Promise<number>((resolve, reject) => {
      const onAbort = () => {
        child.kill();
        reject(new Error("Aborted"));
      };
      options.signal?.addEventListener("abort", onAbort);

      child.on("close", (code) => {
        options.signal?.removeEventListener("abort", onAbort);
        resolve(code ?? -1);
      });

      child.on("error", (err) => {
        options.signal?.removeEventListener("abort", onAbort);
        reject(err);
      });
    });
  } catch (err: any) {
    if (err.message === "Aborted") {
      exitCode = -1;
    } else {
      throw err;
    }
  }

  const stdout = Buffer.concat(stdoutChunks as readonly Uint8Array[]).toString(
    "utf-8"
  );
  const stderr = Buffer.concat(stderrChunks as readonly Uint8Array[]).toString(
    "utf-8"
  );

  return { stdout, stderr, exitCode };
}

/**
 * Processes the output of the Gemini agent.
 * @param stdout The stdout of the agent process.
 * @param exitCode The exit code of the agent process.
 * @param artifactsDir The directory where artifacts are stored.
 * @param startTime The start time of the agent run.
 * @returns A promise that resolves with the processed output and stats.
 */
async function processGeminiOutput(
  stdout: string,
  exitCode: number,
  artifactsDir: string,
  startTime: number
): Promise<{ output: string; stats: any }> {
  if (!stdout) {
    return { output: "EMPTY", stats: undefined };
  }

  const outputFile = path.join(artifactsDir, "gemini-output.json");
  await fs.writeFile(outputFile, stdout);

  let json: any;
  try {
    json = JSON.parse(stdout);
  } catch (e: any) {
    if (exitCode !== 0) {
      const match = stdout.match(/{[\s\S]*}/);
      if (match) {
        try {
          json = JSON.parse(match[0]);
        } catch (e2) {
          // ignore
        }
      }
    }
    if (!json) {
      return {
        output: `\nError parsing JSON output: ${e.message}\n`,
        stats: undefined,
      };
    }
  }

  if (json.response) {
    return { output: json.response, stats: undefined };
  }

  let stats: any;
  if (json.stats && json.stats.models) {
    let totalRequests = 0;
    let totalInputTokens = 0;
    let totalCachedInputTokens = 0;
    let totalOutputTokens = 0;

    for (const modelName in json.stats.models) {
      const modelMetrics = json.stats.models[modelName];
      if (modelMetrics.api) {
        totalRequests += modelMetrics.api.totalRequests || 0;
      }
      if (modelMetrics.tokens) {
        totalInputTokens += modelMetrics.tokens.prompt || 0;
        totalCachedInputTokens += modelMetrics.tokens.cached || 0;
        totalOutputTokens += modelMetrics.tokens.candidates || 0;
      }
    }

    stats = {
      requests: totalRequests,
      inputTokens: totalInputTokens,
      cachedInputTokens: totalCachedInputTokens,
      outputTokens: totalOutputTokens,
      durationSeconds: (Date.now() - startTime) / 1000,
    };
  }

  if (json.error) {
    return { output: `\nError: ${json.error.message}\n`, stats };
  }

  return { output: "EMPTY", stats };
}

/**
 * A class to run the Gemini agent.
 */
export class GeminiAgentRunner {
  /**
   * Streams the output of the Gemini agent, filtering out debug messages.
   * @param sendChunk The callback to send the filtered output to.
   * @param chunk The chunk of output from the agent.
   */
  stream(sendChunk: StreamingCallback<string>, chunk: Buffer) {
    const bufString = chunk.toString("utf-8");
    if (!bufString.startsWith("[DEBUG]")) {
      sendChunk(bufString);
    }
  }

  /**
   * Runs the Gemini agent.
   * @param options The options for the agent runner.
   * @returns A promise that resolves with the response from the agent.
   */
  async run(options: AgentRunnerOptions): Promise<AgentRunnerResponse> {
    const startTime = Date.now();
    const geminiDir = path.join(options.workspaceDir, ".gemini");
    const artifactsDir = path.join(options.workspaceDir, `artifacts`);
    const args = [
      "-p",
      options.prompt,
      "-d",
      "--yolo",
      "--output-format",
      "json",
    ];
    const logger = process.stderr;
    const ai = options.ai;
    let stats: any = undefined;

    const agentOut = await ai.run(
      "run-agent",
      args,
      async (args: string[]): Promise<AgentRunnerResponse> => {
        try {
          const telemetryApiUrl = process.env["GENKIT_TELEMETRY_SERVER"]!;
          const otlpEndpoint = `${telemetryApiUrl}/api/otlp/${options.traceId}/${options.spanId}`;

          await prepareForGemini(geminiDir, artifactsDir, otlpEndpoint);

          const { stdout, exitCode } = await runGemini(
            options,
            args,
            (chunk) => {
              if (options.sendChunk) {
                this.stream(options.sendChunk, chunk);
              }
            }
          );

          const result = await processGeminiOutput(
            stdout,
            exitCode,
            artifactsDir,
            startTime
          );
          stats = result.stats;

          if (exitCode !== 0 && !stats) {
            const telemetryFile = path.join(artifactsDir, "telemetry.log");
            stats = await parseTelemetryLog(telemetryFile, (msg) =>
              logger.write(msg)
            );
          }

          // Return output to track in custom span
          return { done: true, output: result.output, stats };
        } finally {
          // Optionally clean up the workspace.
          // await fs.rm(geminiDir, { recursive: true, force: true });
        }
      }
    );
    return agentOut;
  }
}

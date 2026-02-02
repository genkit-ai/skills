import { ai } from "./genkit";
import { BaseEvalDataPoint, EvalStatusEnum } from "genkit/evaluator";
import { spawn } from "child_process";
import fs from "fs/promises";
import path from "path";

/**
 * An evaluator that checks if a TypeScript application compiles successfully.
 */
export const compilesEval = ai.defineEvaluator(
  {
    name: `clix/compiles`,
    displayName: "Compiles success",
    definition: "Checks if a TS app compiles",
    isBilled: false,
  },
  async (datapoint: BaseEvalDataPoint) => {
    const workspaceDir = (datapoint.output as any)?.workspaceDir;
    const { score, message } = await commandSuccess({
      workspaceDir,
      payload: "npx tsc --noEmit",
    });

    return {
      testCaseId: datapoint.testCaseId,
      evaluation: {
        score,
        status: score === 1 ? EvalStatusEnum.PASS : EvalStatusEnum.FAIL,
        details: {
          reasoning: message,
        },
      },
    };
  }
);

/**
 * An evaluator that checks if a command succeeds.
 */
export const commandSuccessEval = ai.defineEvaluator(
  {
    name: `clix/commandSuccess`,
    displayName: "Command success",
    definition: "Checks if a command succeeds",
    isBilled: false,
  },
  async (datapoint: BaseEvalDataPoint) => {
    const payload = (datapoint.reference as any)?.payload ?? "npx tsc --noEmit";
    const workspaceDir = (datapoint.output as any)?.workspaceDir;
    const payloads = Array.isArray(payload) ? payload : [payload];
    const scores: number[] = [];
    const reasonings: string[] = [];
    for (const p of payloads) {
      const { score, message } = await commandSuccess({
        workspaceDir,
        payload: p,
      });

      scores.push(score || 0);
      reasonings.push(message);
    }

    const sum = scores.reduce(
      (accumulator, currentValue) => accumulator + currentValue,
      0
    );
    const avg = sum / scores.length;

    return {
      testCaseId: datapoint.testCaseId,
      evaluation: {
        score: avg,
        details: {
          reasoning: reasonings.join("\n"),
        },
      },
    };
  }
);

/**
 * An evaluator that checks if a file exists in the workspace.
 */
export const fileExistsEval = ai.defineEvaluator(
  {
    name: `clix/fileExists`,
    displayName: "File exists",
    definition: "Checks if a specific file exists in the workspace",
    isBilled: false,
  },
  async (datapoint: BaseEvalDataPoint) => {
    const workspaceDir = (datapoint.output as any)?.workspaceDir;
    const filePath = (datapoint.reference as any)?.filePath;

    if (!filePath) {
      throw new Error("filePath reference is required for fileExistsEval");
    }

    const fullPath = path.resolve(workspaceDir, filePath);
    let exists = false;
    let message = "";

    try {
      await fs.access(fullPath);
      exists = true;
      message = `File found: ${filePath}`;
    } catch (e) {
      exists = false;
      message = `File not found: ${filePath}`;
    }

    return {
      testCaseId: datapoint.testCaseId,
      evaluation: {
        score: exists ? 1 : 0,
        status: exists ? EvalStatusEnum.PASS : EvalStatusEnum.FAIL,
        details: {
          reasoning: message,
        },
      },
    };
  }
);

/**
 * Runs a command and checks if it succeeds.
 * @param params The parameters for the command.
 * @returns A promise that resolves with the score, command, and a message.
 */
export const commandSuccess = async (params: {
  workspaceDir: string;
  payload?: any;
}) => {
  const { workspaceDir, payload } = params;
  if (!payload) {
    return {
      score: 0,
      command: undefined,
      message: "No command provided.",
    };
  }

  const command = typeof payload === "string" ? payload : payload.command;
  const outputContains =
    typeof payload === "string" ? undefined : payload.outputContains;
  const timeout =
    typeof payload === "object" && payload.timeout ? payload.timeout : 10000; // Default 10 second timeout

  const proc = spawn(command, {
    cwd: workspaceDir,
    stdio: ["ignore", "pipe", "pipe"],
    shell: true,
    env: {
      ...process.env,
      GENKIT_ENV: "prod",
    },
  });

  let stdout = "";
  let stderr = "";

  proc.stdout?.on("data", (data) => {
    stdout += data.toString();
  });

  proc.stderr?.on("data", (data) => {
    stderr += data.toString();
  });

  // Create a timeout promise
  const timeoutPromise = new Promise<number>((resolve) => {
    setTimeout(() => {
      proc.kill("SIGTERM"); // Try graceful termination first
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill("SIGKILL"); // Force kill if still running
        }
      }, 1000);
      resolve(-1); // Return -1 to indicate timeout
    }, timeout);
  });

  // Wait for process to exit
  const exitCode = await Promise.race([
    new Promise<number>((resolve, reject) => {
      proc.on("exit", (code) => {
        resolve(code ?? 0);
      });

      proc.on("error", (err) => {
        reject(err);
      });
    }),
    timeoutPromise,
  ]);

  const finalOut = stdout.slice(0, 40).length > 0 ? stdout.slice(0, 40) : "N/A";
  const finalErr = stderr.slice(0, 40).length > 0 ? stderr.slice(0, 40) : "N/A";
  const cmdOutput = `\n\nSTDOUT:\n${finalOut}\n\nSTDERR:\n${finalErr}`;

  await ai.run(
    "command-stdio",
    command,
    async (): Promise<{ stdout: string; stderr: string }> => {
      return { stdout, stderr };
    }
  );

  if (exitCode === -1) {
    return {
      score: 0.0,
      command,
      message: `Command '${command}' timed out after ${timeout}ms.${cmdOutput}`,
    };
  }

  if (exitCode > 0) {
    return {
      score: 0.0,
      command,
      message: `Command '${command}' exited with code ${exitCode}.${cmdOutput}`,
    };
  }

  if (!outputContains) {
    return {
      score: 1.0,
      command,
      message: `Command '${command}' was successful.${cmdOutput}`,
    };
  }

  if (stdout.includes(outputContains)) {
    return {
      score: 1.0,
      command,
      message: `Command '${command}' contained output ${JSON.stringify(
        outputContains
      )}.${cmdOutput}`,
    };
  } else {
    return {
      score: 0.0,
      command,
      message: `Command '${command}' output did not contain ${JSON.stringify(
        outputContains
      )}.${cmdOutput}`,
    };
  }
};

import fs from "fs/promises";

/**
 * Parses a telemetry log file to extract usage statistics.
 * @param logPath The path to the telemetry log file.
 * @param debug A function to log debug messages.
 * @returns A promise that resolves with the parsed statistics, or undefined if the file does not exist or contains no relevant data.
 */
export async function parseTelemetryLog(
  logPath: string,
  debug: (message: string) => void
): Promise<any> {
  let content: string;
  try {
    content = await fs.readFile(logPath, "utf-8");
  } catch (e: any) {
    if (e.code === "ENOENT") {
      return undefined;
    }
    throw e;
  }

  const stats: any = {
    requests: 0,
    inputTokens: 0,
    outputTokens: 0,
    cachedInputTokens: 0,
    durationSeconds: 0,
  };

  const lines = content.split("\n");
  let firstHrTime: [number, number] | undefined;
  let lastHrTime: [number, number] | undefined;
  let inObject = false;
  let currentObjectLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("{")) {
      inObject = true;
      currentObjectLines = [line];
    } else if (inObject) {
      currentObjectLines.push(line);
    }

    if (line.startsWith("}") && inObject) {
      inObject = false;
      try {
        const obj = JSON.parse(currentObjectLines.join("\n"));
        currentObjectLines = [];

        if (obj.hrTime) {
          if (!firstHrTime) {
            firstHrTime = obj.hrTime;
          }
          lastHrTime = obj.hrTime;
        }

        if (obj.attributes?.["event.name"] === "gemini_cli.api_response") {
          stats.requests++;
        }

        if (obj.attributes) {
          for (const key in obj.attributes) {
            if (key.endsWith("_token_count")) {
              const val = obj.attributes[key];
              if (typeof val === "number") {
                if (key === "input_token_count") {
                  stats.inputTokens += val;
                } else if (key === "output_token_count") {
                  stats.outputTokens += val;
                } else if (key === "cached_content_token_count") {
                  stats.cachedInputTokens += val;
                }
              }
            }
          }
        }
      } catch (e: any) {
        debug(`Error parsing telemetry object: ${e.message}\n`);
      }
    }
  }

  if (firstHrTime && lastHrTime) {
    const start = firstHrTime[0] + firstHrTime[1] / 1e9;
    const end = lastHrTime[0] + lastHrTime[1] / 1e9;
    stats.durationSeconds = end - start;
  }

  if (
    stats.requests > 0 ||
    stats.inputTokens > 0 ||
    stats.outputTokens > 0 ||
    stats.cachedInputTokens > 0
  ) {
    return stats;
  }

  return undefined;
}

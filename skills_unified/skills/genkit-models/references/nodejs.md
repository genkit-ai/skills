# Models (Node.js)

## Generate Content

```ts
const { text } = await ai.generate({
  model: googleAI.model('gemini-2.5-flash'),
  prompt: "Hello Genkit",
});
```

## Structured Output

```ts
const { output } = await ai.generate({
  prompt: "Generate a character",
  output: { schema: z.object({ name: z.string() }) },
});
```

## Tools

```ts
const myTool = ai.defineTool({ ... }, (input) => { ... });

const { text } = await ai.generate({
  tools: [myTool],
  prompt: "Use the tool",
});
```

## Gemini Models

### Basic Usage

```ts
import { ai, z } from '...'; // path to genkit instance
import { googleAI } from '@genkit-ai/google-genai';

const { text } = await ai.generate({
  model: googleAI.model('gemini-3-flash-preview'),
  prompt: 'Tell me a story in a pirate accent',
});
```

ALWAYS use `gemini-3-*` or`gemini-2.5-*` series models, they are the best and current generation of Gemini models. NEVER use `gemini-2.0-*` or `gemini-1.5-*` models. For general purpose inference, use one of these models:

- `gemini-3-flash-preview`: balance of speed and performance, good default
- `gemini-3-pro-preview`: most powerful, use for complex prompts
- `gemini-2.5-flash`: GA model with balance of speed/performance
- `gemini-2.5-pro`: GA model for complex prompts
- `gemini-2.5-flash-lite`: GA model for simple prompts

All of these models can accept multi-modal input, but for image or audio output see the available documentation for specialized models.

### Common Usage Scenarios

#### Setting Thinking Level (Gemini 3 Models Only)

```ts
const response = await ai.generate({
  model: googleAI.model('gemini-3-pro-preview'),
  prompt: 'what is heavier, one kilo of steel or one kilo of feathers',
  config: {
    thinkingConfig: {
      thinkingLevel: 'HIGH', // Or 'LOW'
      includeThoughts: true, // Include thought summaries
    },
  },
});
```

#### Google Search Grounding

When enabled, Gemini models can use Google Search to find current information to answer prompts.

```ts
const response = await ai.generate({
  model: googleAI.model('gemini-2.5-flash'),
  prompt: 'What are the top tech news stories this week?',
  config: {
    googleSearchRetrieval: true,
  },
});

// Access grounding metadata
const groundingMetadata = (response.custom as any)?.candidates?.[0]
  ?.groundingMetadata;
if (groundingMetadata) {
  console.log('Sources:', groundingMetadata.groundingChunks);
}
```

## Image Generation (Nano Banana)

The Nano Banana models can perform sophisticated image edits.

- `gemini-2.5-flash-image-preview`

- You must ALWAYS add `{config: {responseModalities: ['TEXT', 'IMAGE']}}` to your `ai.generate` calls when using this model.

<example>
```ts
// generate an image from a prompt

import { ai } from "@/ai/genkit"; // or wherever genkit is initialized
import { googleAI } from "@genkit-ai/google-genai";

const {media} = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-image-preview'),
  config: {responseModalities: ['TEXT', 'IMAGE']}},
  prompt: "generate a picture of a unicorn wearing a space suit on the moon",
});

return media.url; // --> "data:image/png;base64,..."
```
</example>

<example>
```ts
// edit an image with a text prompt

import { ai } from "@/ai/genkit"; // or wherever genkit is initialized
import { googleAI } from "@genkit-ai/google-genai";

const {media} = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-image-preview'),
  config: {responseModalities: ['TEXT', 'IMAGE']}},
  prompt: [
    {text: "change the person's outfit to a banana costume"},
    {media: {url: "https://..." /* or 'data:...' */}},
  ],
});

return media.url; // --> "data:image/png;base64,..."
```
</example>

<example>
```ts
// combine multiple images together

import { ai } from "@/ai/genkit"; // or wherever genkit is initialized
import { googleAI } from "@genkit-ai/google-genai";

const {personImageUri, animalImageUri, sceneryImageUri} = await loadImages(...);

const {media} = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-image-preview'),
  config: {responseModalities: ['TEXT', 'IMAGE']}},
  prompt: [
    // the model tends to match aspect ratio of the *last* image provided
    {text: "[PERSON]:\n"},
    {media: {url: personImageUri}},
    {text: "\n[ANIMAL]:\n"},
    {media: {url: animalImageUri}},
    {text; "\n[SCENERY]:\n"},
    // IMPORTANT: the model tends to match aspect ratio of the *last* image provided
    {media: {url: sceneryImageUri}},
    {text: "make an image of [PERSON] riding a giant version of [ANIMAL] with a background of [SCENERY]"},
  ],
});

return media.url; // --> "data:image/png;base64,..."
```
</example>

<example>
```ts
// use an annotated image to guide generation

import { ai } from "@/ai/genkit"; // or wherever genkit is initialized
import { googleAI } from "@genkit-ai/google-genai";

const originalImageUri = "data:..."; // the original image
const annotatedImageUri = "data:..."; // the image with annotations on top of it

const {media} = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-image-preview'),
  config: {responseModalities: ['TEXT', 'IMAGE']}},
  prompt: [
    
    {text: "follow the instructions in the following annotated image:"},
    {media: {url: annotatedImageUri}},
    {text: "\n\napply the annotated instructions to the original image, making sure to follow the instructions of the annotations.\n\noriginal image:\n"},
    {media: {url: originalImageUri}},
  ],
});

return media.url; // --> "data:image/png;base64,..."
```
</example>

## Prompting tips for image editing

- For complex edits prefer a chain of small edits to a single complex edit. Feed the output of one generation as input to the next.
- Be specific and detailed about the edits you want to make.
- Be clear whether added images are meant as style or subject references.

## Speech Generation (Gemini TTS)

The Google GenAI plugin provides access to text-to-speech capabilities through Gemini TTS models. These models can convert text into natural-sounding speech for various applications.

#### Basic Usage

To generate audio using a TTS model:

```ts
import { googleAI } from '@genkit-ai/google-genai';
import { writeFile } from 'node:fs/promises';
import wav from 'wav'; // npm install wav && npm install -D @types/wav

const ai = genkit({
  plugins: [googleAI()],
});

const { media } = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-preview-tts'),
  config: {
    responseModalities: ['AUDIO'],
    speechConfig: {
      voiceConfig: {
        prebuiltVoiceConfig: { voiceName: 'Algenib' },
      },
    },
  },
  prompt: 'Say that Genkit is an amazing Gen AI library',
});

if (!media) {
  throw new Error('no media returned');
}
const audioBuffer = Buffer.from(media.url.substring(media.url.indexOf(',') + 1), 'base64');
// The googleAI plugin returns raw PCM data, which we convert to WAV format.
await writeFile('output.wav', await toWav(audioBuffer));

async function toWav(pcmData: Buffer, channels = 1, rate = 24000, sampleWidth = 2): Promise<string> {
  return new Promise((resolve, reject) => {
    // This code depends on `wav` npm library.
    const writer = new wav.Writer({
      channels,
      sampleRate: rate,
      bitDepth: sampleWidth * 8,
    });

    let bufs = [] as any[];
    writer.on('error', reject);
    writer.on('data', function (d) {
      bufs.push(d);
    });
    writer.on('end', function () {
      resolve(Buffer.concat(bufs).toString('base64'));
    });

    writer.write(pcmData);
    writer.end();
  });
}
```

#### Multi-speaker Audio Generation

You can generate audio with multiple speakers, each with their own voice:

```ts
const response = await ai.generate({
  model: googleAI.model('gemini-2.5-flash-preview-tts'),
  config: {
    responseModalities: ['AUDIO'],
    speechConfig: {
      multiSpeakerVoiceConfig: {
        speakerVoiceConfigs: [
          {
            speaker: 'Speaker1',
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: 'Algenib' },
            },
          },
          {
            speaker: 'Speaker2',
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: 'Achernar' },
            },
          },
        ],
      },
    },
  },
  prompt: `Here's the dialog:
    Speaker1: "Genkit is an amazing Gen AI library!"
    Speaker2: "I thought it was a framework."`,
});
```

When using multi-speaker configuration, the model automatically detects speaker labels in the text (like "Speaker1:" and "Speaker2:") and applies the corresponding voice to each speaker's lines.

#### Configuration Options

The Gemini TTS models support various configuration options:

##### Voice Selection

You can choose from different pre-built voices with unique characteristics:

```ts
speechConfig: {
  voiceConfig: {
    prebuiltVoiceConfig: {
      voiceName: 'Algenib' // Other options: 'Achernar', 'Ankaa', etc.
    },
  },
}
```

Full list of available voices:

- `Zephyr`: Bright
- `Puck`: Upbeat
- `Charon`: Informative
- `Kore`: Firm
- `Fenrir`: Excitable
- `Leda`: Youthful
- `Orus`: Firm
- `Aoede`: Breezy
- `Callirrhoe`: Easy-going
- `Autonoe`: Bright
- `Enceladus`: Breathy
- `Iapetus`: Clear
- `Umbriel`: Easy-going
- `Algieba`: Smooth
- `Despina`: Smooth
- `Erinome`: Clear
- `Algenib`: Gravelly
- `Rasalgethi`: Informative
- `Laomedeia`: Upbeat
- `Achernar`: Soft
- `Alnilam`: Firm
- `Schedar`: Even
- `Gacrux`: Mature
- `Pulcherrima`: Forward
- `Achird`: Friendly
- `Zubenelgenubi`: Casual
- `Vindemiatrix`: Gentle
- `Sadachbia`: Lively
- `Sadaltager`: Knowledgeable
- `Sulafat`: Warm

##### Speech Emphasis

You can use markdown-style formatting in your prompt to add emphasis:

- Bold text (`**like this**`) for stronger emphasis
- Italic text (`*like this*`) for moderate emphasis

Example:

```ts
prompt: 'Genkit is an **amazing** Gen AI *library*!';
```

##### Advanced Speech Parameters

For more control over the generated speech:

```ts
speechConfig: {
  voiceConfig: {
    prebuiltVoiceConfig: {
      voiceName: 'Algenib',
      speakingRate: 1.0,  // Range: 0.25 to 4.0, default is 1.0
      pitch: 0.0,         // Range: -20.0 to 20.0, default is 0.0
      volumeGainDb: 0.0,  // Range: -96.0 to 16.0, default is 0.0
    },
  },
}
```

- `speakingRate`: Controls the speed of speech (higher values = faster speech)
- `pitch`: Adjusts the pitch of the voice (higher values = higher pitch)
- `volumeGainDb`: Controls the volume (higher values = louder)

For more detailed information about the Gemini TTS models and their configuration options, see the [Google AI Speech Generation documentation](https://ai.google.dev/gemini-api/docs/speech-generation).

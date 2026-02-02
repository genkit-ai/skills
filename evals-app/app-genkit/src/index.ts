import { genkit, z } from 'genkit';

export const ai = genkit({
  plugins: [],
});

export const helloFlow = ai.defineFlow(
  {
    name: 'helloFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (name) => {
    return `Hello, ${name}!`;
  }
);


(async () => {
  const response = await helloFlow('Dave');
  console.log(response); // 'Hello, Dave!'
})();

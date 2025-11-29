import { genkit } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { z } from 'zod'

const ai = genkit({
  plugins: [googleAI()]
})

// Input schema
export const SummarizationInput = z.object({
  transcript: z.string().describe('The transcript text to summarize'),
  caseContext: z.string().optional().describe('Additional case context'),
  outputType: z.enum(['brief', 'detailed', 'legal']).default('brief')
})

export type SummarizationInputType = z.infer<typeof SummarizationInput>

// Key moment schema
const KeyMoment = z.object({
  timestamp: z.string().optional().describe('Timestamp reference if available'),
  description: z.string().describe('Description of the key moment'),
  importance: z.enum(['high', 'medium', 'low']).default('medium'),
  speakers: z.array(z.string()).optional().describe('Speakers involved')
})

// Output schema
export const SummarizationOutput = z.object({
  summary: z.string().describe('Executive summary'),
  keyMoments: z.array(KeyMoment).describe('Important moments from the transcript'),
  actionItems: z.array(z.string()).describe('Action items or follow-ups identified'),
  topics: z.array(z.string()).describe('Main topics discussed'),
  entities: z.object({
    people: z.array(z.string()).optional(),
    organizations: z.array(z.string()).optional(),
    locations: z.array(z.string()).optional(),
    dates: z.array(z.string()).optional()
  }).optional().describe('Named entities extracted')
})

export type SummarizationOutputType = z.infer<typeof SummarizationOutput>

// Summarization flow
export const summarizeTranscript = ai.defineFlow(
  {
    name: 'summarizeTranscript',
    inputSchema: SummarizationInput,
    outputSchema: SummarizationOutput
  },
  async (input) => {
    const { transcript, caseContext, outputType } = input

    const lengthGuidance = {
      brief: '2-3 sentences',
      detailed: '1-2 paragraphs',
      legal: '1 paragraph with legal relevance highlighted'
    }

    const prompt = `
You are a legal document analyst. Analyze this transcript and provide a structured summary.

${caseContext ? `Case Context: ${caseContext}\n` : ''}

Transcript:
${transcript}

Provide your analysis as JSON with this structure:
{
  "summary": "${lengthGuidance[outputType]} summary of the transcript",
  "keyMoments": [
    {
      "timestamp": "optional timestamp or 'N/A'",
      "description": "what happened",
      "importance": "high|medium|low",
      "speakers": ["who was involved"]
    }
  ],
  "actionItems": ["any follow-up actions mentioned or implied"],
  "topics": ["main topics discussed"],
  "entities": {
    "people": ["names mentioned"],
    "organizations": ["companies, firms, agencies"],
    "locations": ["places mentioned"],
    "dates": ["dates, times, deadlines mentioned"]
  }
}

Focus on:
- Admissions or contradictions
- Key facts and evidence discussed
- Legal issues or claims mentioned
- Dates and deadlines
- Agreements or disputes
`

    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-flash'),
      prompt,
      output: { format: 'json', schema: SummarizationOutput }
    })

    return response.output as SummarizationOutputType
  }
)

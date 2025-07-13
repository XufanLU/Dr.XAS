import { z } from 'zod'

export const chatSchema = z.object({
  message: z.string().min(1),
  conversation_id: z.string().optional(),
  agent_id: z.string().optional(),
  meta: z.record(z.any()).optional()
})
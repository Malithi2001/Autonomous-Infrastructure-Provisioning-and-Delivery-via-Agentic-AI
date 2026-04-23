import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: { tool: string; input: string; output: string }[]
  requiresApproval?: boolean
  approvalId?: string
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  isLoading: boolean
  addMessage: (msg: Message) => void
  setLoading: (v: boolean) => void
  setSessionId: (id: string) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setLoading: (v) => set({ isLoading: v }),
  setSessionId: (id) => set({ sessionId: id }),
  clearMessages: () => set({ messages: [], sessionId: null }),
}))

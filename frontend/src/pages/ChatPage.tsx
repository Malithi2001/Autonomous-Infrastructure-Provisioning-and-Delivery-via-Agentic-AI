import { useRef, useEffect, useState } from 'react'
import { Send, Trash2, Bot, User, ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import clsx from 'clsx'
import { useChatStore, Message } from '@/store/chatStore'
import { agentService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

const SUGGESTIONS = [
  'List all running Docker containers',
  'Check system CPU and memory usage',
  'Show recent GitHub Actions workflow runs',
  'Restart the nginx container',
  'Check the health of http://localhost:3000',
]

function MessageBubble({ msg }: { msg: Message }) {
  const [stepsOpen, setStepsOpen] = useState(false)
  const isAssistant = msg.role === 'assistant'

  return (
    <div className={clsx('flex gap-3 animate-slide-up', isAssistant ? 'items-start' : 'items-start flex-row-reverse')}>
      {/* Avatar */}
      <div className={clsx(
        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
        isAssistant ? 'bg-primary-600' : 'bg-surface-600'
      )}>
        {isAssistant ? <Bot size={16} className="text-white" /> : <User size={16} className="text-gray-300" />}
      </div>

      <div className={clsx('flex-1 max-w-[80%]', !isAssistant && 'flex flex-col items-end')}>
        <div className={clsx(
          'px-4 py-3 rounded-xl text-sm leading-relaxed',
          isAssistant
            ? 'bg-surface-800 border border-surface-600 text-gray-100'
            : 'bg-primary-600 text-white'
        )}>
          {isAssistant ? (
            <div className="prose prose-invert prose-sm max-w-none prose-code:bg-surface-700 prose-code:px-1 prose-code:rounded prose-pre:bg-surface-700">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          ) : (
            <p>{msg.content}</p>
          )}
        </div>

        {/* Intermediate steps (tool calls) */}
        {isAssistant && msg.steps && msg.steps.length > 0 && (
          <div className="mt-2 w-full">
            <button
              onClick={() => setStepsOpen(v => !v)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              {stepsOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <Wrench size={11} />
              {msg.steps.length} tool call{msg.steps.length > 1 ? 's' : ''}
            </button>
            {stepsOpen && (
              <div className="mt-2 space-y-2">
                {msg.steps.map((step, i) => (
                  <div key={i} className="bg-surface-900 border border-surface-600 rounded-lg p-3 text-xs font-mono">
                    <p className="text-primary-400 mb-1">→ {step.tool}</p>
                    <p className="text-gray-500 mb-1">Input: {typeof step.input === 'string' ? step.input : JSON.stringify(step.input)}</p>
                    <p className="text-gray-300 whitespace-pre-wrap">{step.output}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-gray-600 mt-1 px-1">
          {formatDistanceToNow(msg.timestamp, { addSuffix: true })}
        </p>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const { messages, sessionId, isLoading, addMessage, setLoading, setSessionId, clearMessages } = useChatStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || isLoading) return

    setInput('')
    addMessage({ id: crypto.randomUUID(), role: 'user', content: msg, timestamp: new Date() })
    setLoading(true)

    try {
      const res = await agentService.chat(msg, sessionId ?? undefined)
      if (res.session_id && !sessionId) setSessionId(res.session_id)
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.output,
        timestamp: new Date(),
        steps: res.intermediate_steps,
        requiresApproval: res.requires_approval,
        approvalId: res.approval_id,
      })
    } catch (err: any) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Error: ${err.response?.data?.detail || err.message || 'Something went wrong.'}`,
        timestamp: new Date(),
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-surface-600 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-white">Agent Chat</h1>
          <p className="text-xs text-gray-500">Natural language DevOps commands</p>
        </div>
        {messages.length > 0 && (
          <button onClick={clearMessages} className="btn-ghost text-xs flex items-center gap-1.5">
            <Trash2 size={13} /> Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="w-14 h-14 bg-primary-600/20 border border-primary-600/30 rounded-2xl flex items-center justify-center">
              <Bot size={28} className="text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white mb-1">Smart DevOps Assistant</h2>
              <p className="text-sm text-gray-500 max-w-sm">
                I can manage Docker containers, trigger CI/CD pipelines, check system health, and more — just ask.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left px-4 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-600 hover:border-primary-600/40 rounded-lg text-sm text-gray-300 hover:text-white transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)
        )}

        {isLoading && (
          <div className="flex gap-3 items-start animate-fade-in">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Bot size={16} className="text-white" />
            </div>
            <div className="bg-surface-800 border border-surface-600 rounded-xl px-4 py-3">
              <div className="flex gap-1.5">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-surface-600 shrink-0">
        <div className="flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me to do something... (Shift+Enter for newline)"
            rows={1}
            className="flex-1 bg-surface-800 border border-surface-600 focus:border-primary-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 resize-none outline-none transition-colors"
            style={{ maxHeight: '120px' }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="btn-primary h-11 w-11 flex items-center justify-center rounded-xl p-0 shrink-0"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-2 text-center">
          High-risk actions require human approval before execution.
        </p>
      </div>
    </div>
  )
}

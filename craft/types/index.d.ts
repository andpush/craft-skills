/** One skill run this session: its expanded prompt is what lands in context. */
export type Invocation = {
  skill: string
  count: number
  /** Estimated tokens of the latest expanded prompt (chars / 4). */
  tokens: number
  /** False once a compaction has summarized it away. */
  isInContext: boolean
}

export type Category = {
  name: string
  tokens: number
  color: string
  kind: 'used' | 'free' | 'buffer' | 'deferred'
}

export type ListedSkill = {
  name: string
  source: string
  pluginName?: string
  tokens: number
}

/** The /context breakdown, as last measured. */
export type Snapshot = {
  detail: 'summary' | 'full'
  model: string
  total: number
  max: number
  percent: number
  autoCompactAt?: number
  categories: Category[]
  skills: {
    total: number
    included: number
    tokens: number
    list: ListedSkill[]
  } | null
}

declare module 'claude-code' {
  interface PluginState {
    'craft': {
      invoked: Invocation[]
      snapshot: Snapshot | null
      error: string | null
    }
  }
}

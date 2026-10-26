import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Invocation, Snapshot } from '../types'

const PANE = 'skill-meter'
const TITLE = 'Skills & context'

const invoked = atom({ plugin: 'craft', key: 'invoked' } as const, [])
const snapshot = atom({ plugin: 'craft', key: 'snapshot' } as const, null)
const error = atom({ plugin: 'craft', key: 'error' } as const, null)

/** Rough token estimate for text the engine does not count for us. */
export const estimateTokens = (text: string) => Math.ceil(text.length / 4)

export const fmt = (n: number) =>
  n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(Math.round(n))

const pad = (text: string, width: number) =>
  text.length >= width ? text.slice(0, Math.max(1, width - 1)) + '…' : text + ' '.repeat(width - text.length)

async function measure($: EngineInterface, detail: 'summary' | 'full') {
  try {
    const usage = await $.session.usage({ breakdown: detail })
    const b = usage.context.breakdown
    if (!b) return

    const next: Snapshot = {
      detail,
      model: b.model,
      total: b.totalTokens,
      max: b.rawMaxTokens,
      percent: b.percentage,
      autoCompactAt: b.autoCompactThreshold,
      categories: b.categories.map(c => ({ name: c.name, tokens: c.tokens, color: c.color, kind: c.kind })),
      skills: b.skills
        ? {
            total: b.skills.totalSkills,
            included: b.skills.includedSkills,
            tokens: b.skills.tokens,
            list: b.skills.skillFrontmatter.map(s => ({
              name: s.name,
              source: s.source,
              pluginName: s.pluginName,
              tokens: s.tokens,
            })),
          }
        : null,
    }
    await update($, snapshot, () => next)
    await update($, error, () => null)
  } catch (err) {
    await update($, error, () => (err instanceof Error ? err.message : String(err)))
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: 'skill-meter',
      description: 'Show skills token cost and context usage in a side pane',
    })
    void $.ui.open({ id: PANE, title: TITLE })
    void measure($, 'summary')

    return started
  })

  on('command.run', { command: 'skill-meter' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    await measure($, 'summary')

    return { text: 'Skill meter pane opened.' }
  })

  // A skill's expanded prompt is what it adds to context when it runs.
  on('skill.prompt', async ($, e, next) => {
    const result = await next(e)
    const tokens = estimateTokens(result.text)
    await update($, invoked, list => {
      const found = list.find(one => one.skill === e.skill)
      const entry: Invocation = {
        skill: e.skill,
        count: (found?.count ?? 0) + 1,
        tokens,
        isInContext: true,
      }

      return found ? list.map(one => (one.skill === e.skill ? entry : one)) : [...list, entry]
    })

    return result
  })

  // After each main-thread turn the engine re-measures; refresh the breakdown then.
  on('session.measure', async ($, e, next) => {
    const result = await next(e)
    if (e.changed.includes('context')) await measure($, 'summary')

    return result
  })

  // A real compaction summarizes earlier skill prompts away.
  on('session.compact', async ($, e, next) => {
    const result = await next(e)
    if (e.trigger !== 'precompute' && e.agentId === undefined) {
      await update($, invoked, list => list.map(one => ({ ...one, isInContext: false }))).catch(() => undefined)
    }

    return result
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const width = Math.max(24, e.props.bodyColumns)
    const snap = await read($, snapshot)
    const runs = await read($, invoked)
    const failed = await read($, error)
    const nameWidth = Math.max(10, width - 16)

    const header = snap ? (
      <Box flexDirection="column">
        <Text bold>
          Context {fmt(snap.total)} / {fmt(snap.max)} ({snap.percent}%)
        </Text>
        <Text dimColor>
          {snap.model}
          {snap.autoCompactAt ? ` · compacts at ${fmt(snap.autoCompactAt)}` : ''}
          {snap.detail === 'full' ? ' · exact' : ' · estimated'}
        </Text>
        <Box>{bar(snap, width - 2).map(seg => <Text color={seg.color}>{seg.text}</Text>)}</Box>
        {snap.categories
          .filter(c => c.tokens > 0)
          .map(c => (
            <Box>
              <Text color={c.color}>{c.kind === 'free' ? '░ ' : '█ '}</Text>
              <Text dimColor={c.kind !== 'used'}>
                {pad(c.name, nameWidth)}
                {fmt(c.tokens).padStart(7)}
              </Text>
            </Box>
          ))}
      </Box>
    ) : (
      <Text dimColor>{failed ? `Could not measure: ${failed}` : 'Measuring after the first reply…'}</Text>
    )

    const listed = snap?.skills?.list ?? []
    const byName = new Map(runs.map(r => [r.skill, r]))
    const rows = [
      ...listed.map(s => ({ name: s.name, listing: s.tokens, run: byName.get(s.name) })),
      ...runs.filter(r => !listed.some(s => s.name === r.skill)).map(r => ({ name: r.skill, listing: 0, run: r })),
    ]
      .map(row => ({ ...row, cost: row.listing + (row.run?.isInContext ? row.run.tokens * row.run.count : 0) }))
      .sort((a, b) => b.cost - a.cost)

    const runTotal = runs.filter(r => r.isInContext).reduce((sum, r) => sum + r.tokens * r.count, 0)

    return (
      <Box flexDirection="column">
        {header}
        <Text> </Text>
        <Text bold>Skills run this session</Text>
        {runs.length === 0 && <Text dimColor>None yet.</Text>}
        {runs.map(r => (
          <Text dimColor={!r.isInContext}>
            {pad(r.skill, nameWidth - 4)}×{String(r.count).padEnd(3)}~{fmt(r.tokens * r.count).padStart(6)}
          </Text>
        ))}
        {runs.length > 0 && (
          <Text dimColor>
            In context now: ~{fmt(runTotal)}
            {runs.some(r => !r.isInContext) ? ' (dim = compacted away)' : ''}
          </Text>
        )}
        <Text> </Text>
        <Text bold>
          Loaded skills{snap?.skills ? ` ${snap.skills.included}/${snap.skills.total} listed · ${fmt(snap.skills.tokens)}` : ''}
        </Text>
        <Text dimColor>Listing is always in context; a run adds its body.</Text>
        {rows.length === 0 && <Text dimColor>No skill listing measured yet.</Text>}
        {rows.map(row => (
          <Text dimColor={!row.run}>
            {pad(row.name, nameWidth)}
            {fmt(row.cost).padStart(7)}
          </Text>
        ))}
        <Text> </Text>
        <Box>
          <Button key="refresh" label="Refresh" hotkey="r" onPress={() => measure($, 'summary')} />
          <Text> </Text>
          <Button key="exact" label="Exact count" hotkey="x" onPress={() => measure($, 'full')} />
        </Box>
      </Box>
    )
  })
}

/** The window as one row of coloured blocks, one segment per category. */
function bar(snap: Snapshot, width: number) {
  const cells = Math.max(10, width)
  const segs: { text: string; color: string }[] = []
  let used = 0
  for (const c of snap.categories) {
    if (c.kind === 'deferred' || c.tokens <= 0) continue
    const n = Math.min(cells - used, Math.round((c.tokens / Math.max(1, snap.max)) * cells))
    if (n <= 0) continue
    segs.push({ text: (c.kind === 'free' ? '░' : '█').repeat(n), color: c.color })
    used += n
  }
  if (used < cells) segs.push({ text: '░'.repeat(cells - used), color: 'inactive' })

  return segs
}

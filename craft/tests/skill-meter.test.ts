import { expect, test } from 'claude-code/testing'

const PANE = { title: 'Skills & context', isFocused: false, bodyColumns: 48, placement: 'dock' } as const

test('records a skill run and leaves its prompt unchanged', async ($, on) => {
  on('skill.prompt', (_$, e) => ({ text: e.text }))

  const out = await $.skill.prompt({ skill: 'demo', text: 'x'.repeat(400) })
  expect(out.text).toBe('x'.repeat(400))
  await $.skill.prompt({ skill: 'demo', text: 'x'.repeat(400) })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({
      plugin: 'craft',
      surface,
      component: 'Pane',
      requestId: 'skill-meter',
      props: { ...PANE, scroll: { top: 0, bodyRows: 40 }, view: {} } as never,
    })
    const rows = await ui.findAll({ type: 'Text', text: /demo/ })
    expect(rows.length).toBeGreaterThan(0)
    expect(await ui.find({ type: 'Text', text: /×2/ })).toBeDefined()
    await ui.unmount()
  }
})

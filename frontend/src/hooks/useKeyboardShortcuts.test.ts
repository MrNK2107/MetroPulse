import { renderHook } from '@testing-library/react'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'
import { useSimulationStore } from '@/store/simulationStore'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('useKeyboardShortcuts', () => {
  it('Ctrl+Enter clicks the run button', () => {
    const btn = document.createElement('button')
    btn.setAttribute('data-run-btn', '')
    const clickSpy = jest.spyOn(btn, 'click').mockImplementation(() => {})
    document.body.appendChild(btn)

    renderHook(() => useKeyboardShortcuts())

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true, bubbles: true }))

    expect(clickSpy).toHaveBeenCalled()
    document.body.removeChild(btn)
    clickSpy.mockRestore()
  })

  it('Escape exits draw mode', () => {
    useSimulationStore.getState().setDrawMode('polygon')
    renderHook(() => useKeyboardShortcuts())

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))

    expect(useSimulationStore.getState().drawMode).toBe('none')
  })

  it('ArrowRight advances frame when pipeline is done', () => {
    const store = useSimulationStore.getState()
    store.setSimulationId('test-id')
    store.addFrame({
      month: 1, timestamp: '', cells: [],
      metrics: { gdpDelta: 0, unemploymentRate: 0, realEstateIndex: 0, transitCongestion: 0, informalEmployment: 0, housingAffordability: 0, floodDisruption: 0, migrationBalance: 0 },
      activeLoop: 'primary', proof: { formula: '', dataQuality: '', cellCount: 0, activeEffects: [] },
    } as any)
    store.addFrame({
      month: 2, timestamp: '', cells: [],
      metrics: { gdpDelta: 0, unemploymentRate: 0, realEstateIndex: 0, transitCongestion: 0, informalEmployment: 0, housingAffordability: 0, floodDisruption: 0, migrationBalance: 0 },
      activeLoop: 'primary', proof: { formula: '', dataQuality: '', cellCount: 0, activeEffects: [] },
    } as any)
    store.setActiveFrameIndex(0)

    renderHook(() => useKeyboardShortcuts())

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))

    expect(useSimulationStore.getState().activeFrameIndex).toBe(1)
  })
})

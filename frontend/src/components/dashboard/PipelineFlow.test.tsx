import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { PipelineFlow } from './PipelineFlow'
import { useSimulationStore } from '@/store/simulationStore'
import type { StageEntry } from '@/store/simulationStore'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('PipelineFlow', () => {
  it('renders nothing when pipeline is idle', () => {
    const { container } = render(<PipelineFlow />)
    expect(container.firstChild).toBeNull()
  })

  it('renders all 5 pipeline stages when active', () => {
    useSimulationStore.getState().setStage('parsing', 'Parsing scenario...')

    render(<PipelineFlow />)

    expect(screen.getByText('Prompt')).toBeInTheDocument()
    expect(screen.getByText('Expectation')).toBeInTheDocument()
    expect(screen.getByText('Simulation')).toBeInTheDocument()
    expect(screen.getByText('Evidence')).toBeInTheDocument()
    expect(screen.getByText('Social Impact')).toBeInTheDocument()
  })

  it('highlights the current active stage', () => {
    useSimulationStore.getState().setStage('simulating', 'Running simulation...')

    const { container } = render(<PipelineFlow />)

    // The active stage should have blue styling
    const stageElements = container.querySelectorAll('[class*="border-blue-500"]')
    expect(stageElements.length).toBe(1)

    // Verify the active stage text is within it
    const activeStage = stageElements[0]
    expect(activeStage.textContent).toContain('Simulation')
  })

  it('marks completed stages with emerald styling', () => {
    // Simulate parsing complete, currently simulating
    useSimulationStore.setState({
      pipelineStage: 'simulating',
      stageHistory: [
        { stage: 'parsing', message: 'Done', status: 'complete' },
        { stage: 'predicting', message: 'Done', status: 'complete' },
        { stage: 'simulating', message: 'Running...', status: 'active' },
      ] as StageEntry[],
    })

    const { container } = render(<PipelineFlow />)

    // Completed stages should have emerald classes
    const completedElements = container.querySelectorAll('[class*="border-emerald-800"]')
    expect(completedElements.length).toBeGreaterThanOrEqual(2)
  })

  it('shows the latest stage message', () => {
    useSimulationStore.setState({
      pipelineStage: 'simulating',
      stageHistory: [
        { stage: 'parsing', message: 'Parsing complete', status: 'complete' },
        { stage: 'simulating', message: 'Running month 3 of 12...', status: 'active' },
      ] as StageEntry[],
    })

    render(<PipelineFlow />)

    expect(screen.getByText('Running month 3 of 12...')).toBeInTheDocument()
  })

  it('renders stage labels in correct order', () => {
    useSimulationStore.getState().setStage('parsing', 'Starting...')

    const { container } = render(<PipelineFlow />)

    const labels = ['Prompt', 'Expectation', 'Simulation', 'Evidence', 'Social Impact']
    const stageContainer = container.querySelector('.flex.items-center.gap-1')
    const textContent = stageContainer?.textContent

    labels.forEach((label) => {
      expect(textContent).toContain(label)
    })

    // Verify order: Prompt comes before Expectation, etc.
    const promptIdx = textContent!.indexOf('Prompt')
    const expectIdx = textContent!.indexOf('Expectation')
    const simIdx = textContent!.indexOf('Simulation')
    const evidenceIdx = textContent!.indexOf('Evidence')
    const socialIdx = textContent!.indexOf('Social Impact')

    expect(promptIdx).toBeLessThan(expectIdx)
    expect(expectIdx).toBeLessThan(simIdx)
    expect(simIdx).toBeLessThan(evidenceIdx)
    expect(evidenceIdx).toBeLessThan(socialIdx)
  })

  it('shows connector lines between stages', () => {
    useSimulationStore.getState().setStage('simulating', 'Running...')

    const { container } = render(<PipelineFlow />)

    // There should be 4 connector dividers (between 5 stages)
    const connectors = container.querySelectorAll('.h-\\[1px\\]')
    expect(connectors.length).toBe(4)
  })

  it('renders during parsing stage', () => {
    useSimulationStore.getState().setStage('parsing', 'Understanding scenario...')

    render(<PipelineFlow />)

    expect(screen.getByText('Prompt')).toBeInTheDocument()
    expect(screen.getByText('Understanding scenario...')).toBeInTheDocument()
  })

  it('renders during done stage', () => {
    useSimulationStore.setState({
      pipelineStage: 'done',
      stageHistory: [
        { stage: 'parsing', message: 'Done', status: 'complete' },
        { stage: 'predicting', message: 'Done', status: 'complete' },
        { stage: 'simulating', message: 'Done', status: 'complete' },
        { stage: 'retrieving', message: 'Done', status: 'complete' },
        { stage: 'synthesizing', message: 'Done', status: 'complete' },
      ] as StageEntry[],
    })

    render(<PipelineFlow />)

    // Should still be visible (not idle)
    expect(screen.getByText('Prompt')).toBeInTheDocument()
  })
})

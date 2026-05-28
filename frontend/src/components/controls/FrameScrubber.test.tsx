import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { FrameScrubber } from './FrameScrubber'
import { useSimulationStore } from '@/store/simulationStore'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('FrameScrubber', () => {
  it('renders nothing when pipeline is idle', () => {
    const { container } = render(<FrameScrubber />)
    expect(container.firstChild).toBeNull()
  })

  it('shows playback controls when pipeline is done with frames', () => {
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

    render(<FrameScrubber />)

    // Should render slider and month indicator
    expect(screen.getByRole('slider')).toBeInTheDocument()
    expect(screen.getByText(/Month 2 \/ 2/)).toBeInTheDocument()
  })

  it('shows range slider with correct range', () => {
    const store = useSimulationStore.getState()
    store.setSimulationId('test-id')
    const frame = {
      month: 1, timestamp: '', cells: [],
      metrics: { gdpDelta: 0, unemploymentRate: 0, realEstateIndex: 0, transitCongestion: 0, informalEmployment: 0, housingAffordability: 0, floodDisruption: 0, migrationBalance: 0 },
      activeLoop: 'primary', proof: { formula: '', dataQuality: '', cellCount: 0, activeEffects: [] },
    }
    for (let i = 0; i < 6; i++) {
      store.addFrame({ ...frame, month: i + 1 } as any)
    }

    render(<FrameScrubber />)

    const slider = screen.getByRole('slider')
    expect(slider).toHaveAttribute('min', '0')
    expect(slider).toHaveAttribute('max', '5')
  })
})

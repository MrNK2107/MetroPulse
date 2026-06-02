import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { SimulationProgress } from './SimulationProgress'
import { useSimulationStore } from '@/store/simulationStore'
import type { StageEntry } from '@/store/simulationStore'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('SimulationProgress (LoadingOverlay)', () => {
  it('renders nothing when idle', () => {
    const { container } = render(<SimulationProgress />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when done', () => {
    useSimulationStore.getState().setStage('done', 'Complete')

    const { container } = render(<SimulationProgress />)
    expect(container.firstChild).toBeNull()
  })

  it('shows loading text during parsing stage', () => {
    useSimulationStore.getState().setStage('parsing', 'Understanding scenario...')

    render(<SimulationProgress />)

    expect(screen.getByText('parsing...')).toBeInTheDocument()
  })

  it('shows loading text during predicting stage', () => {
    useSimulationStore.getState().setStage('predicting', 'Generating expectations...')

    render(<SimulationProgress />)

    expect(screen.getByText('predicting...')).toBeInTheDocument()
  })

  it('shows simulation progress with frame count', () => {
    useSimulationStore.setState({
      pipelineStage: 'simulating',
      parsedScenario: { horizon_months: 12 } as any,
      frames: [
        { month: 1 } as any,
        { month: 2 } as any,
        { month: 3 } as any,
      ],
    })

    render(<SimulationProgress />)

    expect(screen.getByText('Simulating 3 / 12')).toBeInTheDocument()
  })

  it('shows simulation progress with 0 frames', () => {
    useSimulationStore.setState({
      pipelineStage: 'simulating',
      parsedScenario: { horizon_months: 24 } as any,
      frames: [],
    })

    render(<SimulationProgress />)

    expect(screen.getByText('Simulating 0 / 24')).toBeInTheDocument()
  })

  it('renders a progress bar', () => {
    useSimulationStore.getState().setStage('parsing', 'Parsing...')

    const { container } = render(<SimulationProgress />)

    // The progress bar wrapper
    const progressBar = container.querySelector('.bg-blue-500')
    expect(progressBar).toBeInTheDocument()
  })

  it('shows error state with error message', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Something went wrong',
      errorStage: 'simulating',
    })

    render(<SimulationProgress />)

    expect(screen.getByText(/Error:/)).toBeInTheDocument()
    expect(
      screen.getByText(/Something went wrong/)
    ).toBeInTheDocument()
  })

  it('shows specific error hint for parsing stage', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Parse error',
      errorStage: 'parsing',
    })

    render(<SimulationProgress />)

    expect(
      screen.getByText(/Parse error/)
    ).toBeInTheDocument()
  })

  it('shows specific error hint for predicting stage', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Predict error',
      errorStage: 'predicting',
    })

    render(<SimulationProgress />)

    expect(
      screen.getByText(/Predict error/)
    ).toBeInTheDocument()
  })

  it('shows specific error hint for retrieving stage', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Retrieve error',
      errorStage: 'retrieving',
    })

    render(<SimulationProgress />)

    expect(
      screen.getByText(/Retrieve error/)
    ).toBeInTheDocument()
  })

  it('shows specific error hint for synthesizing stage', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Synth error',
      errorStage: 'synthesizing',
    })

    render(<SimulationProgress />)

    expect(
      screen.getByText(/Synth error/)
    ).toBeInTheDocument()
  })

  it('falls back to raw error when stage has no hint', () => {
    useSimulationStore.setState({
      pipelineStage: 'error',
      error: 'Unknown failure mode',
      errorStage: null,
    })

    render(<SimulationProgress />)

    expect(screen.getByText('Unknown failure mode')).toBeInTheDocument()
  })

  it('shows retrieving stage text', () => {
    useSimulationStore.getState().setStage('retrieving', 'Finding case studies...')

    render(<SimulationProgress />)

    expect(screen.getByText('retrieving...')).toBeInTheDocument()
  })

  it('shows synthesizing stage text', () => {
    useSimulationStore.getState().setStage('synthesizing', 'Building report...')

    render(<SimulationProgress />)

    expect(screen.getByText('synthesizing...')).toBeInTheDocument()
  })
})

import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import { ScenarioPanel } from './ScenarioPanel'
import { useSimulationStore } from '@/store/simulationStore'

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    startSimulation: jest.fn(),
    stopSimulation: jest.fn(),
  }),
}))

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('ScenarioPanel', () => {
  it('renders textarea with default scenario text', () => {
    render(<ScenarioPanel />)
    const textarea = screen.getByPlaceholderText(/Describe a city-level event/)
    expect(textarea).toBeInTheDocument()
    expect(textarea).toHaveValue(useSimulationStore.getState().scenarioText)
  })

  it('calls setScenarioText on input change', () => {
    render(<ScenarioPanel />)
    const textarea = screen.getByPlaceholderText(/Describe a city-level event/)
    fireEvent.change(textarea, { target: { value: 'new scenario' } })
    expect(useSimulationStore.getState().scenarioText).toBe('new scenario')
  })

  it('shows run button when idle', () => {
    render(<ScenarioPanel />)
    expect(screen.getByText('Run Simulation')).toBeInTheDocument()
  })

  it('shows error banner when error is set', () => {
    useSimulationStore.getState().setError('Something went wrong')
    render(<ScenarioPanel />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows parsed scenario city', () => {
    useSimulationStore.getState().setParsedScenario({
      city: 'Hyderabad',
      sector_deltas: { it_ites: 10 },
      policies_active: ['Digital India'],
      public_works_zone: null,
      horizon_months: 24,
      causal_chain: '',
      keywords: [],
      confidence: 'medium',
      assumptions: ['test assumption'],
    })
    render(<ScenarioPanel />)
    expect(screen.getByText('Digital India')).toBeInTheDocument()
    expect(screen.getByText(/test assumption/)).toBeInTheDocument()
  })
})

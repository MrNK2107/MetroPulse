import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { ConversationPanel } from './ConversationPanel'
import { useSimulationStore } from '@/store/simulationStore'

// scrollIntoView is not available in jsdom
beforeAll(() => {
  Element.prototype.scrollIntoView = jest.fn()
})

// Mock useWebSocket to avoid real WS connections
const mockStartSimulation = jest.fn()
const mockStopSimulation = jest.fn()
const mockSendResponse = jest.fn()

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    startSimulation: mockStartSimulation,
    stopSimulation: mockStopSimulation,
    sendResponse: mockSendResponse,
  }),
}))

// Mock PresetSelector to isolate ConversationPanel tests
jest.mock('./PresetSelector', () => ({
  PresetSelector: () => <div data-testid="preset-selector">PresetSelector Mock</div>,
}))

beforeEach(() => {
  useSimulationStore.getState().resetAll()
  // resetAll doesn't reset conversationMode, so force it back to quick
  useSimulationStore.setState({ conversationMode: 'quick' })
  mockStartSimulation.mockClear()
  mockStopSimulation.mockClear()
  mockSendResponse.mockClear()
})

describe('ConversationPanel', () => {
  it('renders in quick mode by default', () => {
    render(<ConversationPanel />)

    // Default conversationMode is "quick"
    expect(screen.getByText('What If? Simulator')).toBeInTheDocument()
    // Quick mode shows PresetSelector
    expect(screen.getByTestId('preset-selector')).toBeInTheDocument()
    // Quick mode shows scenario examples
    expect(screen.getByText('Try a scenario')).toBeInTheDocument()
  })

  it('switches between quick and direct mode', () => {
    render(<ConversationPanel />)

    // Start in quick mode
    expect(screen.getByText('What If? Simulator')).toBeInTheDocument()
    expect(screen.getByTestId('preset-selector')).toBeInTheDocument()

    // Switch to deep mode via the "Direct Parameters" button
    const deepModeBtn = screen.getAllByText('Direct Parameters')
    fireEvent.click(deepModeBtn[0])

    // Should now show direct parameter controls
    expect(screen.getByText('Target City')).toBeInTheDocument()
    expect(screen.getByText('Simulation Horizon')).toBeInTheDocument()
    expect(screen.getByText('Active Policy Interventions')).toBeInTheDocument()
    expect(screen.getByText('Sector Modifications')).toBeInTheDocument()
    // PresetSelector should not be visible in deep mode
    expect(screen.queryByTestId('preset-selector')).not.toBeInTheDocument()

    // Switch back to quick mode
    fireEvent.click(screen.getByText('What If?'))

    expect(screen.getByText('What If? Simulator')).toBeInTheDocument()
    expect(screen.getByTestId('preset-selector')).toBeInTheDocument()
  })

  it('shows error state', () => {
    useSimulationStore.setState({
      error: 'Simulation failed due to extreme scenario',
    })

    render(<ConversationPanel />)

    expect(screen.getByText('Simulation failed due to extreme scenario')).toBeInTheDocument()
  })

  it('shows policy toggles in deep mode', () => {
    // Set a parsed scenario so deep mode has data
    useSimulationStore.setState({
      conversationMode: 'deep',
      parsedScenario: {
        city: 'mumbai',
        sector_deltas: {},
        policies_active: ['SEZ Notification', 'Smart City Mission'],
        public_works_zone: null,
        horizon_months: 24,
        causal_chain: '',
        keywords: [],
        confidence: 'medium',
        assumptions: [],
      } as any,
    })

    render(<ConversationPanel />)

    // Check policy toggles are shown
    expect(screen.getByText('SEZ Notification')).toBeInTheDocument()
    expect(screen.getByText('Smart City Mission')).toBeInTheDocument()
    expect(screen.getByText('AMRUT')).toBeInTheDocument()
    expect(screen.getByText('RERA Compliance')).toBeInTheDocument()
    expect(screen.getByText('PM Awas Yojana')).toBeInTheDocument()
    expect(screen.getByText('Make in India')).toBeInTheDocument()
    expect(screen.getByText('Digital India')).toBeInTheDocument()
  })

  it('run button has data-run-btn attribute in quick mode', () => {
    // Set scenario text long enough to enable the run button
    useSimulationStore.setState({
      scenarioText: 'What happens to Mumbai if real estate prices drop significantly?',
    })

    render(<ConversationPanel />)

    const runBtn = document.querySelector('[data-run-btn]')
    expect(runBtn).toBeInTheDocument()
    expect(runBtn).toHaveTextContent('Run Simulation')
    expect(runBtn).not.toBeDisabled()
  })

  it('run button is disabled when scenario text is too short', () => {
    useSimulationStore.setState({
      scenarioText: 'short',
    })

    render(<ConversationPanel />)

    const runBtn = document.querySelector('[data-run-btn]')
    expect(runBtn).toBeInTheDocument()
    expect(runBtn).toBeDisabled()
  })

  it('displays quick example prompts', () => {
    render(<ConversationPanel />)

    expect(screen.getByText(/petrol prices spike in Mumbai/)).toBeInTheDocument()
    expect(screen.getByText(/tech boom in Bengaluru/)).toBeInTheDocument()
    expect(screen.getByText(/Heavy rainfall devastates Chennai/)).toBeInTheDocument()
    expect(screen.getByText(/interest rates rise sharply/)).toBeInTheDocument()
  })

  it('clicking an example prompt sets scenario text', () => {
    render(<ConversationPanel />)

    fireEvent.click(screen.getByText(/petrol prices spike in Mumbai/))

    const store = useSimulationStore.getState()
    expect(store.scenarioText).toBe('What if petrol prices spike in Mumbai?')
  })

  it('shows chat messages when present', () => {
    useSimulationStore.setState({
      conversationMessages: [
        { role: 'user', text: 'What if tech booms?', timestamp: Date.now() },
        { role: 'system', text: 'I will simulate this scenario.', timestamp: Date.now() },
      ],
    })

    render(<ConversationPanel />)

    expect(screen.getByText('What if tech booms?')).toBeInTheDocument()
    expect(screen.getByText('I will simulate this scenario.')).toBeInTheDocument()
  })

  it('shows stop button when simulation is running', () => {
    useSimulationStore.setState({
      scenarioText: 'What happens to Mumbai if real estate prices drop significantly?',
      pipelineStage: 'simulating',
    })

    render(<ConversationPanel />)

    expect(screen.getByText('Stop')).toBeInTheDocument()
    expect(screen.queryByText('Run Simulation')).not.toBeInTheDocument()
  })

  it('clicking stop calls stopSimulation', () => {
    useSimulationStore.setState({
      scenarioText: 'What happens to Mumbai if real estate prices drop significantly?',
      pipelineStage: 'simulating',
    })

    render(<ConversationPanel />)

    fireEvent.click(screen.getByText('Stop'))
    expect(mockStopSimulation).toHaveBeenCalled()
  })

  it('shows MetroPulse header branding', () => {
    render(<ConversationPanel />)

    expect(screen.getByText('MetroPulse')).toBeInTheDocument()
  })
})

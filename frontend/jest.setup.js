require('@testing-library/jest-dom/jest-globals')

// Tests never reach the network. jsdom ships a real XMLHttpRequest and WebSocket, and
// Node may expose a real fetch, so all three are replaced with stand-ins that throw and
// record the attempt; the test then fails in afterEach even if the code swallowed the
// error. Tests install their own mocks (global.fetch = jest.fn(), installMockWebSocket())
// over these. The backend suite has the same rule (backend/tests/conftest.py).
const { afterEach, expect } = require('@jest/globals')

const blockedAttempts = []

function block(what) {
  blockedAttempts.push(what)
  return new Error(`network access blocked in tests: ${what} (mock it instead)`)
}

globalThis.fetch = function blockedFetch(input) {
  const url = typeof input === 'string' ? input : (input && input.url) || String(input)
  return Promise.reject(block(`fetch(${url})`))
}

if (typeof window !== 'undefined') {
  window.WebSocket = globalThis.WebSocket = function BlockedWebSocket(url) {
    throw block(`new WebSocket(${url})`)
  }
  if (window.XMLHttpRequest) {
    window.XMLHttpRequest.prototype.send = function blockedSend() {
      throw block('XMLHttpRequest.send')
    }
  }
}

afterEach(() => {
  const attempts = blockedAttempts.splice(0)
  expect(attempts).toEqual([])
})

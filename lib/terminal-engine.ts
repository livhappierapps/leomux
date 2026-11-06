// EdenMux output renderer retained; no fake/simulated shell engine.
export interface TerminalLine { id: string; type: 'input' | 'output' | 'error' | 'info' | 'success' | 'warning' | 'system'; content: string }

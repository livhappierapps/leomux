import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { LeoClient } from './shell-client';
import type { TerminalLine } from './terminal-engine';
import type { Proposal, ServerMessage } from './protocol';
import { LeoApproval, type Approval } from '@/modules/leo-approval';

type Session = { id: string; name: string; lines: TerminalLine[]; cwd: string };
type Chat = { id: string; role: string; text: string };
function useController() {
  const [sessions, setSessions] = useState<Session[]>([{ id: 'leo', name: 'leo · tmux', lines: [], cwd: '~' }]);
  const [activeSessionId, setActiveSession] = useState('leo');
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState('Disconnected');
  const [pending, setPending] = useState<Proposal[]>([]);
  const [messages, setMessages] = useState<Chat[]>([]);
  const [listening, setListening] = useState(false);
  const [paired, setPaired] = useState(false);
  const client = useRef<LeoClient | null>(null);
  const seq = useRef(0);
  const voiceActive = useRef(false);
  const append = (text: string, type: TerminalLine['type'] = 'output') => setSessions(prev => prev.map(s => s.id === 'leo'
    ? { ...s, lines: [...s.lines, { id: String(++seq.current), content: text, type }].slice(-500) } : s));
  const chatLine = (role: string, text: string) => setMessages(p => [...p, { id: String(++seq.current), role, text }].slice(-60));
  const onMessage = (m: ServerMessage) => {
    switch (m.type) {
      case 'hello': setConnected(true); setStatus('Connected · leo'); break;
      case 'status': setStatus(m.state); setPending(p => p.filter(x => m.pending.includes(x.id))); break;
      case 'proposed':
        setPending(p => p.some(x => x.id === m.id) ? p : [...p, m]);
        append('$ ' + m.cmd + '\n[awaiting swipe approval]', 'input'); break;
      case 'decision': setPending(p => p.filter(x => x.id !== m.id)); chatLine('system', `${m.id}: ${m.decision}`); break;
      case 'output': append(m.data); break;
      case 'exit': append(`${m.id} · exit ${m.code}`, m.code === 0 ? 'success' : 'error'); break;
      case 'alert': chatLine('security', m.msg); break;
      case 'error': voiceActive.current = false; setListening(false); chatLine('error', m.msg); break;
      case 'chat': chatLine('Leo', m.text); break;
      case 'transcript': chatLine('Liv', m.text); break;
      case 'voice': voiceActive.current = m.state !== 'idle'; setListening(m.state !== 'idle'); break;
    }
  };
  // These callbacks do not depend on render state; updater functions avoid stale closures.
  useEffect(() => {
    const c = new LeoClient(onMessage, reason => { setConnected(false); setPending([]); setListening(false); setStatus(reason); });
    client.current = c;
    LeoApproval?.isPaired().then(setPaired).catch(() => setPaired(false));
    const subscription = AppState.addEventListener('change', state => {
      if (state !== 'active' && !voiceActive.current) { c.close(); setConnected(false); setPending([]); setListening(false); setStatus('UI disconnected in background; Termux server is independent.'); }
    });
    return () => { subscription.remove(); c.close(); };
  // Mount exactly one client; no automatic retries or command replay.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const perform = (fn: (c: LeoClient) => void) => {
    try { if (!client.current) throw Error('Client not ready'); fn(client.current); }
    catch (e) { chatLine('error', e instanceof Error ? e.message : 'Operation failed'); }
  };
  const connect = async (newToken?: string, approvalKey?: string) => {
    try {
      if (Platform.OS !== 'android') throw Error('Termux/secure approvals require Android. iOS is layout-only.');
      if (approvalKey) {
        if (!LeoApproval) throw Error('Native approval module missing; use a development build, not Expo Go.');
        await LeoApproval.installKey(approvalKey.trim()); setPaired(true);
      }
      if (newToken) await SecureStore.setItemAsync('leomux.socket-token', newToken.trim());
      const token = await SecureStore.getItemAsync('leomux.socket-token');
      if (!token) throw Error('Enter the local socket token from Termux first.');
      client.current?.connect(token);
    } catch (e) { chatLine('error', e instanceof Error ? e.message : 'Pairing failed'); }
  };
  return {
    sessions, activeSessionId, setActiveSession, activeSession: sessions.find(s => s.id === activeSessionId) ?? sessions[0],
    // Additional tabs are output notes, not extra shells (brain always uses tmux leo).
    createNewSession: () => setSessions(p => [...p, { id: String(++seq.current), name: 'Notes', lines: [], cwd: '~' }]),
    closeSession: (id: string) => { if (id !== 'leo') { setSessions(p => p.filter(s => s.id !== id)); setActiveSession('leo'); } },
    connected, status, pending, messages, listening, paired, connect,
    disconnect: () => { client.current?.close(); setConnected(false); setPending([]); setListening(false); },
    propose: (cmd: string) => perform(c => { setActiveSession('leo'); c.propose(cmd); }),
    sendMessage: (text: string) => perform(c => { c.chat(text); chatLine('Liv', text); }),
    listen: () => perform(c => { c.listen(); voiceActive.current = true; setListening(true); }),
    approve: (approval: Approval) => perform(c => c.approve(approval)),
    deny: (id: string) => perform(c => c.deny(id)),
    control: (type: 'pause' | 'resume' | 'stop') => perform(c => c.control(type)),
    report: (text: string) => chatLine('security', text),
  };
}
type Controller = ReturnType<typeof useController>;
const TerminalContext = createContext<Controller | null>(null);
export function TerminalProvider({ children }: { children: React.ReactNode }) {
  const value = useController();
  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}
export function useTerminal() { const value = useContext(TerminalContext); if (!value) throw Error('Missing TerminalProvider'); return value; }

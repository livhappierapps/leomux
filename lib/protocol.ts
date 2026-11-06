import { Buffer } from 'buffer';
export const MAX_LINE = 1 << 20;
export type Risk = { level: 'low' | 'medium' | 'high' | 'critical'; tags: string[] };
export type Proposal = { type: 'proposed'; id: string; cmd: string; reason: string; risk: Risk;
  nonce: string; cmd_hash: string; session_id: string; deadline: number; timeout: number };
export type ServerMessage =
  | Proposal
  | { type: 'hello'; ok: boolean; version: number; session_id: string }
  | { type: 'status'; state: string; paused: boolean; running: string | null; pending: string[] }
  | { type: 'decision'; id: string; decision: string }
  | { type: 'output'; id: string; data: string; stream: string }
  | { type: 'exit'; id: string; code: number; summary: string }
  | { type: 'error'; msg: string }
  | { type: 'alert'; msg: string; level: string }
  | { type: 'voice'; state: string }
  | { type: 'transcript'; text: string }
  | { type: 'chat'; role: 'leo'; text: string }
  | { type: 'pong' };

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
export function decode(line: Buffer): ServerMessage {
  const m: unknown = JSON.parse(line.toString('utf8'));
  if (!isObject(m) || typeof m.type !== 'string') throw Error('Invalid NDJSON message');
  const stringFields: Record<string, string[]> = {
    proposed: ['id', 'cmd', 'reason', 'nonce', 'cmd_hash', 'session_id'],
    hello: ['session_id'], status: ['state'], decision: ['id', 'decision'],
    output: ['id', 'data', 'stream'], exit: ['id', 'summary'], error: ['msg'],
    alert: ['msg', 'level'], voice: ['state'], transcript: ['text'], chat: ['text'], pong: [],
  };
  const fields = stringFields[m.type];
  if (!fields || fields.some(f => typeof m[f] !== 'string')) throw Error('Invalid server fields');
  if (m.type === 'hello' && (m.ok !== true || m.version !== 2)) throw Error('LeoMux protocol v2 required');
  if (m.type === 'proposed') {
    if (!isObject(m.risk) || !['low', 'medium', 'high', 'critical'].includes(String(m.risk.level)) ||
        !Array.isArray(m.risk.tags) || m.risk.tags.some(t => typeof t !== 'string') ||
        typeof m.deadline !== 'number' || !Number.isFinite(m.deadline) || typeof m.timeout !== 'number' ||
        !/^[0-9a-f]{64}$/.test(String(m.nonce)) || !/^[0-9a-f]{64}$/.test(String(m.cmd_hash)) ||
        !/^[0-9a-f]{32}$/.test(String(m.session_id))) throw Error('Invalid proposal');
  }
  if (m.type === 'status' && (typeof m.paused !== 'boolean' ||
      !(m.running === null || typeof m.running === 'string') || !Array.isArray(m.pending))) throw Error('Invalid status');
  if (m.type === 'exit' && typeof m.code !== 'number') throw Error('Invalid exit');
  return m as ServerMessage;
}
export class Framer {
  private bytes: Buffer = Buffer.alloc(0);
  feed(chunk: Uint8Array): ServerMessage[] {
    this.bytes = Buffer.concat([this.bytes, Buffer.from(chunk)]);
    const messages: ServerMessage[] = [];
    let end: number;
    while ((end = this.bytes.indexOf(10)) >= 0) {
      if (end + 1 > MAX_LINE) throw Error('NDJSON message too large');
      const line = this.bytes.subarray(0, end);
      this.bytes = this.bytes.subarray(end + 1);
      if (line.toString('utf8').trim()) messages.push(decode(line));
    }
    if (this.bytes.length > MAX_LINE) throw Error('NDJSON message too large');
    return messages;
  }
}
export function encode(message: object) {
  const data = JSON.stringify(message) + '\n';
  if (Buffer.byteLength(data) > MAX_LINE) throw Error('NDJSON message too large');
  return data;
}

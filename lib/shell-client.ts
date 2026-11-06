import TcpSocket from 'react-native-tcp-socket';
import { Framer, encode, type ServerMessage } from './protocol';
import type { Approval } from '@/modules/leo-approval';

/** Native TCP, NOT WebSocket. Termux lives on this Android device. */
export class LeoClient {
  private socket: ReturnType<typeof TcpSocket.createConnection> | null = null;
  private heartbeat: ReturnType<typeof setInterval> | null = null;
  private authed = false;
  private session = '';
  constructor(private onMessage: (m: ServerMessage) => void, private onDisconnect: (reason: string) => void) {}
  connect(token: string) {
    this.close();
    const framer = new Framer();
    const socket = TcpSocket.createConnection({ host: '127.0.0.1', port: 8765, connectTimeout: 5000 }, () => {
      socket.write(encode({ type: 'hello', token, client: 'leomux' }));
    });
    this.socket = socket;
    socket.on('data', data => {
      if (this.socket !== socket) return;
      try {
        for (const message of framer.feed(typeof data === 'string' ? new TextEncoder().encode(data) : data)) {
          if (!this.authed) {
            if (message.type !== 'hello' || !message.ok) throw Error('Hello-first authentication failed');
            this.authed = true; this.session = message.session_id;
            this.heartbeat = setInterval(() => this.send({ type: 'ping' }), 3000);
            this.send({ type: 'status' });
          }
          this.onMessage(message);
        }
      } catch (error) {
        this.close(); this.onDisconnect(error instanceof Error ? error.message : 'Protocol error');
      }
    });
    socket.on('error', () => {
      if (this.socket === socket) { this.close(); this.onDisconnect('Could not connect. Start leo_server in Termux first.'); }
    });
    socket.on('close', () => {
      if (this.socket === socket) { this.close(); this.onDisconnect('Disconnected; no commands will be retried.'); }
    });
  }
  private send(message: object) {
    if (!this.authed || !this.socket) throw Error('Connect to Termux first');
    this.socket.write(encode(message));
  }
  propose(cmd: string) { this.send({ type: 'propose', cmd, reason: 'Manual proposal from LeoMux' }); }
  chat(text: string) { this.send({ type: 'chat', text }); }
  listen() { this.send({ type: 'voice.listen' }); }
  control(type: 'pause' | 'resume' | 'stop' | 'status') { this.send({ type }); }
  deny(id: string) { this.send({ type: 'decision', id, decision: 'deny' }); }
  approve(approval: Approval) {
    if (approval.session_id !== this.session) throw Error('Stale session; reconnect and request a fresh proposal');
    this.send({ type: 'decision', decision: 'approve', ...approval });
  }
  close() {
    if (this.heartbeat) clearInterval(this.heartbeat);
    this.heartbeat = null; this.authed = false; this.session = '';
    const socket = this.socket; this.socket = null; socket?.destroy();
  }
}

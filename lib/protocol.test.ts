import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Buffer } from 'buffer';
import { Framer, encode, MAX_LINE } from './protocol';

test('NDJSON survives split multibyte UTF-8 and merged TCP reads', () => {
  const data = Buffer.from(encode({ type: 'output', id: 'a', stream: 'pty', data: 'héllo 🎙\nworld' }) + encode({ type: 'pong' }));
  const f = new Framer(); const messages = [];
  for (const byte of data) messages.push(...f.feed(Buffer.from([byte])));
  assert.deepEqual(messages, [{ type: 'output', id: 'a', stream: 'pty', data: 'héllo 🎙\nworld' }, { type: 'pong' }]);
});
test('invalid schemas, old protocol and complete/incomplete oversize frames fail closed', () => {
  for (const bad of ['[]\n', '{"type":"decision"}\n', '{"type":"hello","ok":true,"version":1,"session_id":"x"}\n'])
    assert.throws(() => new Framer().feed(Buffer.from(bad)));
  assert.throws(() => new Framer().feed(Buffer.from(' '.repeat(MAX_LINE) + '\n')));
  assert.throws(() => new Framer().feed(Buffer.from(' '.repeat(MAX_LINE + 1))));
  assert.throws(() => encode({ data: 'x'.repeat(MAX_LINE) }));
});
test('native approval payload fields roundtrip without executing anything', () => {
  const proposal = { type: 'proposed', id: 'a', cmd: 'pwd', reason: 'test', risk: { level: 'low', tags: [] },
    nonce: '01'.repeat(32), cmd_hash: '02'.repeat(32), session_id: '03'.repeat(16), deadline: 99999, timeout: 60 };
  assert.deepEqual(new Framer().feed(Buffer.from(encode(proposal))), [proposal]);
});

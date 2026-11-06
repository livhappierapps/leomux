/** EdenPanel's top-right floating layout, portrait background and chat bubbles.
 * Voice is the DEFAULT; typing is an explicit fallback. No paywalls; STT uses the configured Android recognizer.
 */
import { useState } from 'react';
import { View, Text, TextInput, ScrollView, Pressable, ImageBackground, StyleSheet, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTerminal } from '@/lib/terminal-context';
import { SwipeApproval } from '@/modules/leo-approval';
import PairingSettings from './PairingSettings';
export default function LeoPanel() {
  const [open, setOpen] = useState(true); const [typing, setTyping] = useState(false);
  const [settings, setSettings] = useState(false); const [input, setInput] = useState('');
  const [reach, setReach] = useState(false);
  const { width, height } = useWindowDimensions(); const insets = useSafeAreaInsets();
  const terminal = useTerminal(); const proposal = terminal.pending[0];
  const submit = () => { if (input.trim()) { terminal.sendMessage(input); setInput(''); } };
  // Pending approvals always re-open the trust pane, but never approve by themselves.
  const visible = open || !!proposal;
  return <View style={[styles.outer, reach ? { bottom: insets.bottom + 80 } : { top: insets.top + 74 }, { right: 10 }]}>
    {!visible ? <Pressable accessibilityLabel="Open Leo voice pane" onPress={() => setOpen(true)} style={styles.bubble}><Text style={styles.text}>Leo 🎙</Text></Pressable> :
      <ImageBackground source={require('@/assets/images/eden-portrait.jpeg')} imageStyle={{ opacity: .14 }}
        style={[styles.panel, { width: Math.min(340, width - 20), maxHeight: height - insets.top - insets.bottom - 100 }]}>
        <View style={styles.header}><Text style={styles.title}>Leo · voice first</Text>
          <Pressable accessibilityLabel="Connection settings" onPress={() => setSettings(!settings)} style={styles.small}><Text style={styles.text}>⚙</Text></Pressable>
          <Pressable accessibilityLabel="Move pane to thumb reach" onPress={() => setReach(!reach)} style={styles.small}><Text style={styles.text}>↕</Text></Pressable>
          <Pressable accessibilityLabel="Collapse pane" onPress={() => setOpen(false)} style={styles.small}><Text style={styles.text}>−</Text></Pressable>
        </View>
        {settings ? <PairingSettings /> : <>
          <ScrollView style={{ maxHeight: proposal ? 100 : 150 }} contentContainerStyle={{ padding: 10, gap: 8 }}>
            {terminal.messages.length === 0 && <Text style={styles.dim}>Tap the microphone to talk to Leo. Shell proposals always wait for your swipe. Voice can never approve.</Text>}
            {terminal.messages.map(m => <View key={m.id} style={[styles.chat, m.role === 'Liv' && { alignSelf: 'flex-end', backgroundColor: '#49313f' }]}>
              <Text style={styles.dim}>{m.role}</Text><Text selectable style={styles.text}>{m.text}</Text>
            </View>)}
          </ScrollView>
          {proposal && <View style={styles.approval}>
            <Text style={styles.dim}>Review the entire command. Swipe from the left; hold at the end, then release.</Text>
            <SwipeApproval key={proposal.nonce} style={{ height: 230 }} proposal={JSON.stringify({ ...proposal, risk: proposal.risk.level })}
              onApproved={e => terminal.approve(e.nativeEvent)} onBlocked={e => terminal.report(e.nativeEvent.message)} />
            <Pressable style={styles.deny} onPress={() => terminal.deny(proposal.id)}><Text style={styles.text}>Deny & pause</Text></Pressable>
          </View>}
          <View style={styles.controls}>
            {!typing ? <Pressable disabled={!terminal.connected || terminal.listening} accessibilityLabel="Talk to Leo using Termux speech recognition"
              style={styles.mic} onPress={terminal.listen}><Text style={styles.title}>{terminal.listening ? '🎙 Listening / thinking…' : '🎙 Talk to Leo'}</Text></Pressable> :
              <View style={styles.inputRow}><TextInput value={input} onChangeText={setInput} placeholder="Talk with Leo…" placeholderTextColor="#ad8d9f"
                style={[styles.text, { flex: 1, minHeight: 48 }]} onSubmitEditing={submit} /><Pressable onPress={submit} style={styles.small}><Text style={styles.text}>Send</Text></Pressable></View>}
            <Pressable onPress={() => setTyping(!typing)} style={styles.small}><Text style={styles.dim}>{typing ? 'Use voice' : 'Type instead'}</Text></Pressable>
          </View>
        </>}
        {/* Emergency STOP is intentionally immediate; making STOP require a swipe would slow safety. */}
        <View style={styles.footer}><Pressable onPress={() => terminal.control('stop')} style={styles.stop} accessibilityLabel="Emergency stop Termux leo session"><Text style={styles.text}>■ STOP</Text></Pressable>
          <Pressable onPress={() => terminal.control('resume')} style={styles.small}><Text style={styles.dim}>Resume</Text></Pressable></View>
      </ImageBackground>}
  </View>;
}
const styles = StyleSheet.create({ outer: { position: 'absolute', zIndex: 100, elevation: 12 }, panel: { backgroundColor: '#21131e', borderWidth: 1, borderColor: '#ae4c70', borderRadius: 16, overflow: 'hidden' }, bubble: { backgroundColor: '#65233f', padding: 16, borderRadius: 30 }, text: { color: '#f5e6d8', fontSize: 13 }, dim: { color: '#c6a0b3', fontSize: 11 }, title: { color: '#f9ccdf', fontSize: 15, fontFamily: 'Cinzel_700Bold' }, header: { flexDirection: 'row', alignItems: 'center', paddingLeft: 12, borderBottomWidth: 1, borderColor: '#573345' }, small: { padding: 12, minHeight: 48, justifyContent: 'center' }, chat: { backgroundColor: '#38202e', borderRadius: 12, padding: 9, maxWidth: '94%' }, approval: { paddingHorizontal: 10, paddingVertical: 8, gap: 8 }, deny: { backgroundColor: '#543440', padding: 12, alignItems: 'center', borderRadius: 8, minHeight: 48 }, controls: { borderTopWidth: 1, borderColor: '#573345', padding: 10, alignItems: 'center' }, mic: { backgroundColor: '#71304e', padding: 14, width: '100%', alignItems: 'center', borderRadius: 12, minHeight: 56 }, inputRow: { flexDirection: 'row', width: '100%' }, footer: { flexDirection: 'row', justifyContent: 'space-between', padding: 10 }, stop: { backgroundColor: '#a42a45', borderRadius: 10, padding: 14, minWidth: 140, alignItems: 'center' } });

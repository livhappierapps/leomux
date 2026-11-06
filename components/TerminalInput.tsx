import { useState } from 'react';
import { View, TextInput, Pressable, Text, StyleSheet } from 'react-native';
import { useTerminal } from '@/lib/terminal-context';
import { useTerminalColors } from '@/lib/theme-context';
export default function TerminalInput() {
  const [cmd, setCmd] = useState('');
  const { propose, connected } = useTerminal(); const tc = useTerminalColors();
  const submit = () => { if (cmd.trim() && connected) { propose(cmd); setCmd(''); } };
  return <View style={[styles.row, { borderColor: tc.border }]}>
    <TextInput accessibilityLabel="Manual command proposal" value={cmd} onChangeText={setCmd} autoCorrect={false}
      autoCapitalize="none" placeholder="Manual command → review in Leo pane" placeholderTextColor={tc.textDim}
      style={[styles.input, { color: tc.text }]} onSubmitEditing={submit} editable={connected} />
    <Pressable disabled={!connected} onPress={submit} style={styles.button}><Text style={{ color: tc.rose }}>Propose</Text></Pressable>
  </View>;
}
const styles = StyleSheet.create({ row: { flexDirection: 'row', padding: 8, borderTopWidth: 1 }, input: { flex: 1, minHeight: 48, fontFamily: 'JetBrainsMono_400Regular', fontSize: 12 }, button: { padding: 12, justifyContent: 'center' } });

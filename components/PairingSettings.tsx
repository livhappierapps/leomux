import { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useTerminal } from '@/lib/terminal-context';
export default function PairingSettings() {
  const [token, setToken] = useState(''); const [key, setKey] = useState('');
  const { connect, paired } = useTerminal();
  return <View style={styles.box}>
    <Text style={styles.text}>In Termux: python termux/leo.py pair. Enter these private values only here. Never send them to Leo or GitHub.</Text>
    <TextInput value={token} onChangeText={setToken} secureTextEntry autoCapitalize="none" autoCorrect={false}
      accessibilityLabel="Per-install socket token" placeholder="Socket token" placeholderTextColor="#ad8d9f" style={styles.input} />
    <TextInput value={key} onChangeText={setKey} secureTextEntry autoCapitalize="none" autoCorrect={false}
      accessibilityLabel="Separate approval signing key" placeholder={paired ? 'Signing key paired (leave blank)' : 'Approval key (64 hex characters)'} placeholderTextColor="#ad8d9f" style={styles.input} />
    <Pressable style={styles.button} onPress={async () => { await connect(token || undefined, key || undefined); setToken(''); setKey(''); }}>
      <Text style={styles.text}>Save privately & connect to 127.0.0.1:8765</Text>
    </Pressable>
    <Text style={styles.text}>Native Android build required. No network address can be changed. Termux must already be running.</Text>
  </View>;
}
const styles = StyleSheet.create({ box: { padding: 12, gap: 8 }, text: { color: '#edd6e0', fontSize: 12 }, input: { backgroundColor: '#35232f', color: 'white', padding: 12, minHeight: 48, borderRadius: 8 }, button: { backgroundColor: '#81324e', borderRadius: 8, padding: 12, minHeight: 48 } });

import { useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, Platform, KeyboardAvoidingView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTerminal } from '@/lib/terminal-context';
import TerminalOutput from '@/components/TerminalOutput';
import TerminalInput from '@/components/TerminalInput';
import SessionTabs from '@/components/SessionTabs';
import LeoPanel from '@/components/LeoPanel';
export default function TerminalScreen() {
  const t = useTerminal(); const insets = useSafeAreaInsets(); const [headless, setHeadless] = useState(false);
  if (headless) return <View style={[styles.root, { paddingTop: insets.top + 30, paddingHorizontal: 24 }]}>
    <Text style={styles.title}>UI disconnected</Text><Text style={styles.text}>The independent Termux server can keep running. Close this app for socket-only operation. No approvals are automatic; they expire without a paired approver. A Grok voice call does not connect itself to localhost.</Text>
    <Pressable onPress={() => setHeadless(false)} style={styles.button}><Text style={styles.text}>Return to UI</Text></Pressable>
  </View>;
  return <KeyboardAvoidingView behavior="padding" style={[styles.root, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
    <View style={styles.header}><View><Text style={styles.title}>LeoMux</Text><Text style={styles.status}>{t.status}</Text></View>
      <Pressable onPress={() => void t.connect()} style={styles.button}><Text style={styles.text}>{t.connected ? 'Reconnect' : 'Connect'}</Text></Pressable>
      <Pressable onPress={() => { t.disconnect(); setHeadless(true); }} style={styles.button}><Text style={styles.text}>Headless</Text></Pressable></View>
    {Platform.OS !== 'android' && <Text style={styles.warning}>Layout preview only: Termux and secure approvals require Android. iPhone 13 cannot run this localhost Termux backend.</Text>}
    <SessionTabs />
    <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 20 }}><TerminalOutput lines={t.activeSession.lines} cwd={t.activeSession.cwd} /></ScrollView>
    <TerminalInput /><LeoPanel />
  </KeyboardAvoidingView>;
}
const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: '#1a1015' }, header: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderColor: '#3a2830' }, title: { color: '#f0e4e8', fontFamily: 'Cinzel_700Bold', fontSize: 19 }, text: { color: '#e5b3c8', fontSize: 12, lineHeight: 20 }, status: { color: '#b08898', fontSize: 10, maxWidth: 180 }, button: { padding: 12, minHeight: 48 }, warning: { color: '#efbd7d', padding: 12 } });

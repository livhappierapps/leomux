import { Stack } from 'expo-router';
import { useFonts, JetBrainsMono_400Regular, JetBrainsMono_700Bold } from '@expo-google-fonts/jetbrains-mono';
import { Cinzel_700Bold } from '@expo-google-fonts/cinzel';
import { ThemeProvider } from '@/lib/theme-context';
import { TerminalProvider } from '@/lib/terminal-context';
import { SafeAreaProvider } from 'react-native-safe-area-context';
export default function RootLayout() {
  const [loaded, error] = useFonts({ JetBrainsMono_400Regular, JetBrainsMono_700Bold, Cinzel_700Bold });
  if (!loaded && !error) return null;
  return <SafeAreaProvider><ThemeProvider><TerminalProvider><Stack screenOptions={{ headerShown: false }} /></TerminalProvider></ThemeProvider></SafeAreaProvider>;
}

import React, { memo } from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { useTerminalColors } from '@/lib/theme-context';
import { TerminalLine } from '@/lib/terminal-engine';

const monoFont = Platform.select({
  ios: 'JetBrainsMono_400Regular',
  android: 'JetBrainsMono_400Regular',
  default: 'JetBrainsMono_400Regular',
});

const monoBold = Platform.select({
  ios: 'JetBrainsMono_700Bold',
  android: 'JetBrainsMono_700Bold',
  default: 'JetBrainsMono_700Bold',
});

type LineColors = {
  input: string; output: string; error: string;
  info: string; success: string; warning: string; system: string; text: string;
  promptUser: string; promptAt: string; promptHost: string;
  promptPath: string; promptSym: string;
};

function getLineColor(type: TerminalLine['type'], c: LineColors): string {
  switch (type) {
    case 'input': return c.input;
    case 'output': return c.output;
    case 'error': return c.error;
    case 'info': return c.info;
    case 'success': return c.success;
    case 'warning': return c.warning;
    case 'system': return c.system;
    default: return c.text;
  }
}

function TerminalOutputLine({
  line, cwd, colors,
}: {
  line: TerminalLine; cwd: string; colors: LineColors;
}) {
  const color = getLineColor(line.type, colors);
  const displayCwd = cwd.replace(/.*\/Documents\//, '~/').replace(/\/$/, '') || '~';

  if (line.type === 'input') {
    return (
      <View style={styles.inputLine}>
        <Text style={[styles.prompt, { fontFamily: monoBold }]}>
          <Text style={{ color: colors.promptUser }}>leo</Text>
          <Text style={{ color: colors.promptAt }}>@</Text>
          <Text style={{ color: colors.promptHost }}>mux</Text>
          <Text style={{ color: colors.promptAt }}>:</Text>
          <Text style={{ color: colors.promptPath }}>{displayCwd}</Text>
          <Text style={{ color: colors.promptSym }}> $ </Text>
        </Text>
        <Text style={[styles.lineText, { color, fontFamily: monoFont }]} selectable>
          {line.content}
        </Text>
      </View>
    );
  }

  return (
    <Text style={[styles.lineText, { color, fontFamily: monoFont }]} selectable>
      {line.content}
    </Text>
  );
}

const MemoizedLine = memo(
  function MemoizedTerminalLine({ line, cwd, colors }: { line: TerminalLine; cwd: string; colors: LineColors }) {
    return (
    <TerminalOutputLine line={line} cwd={cwd} colors={colors} />
    );
  },
  (prev, next) =>
    prev.line.id === next.line.id &&
    prev.cwd === next.cwd &&
    prev.colors === next.colors
);

export default function TerminalOutput({ lines, cwd }: { lines: TerminalLine[]; cwd: string }) {
  const tc = useTerminalColors();

  const colors: LineColors = {
    input: tc.rose,
    output: tc.output,
    error: tc.error,
    info: tc.info,
    success: tc.success,
    warning: tc.warning,
    system: tc.mauve,
    text: tc.text,
    promptUser: tc.rose,
    promptAt: tc.textDim,
    promptHost: tc.mauve,
    promptPath: tc.cream,
    promptSym: tc.textDim,
  };

  return (
    <View style={styles.container}>
      {lines.map((line) => (
        <View key={line.id} style={styles.lineWrapper}>
          <MemoizedLine line={line} cwd={cwd} colors={colors} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 12, paddingTop: 4 },
  lineWrapper: { paddingVertical: 1 },
  inputLine: { flexDirection: 'row', flexWrap: 'wrap', paddingTop: 6 },
  prompt: { fontSize: 13, lineHeight: 20 },
  lineText: { fontSize: 13, lineHeight: 20 },
});

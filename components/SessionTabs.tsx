import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useTerminalColors } from '@/lib/theme-context';
import { useTerminal } from '@/lib/terminal-context';

const monoFont = Platform.select({
  ios: 'JetBrainsMono_400Regular',
  android: 'JetBrainsMono_400Regular',
  default: 'JetBrainsMono_400Regular',
});

export default function SessionTabs() {
  const { sessions, activeSessionId, setActiveSession, createNewSession, closeSession } = useTerminal();
  const tc = useTerminalColors();

  const handleNewTab = () => {
    if (Platform.OS !== 'web') {
      // Local display tabs only; all proposals use the same leo tmux session.
    }
    createNewSession();
  };

  const handleCloseTab = (id: string) => {
    if (Platform.OS !== 'web') {
      // Local display tabs only; all proposals use the same leo tmux session.
    }
    closeSession(id);
  };

  const tabColors = [
    tc.rose, tc.blush, tc.mauve, tc.cream, tc.dustyRose, tc.softPink,
  ];

  return (
    <View style={[styles.container, { backgroundColor: tc.bg, borderBottomColor: tc.border }]}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {sessions.map((session, idx) => {
          const isActive = session.id === activeSessionId;
          const tabColor = tabColors[idx % tabColors.length];
          return (
            <Pressable
              key={session.id}
              onPress={() => setActiveSession(session.id)}
              style={[
                styles.tab,
                isActive && { backgroundColor: tc.bgSecondary },
                isActive && { borderBottomColor: tabColor },
              ]}
            >
              <Ionicons
                name="terminal"
                size={12}
                color={isActive ? tabColor : tc.textMuted}
                style={styles.tabIcon}
              />
              <Text
                style={[
                  styles.tabText,
                  { fontFamily: monoFont, color: tc.textMuted },
                  isActive && { color: tc.text },
                ]}
                numberOfLines={1}
              >
                {session.name}
              </Text>
              {sessions.length > 1 && (
                <Pressable
                  onPress={() => handleCloseTab(session.id)}
                  hitSlop={8}
                  style={styles.closeBtn}
                >
                  <Ionicons
                    name="close"
                    size={12}
                    color={isActive ? tc.textDim : tc.textMuted}
                  />
                </Pressable>
              )}
            </Pressable>
          );
        })}
      </ScrollView>
      <Pressable
        testID="new-tab-btn"
        onPress={handleNewTab}
        style={({ pressed }) => [
          styles.newTabBtn,
          pressed && { backgroundColor: tc.bgSecondary },
        ]}
        hitSlop={8}
      >
        <Ionicons name="add" size={18} color={tc.rose} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    alignItems: 'center',
  },
  scrollContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 8,
    gap: 2,
    flex: 1,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 6,
    marginVertical: 4,
    maxWidth: 150,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabIcon: { marginRight: 5 },
  tabText: { fontSize: 11, flexShrink: 1 },
  closeBtn: {
    marginLeft: 6,
    width: 16, height: 16,
    alignItems: 'center', justifyContent: 'center',
    borderRadius: 4,
  },
  newTabBtn: {
    width: 32, height: 32,
    alignItems: 'center', justifyContent: 'center',
    marginRight: 8, borderRadius: 6,
  },
});

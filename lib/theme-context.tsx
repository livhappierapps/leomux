import React, { createContext, useContext } from 'react';
export interface TerminalPalette {
  bg: string; bgSecondary: string; bgTertiary: string;
  surface: string; surfaceHover: string;
  accent: string; accentDim: string; accentFaint: string;
  rose: string; blush: string; cream: string; creamDim: string;
  mauve: string; dustyRose: string; warmGrey: string; coolGrey: string;
  wine: string; burgundy: string; pink: string; softPink: string; palePink: string;
  ash: string; silver: string;
  text: string; textDim: string; textMuted: string;
  border: string; borderActive: string;
  cursor: string; selection: string;
  prompt: string; output: string;
  error: string; success: string; warning: string; info: string;
  tabBar: string; tabActive: string; tabInactive: string;
}


export const palette: TerminalPalette = {
      bg: '#1a1015', bgSecondary: '#241a1f', bgTertiary: '#2e2228',
      surface: '#1e1318', surfaceHover: '#2a1e24',
      accent: '#c94060', accentDim: '#8a2a3f', accentFaint: 'rgba(201,64,96,0.08)',
      rose: '#e8607a', blush: '#f2a0b0', cream: '#f5e6d8', creamDim: '#d4c0b0',
      mauve: '#b08898', dustyRose: '#c07888', warmGrey: '#9a8890', coolGrey: '#706068',
      wine: '#8a3050', burgundy: '#6a2040', pink: '#e87898', softPink: '#f0b8c8', palePink: '#f8d8e0',
      ash: '#a89098', silver: '#c8b8c0',
      text: '#f0e4e8', textDim: '#9a8890', textMuted: '#5a4a52',
      border: '#3a2830', borderActive: '#c94060',
      cursor: '#e8607a', selection: 'rgba(201,64,96,0.15)',
      prompt: '#e8607a', output: '#d8c8d0',
      error: '#e85050', success: '#90c8a0', warning: '#e8c878', info: '#b0a0c0',
      tabBar: '#1e1318', tabActive: '#c94060', tabInactive: '#5a4a52',
    };
const ThemeContext = createContext(palette);
export function ThemeProvider({children}: {children: React.ReactNode}) { return <ThemeContext.Provider value={palette}>{children}</ThemeContext.Provider>; }
export function useTerminalColors() { return useContext(ThemeContext); }

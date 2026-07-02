import { useEffect, useCallback } from 'react';
import { ChartTimeframe } from './chartTypes';
import { TIMEFRAMES } from './chartConstants';

// ============================================================================
// Chart Keyboard Actions Interface
// ============================================================================

export interface ChartKeyboardActions {
  onTimeframeChange: (tf: ChartTimeframe) => void;
  onToggleFullscreen: () => void;
  onUndoDrawing: () => void;
  onDeleteDrawing: () => void;
  onResetDrawings: () => void;
  onToggleReplay?: () => void;
}

// ============================================================================
// useChartKeyboardShortcuts Hook
// ============================================================================

/**
 * Custom hook that binds keyboard shortcuts for the trading chart.
 *
 * Shortcuts:
 *  - 1–7        → Switch timeframe (maps to TIMEFRAMES array by index)
 *  - f / F      → Toggle fullscreen
 *  - Escape     → Exit fullscreen (only when fullscreen is active)
 *  - Ctrl+Z     → Undo last drawing (Cmd+Z on macOS)
 *  - Delete     → Delete selected drawing
 *  - Backspace  → Delete selected drawing
 *  - Space      → Toggle replay mode (if provided)
 *
 * All shortcuts are suppressed when the user is focused on an input,
 * textarea, or contenteditable element.
 *
 * @param actions - Callback functions for each shortcut action
 * @param enabled - Whether keyboard shortcuts are active (defaults to true)
 */
export function useChartKeyboardShortcuts(
  actions: ChartKeyboardActions,
  enabled: boolean = true
): void {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore shortcuts when typing in form elements or contenteditable
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return;
      }

      const key = event.key;
      const isCtrlOrMeta = event.ctrlKey || event.metaKey;

      // ── Timeframe shortcuts: 1 through 7 ──────────────────────────────
      if (!isCtrlOrMeta && !event.altKey && !event.shiftKey) {
        const hotkeyIndex = parseInt(key, 10);
        if (hotkeyIndex >= 1 && hotkeyIndex <= 7 && hotkeyIndex <= TIMEFRAMES.length) {
          event.preventDefault();
          actions.onTimeframeChange(TIMEFRAMES[hotkeyIndex - 1].key);
          return;
        }
      }

      // ── Fullscreen toggle: f / F ───────────────────────────────────────
      if ((key === 'f' || key === 'F') && !isCtrlOrMeta && !event.altKey) {
        event.preventDefault();
        actions.onToggleFullscreen();
        return;
      }

      // ── Exit fullscreen: Escape ────────────────────────────────────────
      if (key === 'Escape') {
        if (document.fullscreenElement) {
          event.preventDefault();
          actions.onToggleFullscreen();
        }
        return;
      }

      // ── Undo drawing: Ctrl+Z / Cmd+Z ──────────────────────────────────
      if (key === 'z' && isCtrlOrMeta && !event.shiftKey) {
        event.preventDefault();
        actions.onUndoDrawing();
        return;
      }

      // ── Delete selected drawing: Delete or Backspace ───────────────────
      if (key === 'Delete' || key === 'Backspace') {
        event.preventDefault();
        actions.onDeleteDrawing();
        return;
      }

      // ── Toggle replay: Space ───────────────────────────────────────────
      if (key === ' ' && !isCtrlOrMeta && !event.altKey) {
        if (actions.onToggleReplay) {
          event.preventDefault();
          actions.onToggleReplay();
        }
        return;
      }
    },
    [actions]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);
}

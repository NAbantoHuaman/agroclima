import * as ExpoHaptics from "expo-haptics";

function fireSafe(invoke: () => Promise<void> | undefined): void {
  try {
    const result = invoke();
    if (result && typeof result.catch === "function") {
      result.catch(() => {
        // Ignore unavailable native haptic implementation (e.g. Android Expo Go / device without vibrator bridge)
      });
    }
  } catch {
    // Ignore synchronous native module errors
  }
}

export const SafeHaptics = {
  ImpactFeedbackStyle: ExpoHaptics.ImpactFeedbackStyle,
  NotificationFeedbackType: ExpoHaptics.NotificationFeedbackType,
  selectionAsync(): void {
    fireSafe(() =>
      typeof ExpoHaptics.selectionAsync === "function"
        ? ExpoHaptics.selectionAsync()
        : undefined
    );
  },
  impactAsync(
    style: ExpoHaptics.ImpactFeedbackStyle = ExpoHaptics.ImpactFeedbackStyle.Light
  ): void {
    fireSafe(() =>
      typeof ExpoHaptics.impactAsync === "function"
        ? ExpoHaptics.impactAsync(style)
        : undefined
    );
  },
  notificationAsync(
    type: ExpoHaptics.NotificationFeedbackType = ExpoHaptics.NotificationFeedbackType.Success
  ): void {
    fireSafe(() =>
      typeof ExpoHaptics.notificationAsync === "function"
        ? ExpoHaptics.notificationAsync(type)
        : undefined
    );
  },
};

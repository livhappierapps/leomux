import { Platform, Text, type ViewProps } from 'react-native';
import { requireOptionalNativeModule, requireNativeViewManager } from 'expo-modules-core';

export type Approval = { id: string; nonce: string; session_id: string; signature: string };
type Props = ViewProps & {
  proposal: string;
  onApproved: (event: { nativeEvent: Approval }) => void;
  onBlocked: (event: { nativeEvent: { message: string } }) => void;
};
export const LeoApproval = Platform.OS === 'android'
  ? requireOptionalNativeModule<{ installKey(key: string): Promise<void>; isPaired(): Promise<boolean> }>('LeoApproval')
  : null;
const NativeView = LeoApproval ? requireNativeViewManager<Props>('LeoApproval') : null;
export function SwipeApproval(props: Props) {
  // Fail CLOSED: never replace with a JS tap/swipe or unsigned approval.
  return NativeView ? <NativeView {...props} /> : <Text style={{ color: '#ffb3c7' }}>
    Secure Android approval module unavailable. Use a native development build; Expo Go/iOS cannot approve.
  </Text>;
}

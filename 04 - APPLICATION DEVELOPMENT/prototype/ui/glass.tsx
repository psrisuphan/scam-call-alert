import React, { ReactNode, RefObject } from 'react';
import { ActivityIndicator, Platform, StatusBar, StyleProp, StyleSheet, TouchableOpacity, View, ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

export type IconName = React.ComponentProps<typeof Ionicons>['name'];
export type Tone = 'neutral' | 'safe' | 'danger';

export const color = {
  label: '#1c1c1e', secondary: '#8a8a8e', tertiary: '#c7c7cc', fill: 'rgba(118,118,128,0.12)',
  separator: 'rgba(60,60,67,0.12)', grouped: '#f2f2f7', blue: '#0a84ff', green: '#30d158',
  red: '#ff453a', orange: '#ff9f0a', white: '#ffffff', glassText: 'rgba(255,255,255,0.94)',
  glassSecondary: 'rgba(235,235,245,0.6)',
};

// Edge-to-edge Android window: content draws under the status and navigation bars.
export const inset = { top: Platform.OS === 'android' ? StatusBar.currentHeight ?? 24 : 47, bottom: 30 };

export function Icon({ name, size = 22, tint = color.label }: { name: IconName; size?: number; tint?: string }) {
  return <Ionicons name={name} size={size} color={tint} />;
}

type GlassProps = {
  target: RefObject<View | null>; radius?: number; light?: boolean; tint?: string;
  style?: StyleProp<ViewStyle>; children?: ReactNode;
  /** Real backdrop blur. Costly on the emulator, so reserve it for large surfaces. */
  live?: boolean;
};

/**
 * Liquid Glass-inspired material: backdrop blur of the shared target, a thin
 * tint, a specular top sheen and a rim that is brighter where light lands.
 */
export function Glass({ target, radius = 28, light = false, tint, style, children, live = false }: GlassProps) {
  const base = light ? (live ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.78)') : (live ? 'rgba(255,255,255,0.045)' : 'rgba(255,255,255,0.09)');
  return <View style={[{ borderRadius: radius, overflow: 'hidden' }, style]}>
    {live && <BlurView blurTarget={target} blurMethod="dimezisBlurViewSdk31Plus" intensity={light ? 60 : 24}
      tint={light ? 'light' : 'systemChromeMaterialDark'} style={StyleSheet.absoluteFill} />}
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: tint ?? base }]} />
    <LinearGradient pointerEvents="none" colors={[light ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.13)', 'rgba(255,255,255,0)']}
      start={{ x: 0, y: 0 }} end={{ x: 0.35, y: 0.5 }} style={StyleSheet.absoluteFill} />
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, light ? rim.light : rim.dark, { borderRadius: radius }]} />
    {children}
  </View>;
}

type GlassButtonProps = {
  target: RefObject<View | null>; icon: IconName; label: string; onPress: () => void;
  size?: number; fill?: string; light?: boolean; disabled?: boolean; busy?: boolean; iconTint?: string; hangUp?: boolean;
};

/** Circular icon control; a solid `fill` replaces the glass for primary call actions. */
export function GlassButton({ target, icon, label, onPress, size = 64, fill, light = false, disabled = false, busy = false, iconTint, hangUp = false }: GlassButtonProps) {
  const tint = iconTint ?? (fill || !light ? color.white : color.label);
  const content = busy ? <ActivityIndicator color={tint} /> : <View style={hangUp && { transform: [{ rotate: '135deg' }] }}><Icon name={icon} size={Math.round(size * 0.42)} tint={tint} /></View>;
  return <TouchableOpacity accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled, busy }}
    disabled={disabled} onPress={onPress} activeOpacity={0.7} style={disabled && { opacity: 0.35 }}>
    {fill
      ? <View style={[styles.center, { width: size, height: size, borderRadius: size / 2, backgroundColor: fill }]}>{content}</View>
      : <Glass target={target} light={light} radius={size / 2} style={[styles.center, { width: size, height: size }]}>{content}</Glass>}
  </TouchableOpacity>;
}

/** Quiet dark call backdrop: a barely-there vertical falloff, like the iOS call screen without a contact poster. */
export function Ambient() {
  return <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: '#0a0a0b', experimental_backgroundImage: 'linear-gradient(180deg, #1c1c1e 0%, #111112 45%, #0a0a0b 100%)' }]} />;
}

const rim = StyleSheet.create({
  dark: { borderWidth: 1, borderTopColor: 'rgba(255,255,255,0.34)', borderLeftColor: 'rgba(255,255,255,0.18)', borderRightColor: 'rgba(255,255,255,0.10)', borderBottomColor: 'rgba(255,255,255,0.14)' },
  light: { borderWidth: 1, borderTopColor: 'rgba(255,255,255,0.95)', borderLeftColor: 'rgba(255,255,255,0.8)', borderRightColor: 'rgba(0,0,0,0.05)', borderBottomColor: 'rgba(0,0,0,0.07)' },
});
const styles = StyleSheet.create({ center: { alignItems: 'center', justifyContent: 'center' } });

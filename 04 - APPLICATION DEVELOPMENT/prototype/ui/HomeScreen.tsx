import React, { useRef } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { BlurTargetView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { color, Glass, GlassButton, Icon, inset } from './glass';

export type Mode = 'recorded' | 'microphone';
export type Recording = { id: string; title: string; duration_seconds: number };

type Props = {
  mode: Mode; recordings: Recording[]; selected: string; connected: boolean; loading: boolean;
  busy: boolean; error: string; clock: (ms?: number) => string;
  onMode: (mode: Mode) => void; onSelect: (id: string) => void; onConnect: () => void;
  onSettings: () => void; onCall: () => void;
};

const modes = [
  { value: 'recorded', icon: 'play-circle-outline', selectedIcon: 'play-circle', label: 'บทสนทนาที่บันทึกไว้' },
  { value: 'microphone', icon: 'mic-outline', selectedIcon: 'mic', label: 'ไมโครโฟนสด' },
] as const;

export function HomeScreen(p: Props) {
  const target = useRef<View | null>(null);
  const canCall = p.connected && !p.loading && (p.mode === 'microphone' || Boolean(p.selected));

  return <View style={styles.root}>
    <BlurTargetView ref={target} style={StyleSheet.absoluteFill}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text accessibilityRole="header" style={styles.title}>Scam Call Alert</Text>

        <View accessibilityRole="tablist" style={styles.segmented}>
          {modes.map(m => {
            const on = p.mode === m.value;
            return <TouchableOpacity key={m.value} accessibilityRole="tab" accessibilityLabel={m.label}
              accessibilityState={{ selected: on, disabled: p.busy }} disabled={p.busy}
              onPress={() => p.onMode(m.value)} style={[styles.segment, on && styles.segmentOn]}>
              <Icon name={on ? m.selectedIcon : m.icon} size={21} tint={on ? color.label : color.secondary} />
            </TouchableOpacity>;
          })}
        </View>

        {p.mode === 'recorded'
          ? p.recordings.length
            ? <View accessibilityRole="radiogroup" style={styles.list}>
              {p.recordings.map((r, i) => {
                const on = r.id === p.selected;
                const unverified = r.title.includes('unverified');
                return <TouchableOpacity key={r.id} onPress={() => p.onSelect(r.id)} accessibilityRole="radio"
                  accessibilityLabel={`${r.title}${unverified ? ', ยังไม่ตรวจสอบ' : ''}`} accessibilityState={{ checked: on }}
                  style={[styles.row, i > 0 && styles.rowDivider]}>
                  <View style={[styles.badge, on && styles.badgeOn]}>
                    <Text style={[styles.badgeText, on && { color: color.white }]}>{String(i + 1).padStart(2, '0')}</Text>
                  </View>
                  <Text numberOfLines={1} style={[styles.name, styles.flex]}>{r.title.split(' · ')[0]}</Text>
                  <Text style={styles.duration}>{p.clock(r.duration_seconds * 1000)}</Text>
                  {unverified && <Icon name="alert-circle" size={17} tint={color.orange} />}
                  {on && <Icon name="checkmark" size={22} tint={color.blue} />}
                </TouchableOpacity>;
              })}
            </View>
            : <View style={styles.empty}>
              <Icon name={p.connected ? 'play-circle-outline' : 'cloud-offline-outline'} size={44} tint={color.tertiary} />
            </View>
          : <View style={styles.micStage}>
            <View style={styles.ringOuter}><View style={styles.ringInner}>
              <View style={styles.micOrb}><Icon name="mic" size={50} tint={color.label} /></View>
            </View></View>
          </View>}

        {!!p.error && p.connected && <View accessibilityRole="alert" style={styles.notice}>
          <Icon name="alert-circle" size={18} tint={color.red} />
          <Text style={styles.noticeText}>{p.error}</Text>
        </View>}
      </ScrollView>
    </BlurTargetView>

    <LinearGradient pointerEvents="none" colors={['rgba(242,242,247,0)', 'rgba(242,242,247,0.92)']} style={styles.bottomFade} />

    <View style={styles.topBar}>
      {p.loading
        ? <Glass target={target} light radius={22} style={styles.pill}><ActivityIndicator size="small" color={color.secondary} /></Glass>
        : !p.connected
          ? <TouchableOpacity accessibilityRole="button" accessibilityLabel="เชื่อมต่อ" accessibilityHint="ระบบวิเคราะห์ยังไม่พร้อม" onPress={p.onConnect}>
            <Glass target={target} light radius={22} style={styles.pill}>
              <Icon name="cloud-offline-outline" size={19} tint={color.red} />
              <Icon name="refresh" size={18} tint={color.label} />
            </Glass>
          </TouchableOpacity>
          : <View />}
      <GlassButton target={target} light size={44} icon="ellipsis-horizontal" label="การตั้งค่า" onPress={p.onSettings} />
    </View>

    <View style={styles.dock}>
      <GlassButton target={target} size={76} fill={canCall ? color.green : '#aeaeb2'} icon="call"
        label={p.mode === 'recorded' ? 'จำลองสายเข้า' : 'เริ่มฟัง'} disabled={!canCall} onPress={p.onCall} />
    </View>
  </View>;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.grouped },
  flex: { flex: 1 },
  page: { paddingHorizontal: 20, paddingTop: inset.top + 64, paddingBottom: 180, gap: 22 },
  title: { color: color.label, fontSize: 34, fontWeight: '700', letterSpacing: 0.3 },
  segmented: { flexDirection: 'row', backgroundColor: color.fill, borderRadius: 100, padding: 3 },
  segment: { flex: 1, height: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 100 },
  segmentOn: { backgroundColor: color.white, boxShadow: '0 2px 8px rgba(0,0,0,0.10)' },
  list: { backgroundColor: color.white, borderRadius: 24, overflow: 'hidden' },
  row: { minHeight: 60, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 14 },
  rowDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: color.separator, marginLeft: 0 },
  badge: { width: 36, height: 36, borderRadius: 18, backgroundColor: color.grouped, alignItems: 'center', justifyContent: 'center' },
  badgeOn: { backgroundColor: color.blue },
  badgeText: { color: color.label, fontSize: 14, fontWeight: '600', fontVariant: ['tabular-nums'] },
  name: { color: color.label, fontSize: 17 },
  duration: { color: color.secondary, fontSize: 17, fontVariant: ['tabular-nums'] },
  empty: { alignItems: 'center', paddingVertical: 72 },
  micStage: { alignItems: 'center', paddingVertical: 40 },
  ringOuter: { width: 236, height: 236, borderRadius: 118, borderWidth: 1, borderColor: 'rgba(60,60,67,0.08)', alignItems: 'center', justifyContent: 'center' },
  ringInner: { width: 184, height: 184, borderRadius: 92, borderWidth: 1, borderColor: 'rgba(60,60,67,0.12)', alignItems: 'center', justifyContent: 'center' },
  micOrb: { width: 128, height: 128, borderRadius: 64, backgroundColor: color.white, alignItems: 'center', justifyContent: 'center', boxShadow: '0 10px 30px rgba(0,0,0,0.08)' },
  notice: { flexDirection: 'row', gap: 10, alignItems: 'center', padding: 14, borderRadius: 18, backgroundColor: 'rgba(255,69,58,0.08)' },
  noticeText: { flex: 1, color: color.label, fontSize: 14, lineHeight: 21 },
  topBar: { position: 'absolute', top: inset.top + 8, left: 16, right: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  pill: { height: 44, minWidth: 44, paddingHorizontal: 14, flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center' },
  bottomFade: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 170 },
  dock: { position: 'absolute', left: 0, right: 0, bottom: inset.bottom + 18, alignItems: 'center' },
});

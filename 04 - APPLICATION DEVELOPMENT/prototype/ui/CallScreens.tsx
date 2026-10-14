import React, { useRef } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BlurTargetView } from 'expo-blur';
import { Ambient, color, Glass, GlassButton, Icon, IconName, inset, Tone } from './glass';
import type { Mode } from './HomeScreen';

export const modeName = (mode: Mode) => mode === 'microphone' ? 'ไมโครโฟนสด' : 'บทสนทนาที่บันทึก';

type IncomingProps = { mode: Mode; loading: boolean; error: string; onDecline: () => void; onAccept: () => void };

export function IncomingScreen({ mode, loading, error, onDecline, onAccept }: IncomingProps) {
  const target = useRef<View | null>(null);
  return <View style={styles.root}>
    <BlurTargetView ref={target} pointerEvents="none" style={StyleSheet.absoluteFill}><Ambient /></BlurTargetView>
    <View style={styles.incoming}>
      <Glass target={target} radius={64} style={styles.avatar}>
        <Icon name={mode === 'microphone' ? 'mic' : 'person'} size={56} tint={color.glassText} />
      </Glass>
      <Text style={styles.caller}>{modeName(mode)}</Text>
      <View style={styles.flex} />
      {!!error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
      <View style={styles.answerRow}>
        <View style={styles.answer}>
          <GlassButton target={target} size={76} fill={color.red} icon="call" hangUp label="ปฏิเสธ" disabled={loading} onPress={onDecline} />
          <Text style={styles.answerLabel}>ปฏิเสธ</Text>
        </View>
        <View style={styles.answer}>
          <GlassButton target={target} size={76} fill={color.green} icon="call" label="ตอบรับ" disabled={loading} busy={loading} onPress={onAccept} />
          <Text style={styles.answerLabel}>ตอบรับ</Text>
        </View>
      </View>
    </View>
  </View>;
}

export type Status = { text: string; icon: IconName | 'spinner'; tone: Tone };
export type Phase = { icon: IconName; label: string } | null;

type SessionProps = {
  mode: Mode; status: Status; phase: Phase; time: string; transcript?: string; warning: boolean;
  delaySeconds: number | null; saved: boolean; failure: string; canRetry: boolean;
  active: boolean; archived: boolean; terminal: boolean; paused: boolean; finishing: boolean;
  onBack: () => void; onPause: () => void; onSave: () => void; onEnd: () => void; onRetry: () => void; onReset: () => void;
};

const toneTint: Record<Tone, string> = { neutral: color.glassText, safe: color.green, danger: '#ff6961' };

export function SessionScreen(p: SessionProps) {
  const target = useRef<View | null>(null);
  const scroll = useRef<ScrollView | null>(null);
  const live = p.active && !p.archived;

  return <View style={styles.root}>
    <BlurTargetView ref={target} pointerEvents="none" style={StyleSheet.absoluteFill}><Ambient /></BlurTargetView>

    <View style={styles.session}>
      <View style={styles.topBar}>
        {p.archived ? <GlassButton target={target} size={44} icon="chevron-back" label="กลับไป Session ปัจจุบัน" onPress={p.onBack} /> : <View style={styles.topSlot} />}
        {p.saved ? <Glass target={target} radius={22} style={styles.topSlot}>
          <View accessible accessibilityLabel="บันทึกหลักฐานแล้ว" style={styles.center}><Icon name="file-tray-full" size={19} tint={color.glassText} /></View>
        </Glass> : <View style={styles.topSlot} />}
      </View>

      <View style={styles.header}>
        <Text style={styles.name}>{modeName(p.mode)}</Text>
        <View style={styles.timeRow} accessible accessibilityLabel={p.phase ? `${p.phase.label} ${p.time}` : p.time}>
          {p.phase && <Icon name={p.phase.icon} size={16} tint={color.glassSecondary} />}
          <Text style={styles.time}>{p.time}</Text>
        </View>
      </View>

      <View style={styles.statusRow}>
        <Glass target={target} radius={20} tint={p.status.tone === 'danger' ? 'rgba(255,69,58,0.18)' : undefined} style={styles.pill}>
          {p.status.icon === 'spinner'
            ? <ActivityIndicator size="small" color={color.glassText} />
            : <Icon name={p.status.icon} size={17} tint={toneTint[p.status.tone]} />}
          <Text accessibilityLiveRegion="polite" style={[styles.pillText, p.status.tone !== 'neutral' && { color: toneTint[p.status.tone] }]}>{p.status.text}</Text>
        </Glass>
        {p.delaySeconds !== null && <Glass target={target} radius={20} style={styles.pill}>
          <View accessible accessibilityLabel={`วิเคราะห์ล่าช้า ${p.delaySeconds} วินาที`} style={styles.pillInner}>
            <Icon name="hourglass-outline" size={15} tint={color.orange} />
            <Text style={[styles.pillText, { color: color.orange }]}>{p.delaySeconds}s</Text>
          </View>
        </Glass>}
      </View>

      {p.warning && <Glass target={target} radius={26} tint="rgba(255,59,48,0.32)" style={styles.alert}>
        <View accessibilityRole="alert" style={styles.alertInner}>
          <View style={styles.alertIcon}><Icon name="warning" size={22} tint={color.white} /></View>
          <Text style={styles.alertText}>ระวัง! สายนี้อาจเป็นมิจฉาชีพ</Text>
        </View>
      </Glass>}

      {!!p.failure && <Glass target={target} radius={22} style={styles.alert}>
        <View style={styles.alertInner}>
          <Icon name="alert-circle" size={20} tint="#ff6961" />
          <Text accessibilityRole="alert" style={styles.failureText}>{p.failure}</Text>
          {p.canRetry && <GlassButton target={target} size={40} icon="refresh" label="ลองใหม่" onPress={p.onRetry} />}
        </View>
      </Glass>}

      <Glass live target={target} radius={34} style={styles.transcript}>
        <ScrollView ref={scroll} contentContainerStyle={styles.transcriptBody} onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}>
          {p.transcript
            ? <Text selectable style={styles.transcriptText}>{p.transcript}</Text>
            : <View accessible accessibilityLabel="รอเสียงจากบทสนทนา" style={styles.waiting}>
              <Icon name="ellipsis-horizontal" size={30} tint="rgba(235,235,245,0.32)" />
            </View>}
        </ScrollView>
      </Glass>

      <View style={styles.controls}>
        {live && p.mode === 'recorded' && <GlassButton target={target} size={72} icon={p.paused ? 'play' : 'pause'}
          label={p.paused ? 'เล่นต่อ' : 'พักเสียง'} disabled={p.finishing} onPress={p.onPause} />}
        {live && p.mode === 'microphone' && <GlassButton target={target} size={72} icon={p.saved ? 'file-tray-full' : 'file-tray-outline'}
          label={p.saved ? 'บันทึกแล้ว' : 'บันทึกหลักฐานของ Session นี้'} disabled={p.saved} onPress={p.onSave} />}
        {live && <GlassButton target={target} size={72} fill={color.red} icon="call" hangUp label="จบ / หยุด" onPress={p.onEnd} />}
        {p.terminal && !p.archived && <GlassButton target={target} size={72} icon="close" label="เริ่ม Session ใหม่" onPress={p.onReset} />}
      </View>
    </View>
  </View>;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#07080b' },
  flex: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  incoming: { flex: 1, alignItems: 'center', paddingTop: inset.top + 96, paddingBottom: inset.bottom + 40, paddingHorizontal: 32 },
  avatar: { width: 128, height: 128, alignItems: 'center', justifyContent: 'center' },
  caller: { color: color.white, fontSize: 32, fontWeight: '400', marginTop: 26, textAlign: 'center' },
  error: { color: '#ffb4ab', fontSize: 14, lineHeight: 21, textAlign: 'center', marginBottom: 28 },
  answerRow: { width: '100%', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 16 },
  answer: { alignItems: 'center', gap: 12 },
  answerLabel: { color: color.glassText, fontSize: 15 },

  session: { flex: 1, paddingTop: inset.top + 8, paddingBottom: inset.bottom + 12, paddingHorizontal: 16 },
  topBar: { height: 44, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  topSlot: { width: 44, height: 44 },
  header: { alignItems: 'center', gap: 6, marginTop: 4 },
  name: { color: color.white, fontSize: 26, fontWeight: '500', textAlign: 'center' },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  time: { color: color.glassSecondary, fontSize: 17, fontVariant: ['tabular-nums'] },
  statusRow: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginTop: 18 },
  pill: { height: 40, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 8 },
  pillInner: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pillText: { color: color.glassText, fontSize: 15, fontWeight: '600' },
  alert: { marginTop: 14 },
  alertInner: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, paddingLeft: 14, paddingRight: 18 },
  alertIcon: { width: 40, height: 40, borderRadius: 20, backgroundColor: color.red, alignItems: 'center', justifyContent: 'center' },
  alertText: { flex: 1, color: color.white, fontSize: 17, fontWeight: '600', lineHeight: 23 },
  failureText: { flex: 1, color: color.glassText, fontSize: 14, lineHeight: 21 },
  transcript: { flex: 1, marginTop: 14 },
  transcriptBody: { padding: 24, flexGrow: 1 },
  transcriptText: { color: color.glassText, fontSize: 19, lineHeight: 32 },
  waiting: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  controls: { flexDirection: 'row', justifyContent: 'center', gap: 32, paddingTop: 22, minHeight: 94 },
});

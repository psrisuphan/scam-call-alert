import React from 'react';
import { ActivityIndicator, Modal, Pressable, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { color, Icon, inset } from './glass';

type Props = {
  visible: boolean; endpoint: string; connected: boolean; loading: boolean; approach: string;
  showStaged: boolean; staged: boolean;
  onEndpoint: (value: string) => void; onConnect: () => void; onApproach: (value: string) => void;
  onStaged: (value: boolean) => void; onClose: () => void;
};

const approaches = [['latest', 'Latest'], ['recent', 'Recent'], ['accumulated', 'Accumulated']] as const;

/** Developer-only settings, kept out of the main flow in a bottom sheet. */
export function SettingsSheet(p: Props) {
  return <Modal visible={p.visible} transparent animationType="slide" statusBarTranslucent navigationBarTranslucent onRequestClose={p.onClose}>
    <Pressable accessibilityLabel="ปิด" style={styles.scrim} onPress={p.onClose} />
    <View style={styles.sheet}>
      <View style={styles.grabber} />
      <View style={styles.header}>
        <Text style={styles.title}>Developer</Text>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="ปิด" onPress={p.onClose} style={styles.close}>
          <Icon name="close" size={20} tint={color.secondary} />
        </TouchableOpacity>
      </View>

      <View style={styles.group}>
        <View style={styles.row}>
          <View style={[styles.dot, { backgroundColor: p.connected ? color.green : color.red }]} />
          <TextInput style={styles.input} value={p.endpoint} onChangeText={p.onEndpoint} autoCapitalize="none" autoCorrect={false}
            keyboardType="url" accessibilityLabel="Analysis service URL" />
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="เชื่อมต่อ" disabled={p.loading} onPress={p.onConnect} style={styles.inline}>
            {p.loading ? <ActivityIndicator size="small" color={color.blue} /> : <Icon name="refresh" size={20} tint={color.blue} />}
          </TouchableOpacity>
        </View>
      </View>

      <Text style={styles.caption}>Context</Text>
      <View accessibilityRole="radiogroup" style={styles.segmented}>
        {approaches.map(([value, title]) => {
          const on = p.approach === value;
          return <TouchableOpacity key={value} accessibilityRole="radio" accessibilityState={{ checked: on }} onPress={() => p.onApproach(value)}
            style={[styles.segment, on && styles.segmentOn]}>
            <Text style={[styles.segmentText, on && { color: color.label }]}>{title}</Text>
          </TouchableOpacity>;
        })}
      </View>

      {p.showStaged && <View style={[styles.group, { marginTop: 22 }]}>
        <View style={styles.row}>
          <Text style={styles.rowText}>Background check</Text>
          <Switch value={p.staged} onValueChange={p.onStaged} accessibilityLabel="Background check"
            trackColor={{ true: color.green, false: '#e9e9eb' }} thumbColor={color.white} />
        </View>
      </View>}
    </View>
  </Modal>;
}

const styles = StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.25)' },
  sheet: { backgroundColor: color.grouped, borderTopLeftRadius: 34, borderTopRightRadius: 34, paddingHorizontal: 20, paddingBottom: inset.bottom + 28 },
  grabber: { alignSelf: 'center', width: 36, height: 5, borderRadius: 3, backgroundColor: 'rgba(60,60,67,0.3)', marginTop: 8 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 14 },
  title: { color: color.label, fontSize: 20, fontWeight: '700' },
  close: { width: 32, height: 32, borderRadius: 16, backgroundColor: color.fill, alignItems: 'center', justifyContent: 'center' },
  group: { backgroundColor: color.white, borderRadius: 20, overflow: 'hidden' },
  row: { minHeight: 54, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 12 },
  rowText: { flex: 1, color: color.label, fontSize: 16 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  input: { flex: 1, color: color.label, fontSize: 16, paddingVertical: 12 },
  inline: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  caption: { color: color.secondary, fontSize: 13, marginTop: 22, marginBottom: 8, marginLeft: 16 },
  segmented: { flexDirection: 'row', backgroundColor: color.fill, borderRadius: 100, padding: 3 },
  segment: { flex: 1, height: 36, alignItems: 'center', justifyContent: 'center', borderRadius: 100 },
  segmentOn: { backgroundColor: color.white, boxShadow: '0 2px 8px rgba(0,0,0,0.10)' },
  segmentText: { color: color.secondary, fontSize: 14, fontWeight: '600' },
});

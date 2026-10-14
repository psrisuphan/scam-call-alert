import React, { useEffect, useRef, useState } from 'react';
import { AppState, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as Notifications from 'expo-notifications';
import Monitor from './modules/scam-monitor';
import { HomeScreen, Recording } from './ui/HomeScreen';
import { IncomingScreen, Phase, SessionScreen, Status } from './ui/CallScreens';
import { SettingsSheet } from './ui/SettingsSheet';

type Snapshot = {
  mode?: 'recorded' | 'microphone';
  session_id?: string; native_active?: boolean; native_state?: string; state?: string;
  transcript?: string; warning?: boolean; stt_busy?: boolean; classifier_busy?: boolean;
  prediction?: { label: string; transcript_version: number }; error?: { message: string };
  connection_error?: string; audio_position_ms?: number; duration_ms?: number;
  save_evidence?: boolean; queued_seconds?: number;
  analysis_delayed?: boolean; analysis_backlog_seconds?: number;
};
const clock = (ms = 0) => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;

export default function App() {
  const [endpoint, setEndpoint] = useState('http://10.0.2.2:8765');
  const [mode, setMode] = useState<'recorded' | 'microphone'>('recorded');
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selected, setSelected] = useState('');
  const [incoming, setIncoming] = useState(false);
  const [state, setState] = useState<Snapshot>({});
  const [error, setError] = useState('');
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [approach, setApproach] = useState('accumulated');
  const [staged, setStaged] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [archive, setArchive] = useState<string | null>(null);
  const archiveRef = useRef<string | null>(null);
  const currentRef = useRef<Snapshot>({});
  const endpointRef = useRef(endpoint);
  endpointRef.current = endpoint;
  const active = Boolean(currentRef.current.native_active);
  const busy = active || loading;
  const displayMode = state.mode ?? mode;

  const observe = async () => {
    try {
      const current = JSON.parse(await Monitor.state());
      currentRef.current = current;
      const origin = await Monitor.notificationSession();
      if (origin) {
        archiveRef.current = origin; setArchive(origin);
        await Monitor.clearNotificationSession();
      }
      const target = archiveRef.current;
      if (target && target !== current.session_id) {
        const saved = JSON.parse(await Monitor.sessionSnapshot(target));
        if (saved.session_id) setState(saved);
        else {
          try {
            const response = await fetch(`${endpointRef.current}/sessions/${target}`);
            const old = await response.json();
            setState({ ...old, native_state: old.state ?? 'ended', native_active: false });
          } catch { setState({ native_state: 'ended', connection_error: 'ไม่พบข้อมูล Session เดิม' }); }
        }
      } else setState(current);
    } catch { setError('ไม่สามารถอ่านสถานะของแอปได้'); }
  };
  useEffect(() => {
    // Rendering only: capture, delivery, analysis polling and alerts run natively.
    const timer = setInterval(observe, 500);
    const subscription = AppState.addEventListener('change', s => { if (s === 'active') void observe(); });
    void observe();
    return () => { clearInterval(timer); subscription.remove(); };
  }, []);

  const connect = async () => {
    setLoading(true); setError('');
    try {
      const health = await fetch(`${endpoint}/health`).then(r => { if (!r.ok) throw new Error(); return r.json(); });
      const list: Recording[] = await fetch(`${endpoint}/recordings`).then(r => r.json());
      setRecordings(list); setSelected(list[0]?.id ?? ''); setConnected(health.status === 'ready');
    } catch { setConnected(false); setError('เชื่อมต่อระบบวิเคราะห์ไม่ได้ ตรวจสอบบริการบนคอมพิวเตอร์'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void connect(); }, []);
  const start = async () => {
    if (busy) return;
    setLoading(true); setError('');
    try {
      await Notifications.setNotificationChannelAsync('scam-warning', { name: 'Possible scam warning', importance: Notifications.AndroidImportance.HIGH });
      const permission = await Notifications.requestPermissionsAsync();
      if (!permission.granted) setError('ไม่ได้อนุญาตการแจ้งเตือน ระบบจะแสดงคำเตือนภายในแอปเท่านั้น');
      archiveRef.current = null; setArchive(null);
      setState({ native_state: 'starting' });
      await Monitor.start(JSON.stringify({ endpoint, mode, approach, recording_id: selected,
        save: mode === 'recorded', staged_background: mode === 'recorded' && staged }));
      await observe();
      setIncoming(false);
    } catch (e) { setError(e instanceof Error ? e.message : 'เริ่มการวิเคราะห์ไม่ได้'); }
    finally { setLoading(false); }
  };
  const end = async () => { await Monitor.end(); setIncoming(false); await observe(); };
  const switchMode = async (next: 'recorded' | 'microphone') => {
    if (busy) return;
    await Monitor.clearDisplay();
    setMode(next); setIncoming(false); setError('');
    archiveRef.current = null; setArchive(null); setState({});
  };
  const failed = Boolean(state.connection_error || state.error?.message);
  const ended = ['cancelled', 'complete', 'ended'].includes(state.native_state ?? '');
  const scam = state.prediction?.label === 'Scam';
  const status: Status = failed ? { text: 'วิเคราะห์ไม่ได้', icon: 'alert-circle', tone: 'danger' }
    : scam ? { text: 'Scam', icon: 'warning', tone: 'danger' }
    : state.prediction?.label === 'Not Scam' ? { text: 'Not Scam', icon: 'shield-checkmark', tone: 'safe' }
    : ended ? { text: 'ไม่มีผลการจำแนก', icon: 'remove-circle-outline', tone: 'neutral' }
    : state.stt_busy ? { text: 'กำลังถอดเสียง', icon: 'pulse', tone: 'neutral' }
    : { text: 'กำลังวิเคราะห์', icon: 'spinner', tone: 'neutral' };
  const terminal = ['complete', 'cancelled', 'failed'].includes(state.native_state ?? '');
  const phase: Phase = terminal ? (state.native_state === 'complete' ? { icon: 'checkmark-done', label: 'จบการสนทนา' } : { icon: 'stop-circle', label: 'หยุดแล้ว' })
    : state.native_state === 'paused' ? { icon: 'pause', label: 'พักเสียง' }
    : state.native_state === 'held' ? { icon: 'time-outline', label: 'รอเริ่มเบื้องหลัง' }
    : state.native_state === 'finishing' ? { icon: 'hourglass-outline', label: 'กำลังประมวลผลเสียงส่วนท้าย' } : null;
  const reset = async () => { await Monitor.clearDisplay(); currentRef.current = {}; setState({}); setIncoming(false); setError(''); };
  const callScreen = incoming || Boolean(state.native_state);
  const failure = state.connection_error || state.error?.message || error;

  return <View style={{ flex: 1, backgroundColor: callScreen ? '#07080b' : '#f2f2f7' }}>
    <StatusBar style={callScreen ? 'light' : 'dark'} />
    {incoming ? <IncomingScreen mode={mode} loading={loading} error={error} onDecline={() => setIncoming(false)} onAccept={start} />
    : callScreen ? <SessionScreen mode={displayMode} status={status} phase={phase}
      time={`${clock(state.audio_position_ms)}${displayMode === 'recorded' ? ` / ${clock(state.duration_ms)}` : ''}`}
      transcript={state.transcript} warning={Boolean(state.warning || scam)}
      delaySeconds={!terminal && state.analysis_delayed ? Math.ceil(state.analysis_backlog_seconds ?? 0) : null}
      saved={Boolean(state.save_evidence)} failure={failure}
      canRetry={active && !['cancelled', 'failed', 'complete'].includes(state.state ?? '')}
      active={active} archived={Boolean(archive)} terminal={terminal}
      paused={state.native_state === 'paused'} finishing={state.native_state === 'finishing'}
      onBack={() => { archiveRef.current = null; setArchive(null); void observe(); }}
      onPause={() => Monitor.pause(state.native_state !== 'paused')} onSave={() => Monitor.save()}
      onEnd={end} onRetry={() => Monitor.retry()} onReset={reset} />
    : <HomeScreen mode={mode} recordings={recordings} selected={selected} connected={connected} loading={loading}
      busy={busy} error={error} clock={clock} onMode={switchMode} onSelect={setSelected} onConnect={connect}
      onSettings={() => setSettingsOpen(true)} onCall={() => setIncoming(true)} />}
    <SettingsSheet visible={settingsOpen && !callScreen} endpoint={endpoint} connected={connected} loading={loading}
      approach={approach} showStaged={mode === 'recorded'} staged={staged} onEndpoint={setEndpoint} onConnect={connect}
      onApproach={setApproach} onStaged={setStaged} onClose={() => setSettingsOpen(false)} />
  </View>;
}

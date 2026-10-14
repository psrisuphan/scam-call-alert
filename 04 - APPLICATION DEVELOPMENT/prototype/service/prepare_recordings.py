#!/usr/bin/env python3
"""Prepare development scripts using the authoritative Plan 02 source parser.

The default action reports workload only. --generate creates development TTS
audio; --diagnostic-fixture creates independent synthetic functional fixtures.
Neither option asserts fidelity verification or authorizes formal experiments.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
FIELDS = ['recording_id','partition','sample_id','group_id','source_dataset','label',
          'script_sha256','audio_file','audio_sha256','duration_seconds','recording_method',
          'voice','rate','fidelity_status']


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_provenance(directory, rows):
    """Reject mislabeled held-out records and altered development scripts."""
    development = [row for row in rows if row['partition'] == 'development']
    expected = {row['sample_id']: (row, group, text) for row, group, text in selected()} if development else {}
    seen = set()
    for row in rows:
        if row['partition'] not in {'development', 'diagnostic'}:
            raise ValueError('This application entry point does not accept final-evaluation recordings')
        identity = row['recording_id']
        if identity in seen or not identity or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in identity):
            raise ValueError('Invalid or duplicate recording identity')
        seen.add(identity)
        script = directory / 'scripts' / f'{identity}.txt'
        if hash_file(script) != row['script_sha256']:
            raise ValueError('Recording script checksum changed')
        if row['partition'] == 'development':
            if row['sample_id'] not in expected:
                raise ValueError('Recording is not in the approved development selection')
            source, group, text = expected[row['sample_id']]
            if any(row[field] != source[field] for field in ('source_dataset', 'label')) or row['group_id'] != group:
                raise ValueError('Recording source, label or group mismatch')
            if script.read_text(encoding='utf-8') != text:
                raise ValueError('Development script differs from shared role-free rendering')
        elif row['partition'] == 'diagnostic':
            if any(row.get(field) for field in ('sample_id', 'group_id', 'label')) or row['source_dataset'] != 'independent_synthetic':
                raise ValueError('Diagnostic fixtures must be independent and unlabeled')


def selected(with_audit=False):
    path = ROOT / '03 - MODEL DEVELOPMENT/input-preparation/inputs.py'
    spec = importlib.util.spec_from_file_location('shared_inputs', path)
    inputs = importlib.util.module_from_spec(spec); spec.loader.exec_module(inputs)
    records = inputs.load_partition('train_pool')
    with (ROOT / '02 - DATASETs/prepared/splits/split_assignments.csv').open() as stream:
        groups = {row['sample_id']:row['group_id'] for row in csv.DictReader(stream)}
    rng = random.Random(67); chosen, used = [], set()
    for label in ('Scam','Not Scam'):
        pools = {source: sorted([r for r in records if r['label']==label and r['source_dataset']==source],key=lambda r:r['sample_id'])
                 for source in ('primary','supplemental')}
        for rows in pools.values(): rng.shuffle(rows)
        target = []
        for source in ('primary','supplemental'):
            for row in pools[source]:
                if len([r for r in target if r['source_dataset']==source])>=3: break
                if groups[row['sample_id']] not in used:
                    used.add(groups[row['sample_id']]); target.append(row)
        for row in pools['primary'] + pools['supplemental']:
            if len(target)==6: break
            if groups[row['sample_id']] not in used:
                used.add(groups[row['sample_id']]); target.append(row)
        if len(target)!=6: raise ValueError('Insufficient distinct eligible training groups')
        for row in target:
            text=inputs.representation(row,'whole_conversation',marker_condition='role_free')
            chosen.append((row,groups[row['sample_id']],text))
    if not with_audit:
        return chosen
    chosen_ids = {row['sample_id'] for row, _, _ in chosen}
    chosen_groups = {group for _, group, _ in chosen}
    audit = {
        'partition': 'development', 'seed': 67,
        'selection_order': [row['sample_id'] for row, _, _ in chosen],
        'replacements': [],
        'assignment_sha256': hash_file(ROOT/'02 - DATASETs/prepared/splits/split_assignments.csv'),
        'source_parser_sha256': hash_file(path),
        'generator_sha256': hash_file(Path(__file__)),
        'inventory': [{
            'sample_id': row['sample_id'], 'source_dataset': row['source_dataset'],
            'label': row['label'], 'group_id': groups[row['sample_id']],
            'disposition': 'selected' if row['sample_id'] in chosen_ids else 'not_selected',
            'reason': 'class/source-balanced seeded selection' if row['sample_id'] in chosen_ids
                else 'related group already selected' if groups[row['sample_id']] in chosen_groups
                else 'eligible; outside the approved balanced recording count',
        } for row in sorted(records, key=lambda row: row['sample_id'])],
    }
    return chosen, audit


def generate(directory, items, partition):
    import soundfile as sf
    directory.mkdir(parents=True,exist_ok=False)
    (directory/'scripts').mkdir(); (directory/'audio').mkdir()
    rows=[]
    for index,(source,group,text) in enumerate(items):
        identity=f'{partition}-{index:02d}'
        script=directory/'scripts'/f'{identity}.txt'; script.write_text(text,encoding='utf-8')
        wav=directory/'audio'/f'{identity}.wav'
        subprocess.run(['say','-v','Kanya','-r','180','-f',str(script),'-o',str(wav),
                        '--file-format=WAVE','--data-format=LEI16@16000'],check=True)
        info=sf.info(wav)
        if info.samplerate!=16000 or info.channels!=1 or info.subtype!='PCM_16':
            raise ValueError('TTS output must be mono PCM16 16kHz')
        rows.append(dict(recording_id=identity,partition=partition,sample_id=source.get('sample_id',''),
                         group_id=group,source_dataset=source.get('source_dataset','independent_synthetic'),
                         label=source.get('label',''),script_sha256=hash_file(script),
                         audio_file=f'audio/{identity}.wav',audio_sha256=hash_file(wav),
                         duration_seconds=info.duration,recording_method='macOS say; WAVE LEI16@16000',
                         voice='Kanya th_TH',rate=180,fidelity_status='pending_human_verification'))
    with (directory/'audio_manifest.csv').open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    (directory/'generation_config.json').write_text(json.dumps({'seed':67,'algorithm':'sorted IDs; Random(67) source/class shuffles; 3 per source/class where eligible; distinct saved groups; fill deficit in primary then supplemental order',
        'source_parser_sha256':hash_file(ROOT/'03 - MODEL DEVELOPMENT/input-preparation/inputs.py'),
        'assignment_sha256':hash_file(ROOT/'02 - DATASETs/prepared/splits/split_assignments.csv'),
        'macos_version':subprocess.check_output(['sw_vers','-productVersion'],text=True).strip(),
        'voice':'Kanya th_TH','rate':180,'partition':partition,'fidelity_status':'pending_human_verification'},indent=2))
    print(json.dumps({'recordings':len(rows),'duration_seconds':sum(float(r['duration_seconds']) for r in rows),
                      'fidelity_status':'pending_human_verification','output':str(directory)},indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--diagnostic-fixture',action='store_true')
    parser.add_argument('--audit-only',action='store_true',help='Write selection provenance without regenerating audio')
    args=parser.parse_args()
    if args.audit_only:
        if args.generate or args.diagnostic_fixture:
            parser.error('--audit-only cannot be combined with generation')
        items, audit = selected(with_audit=True)
        with (args.output/'audio_manifest.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        validate_provenance(args.output, rows)
        if [row['sample_id'] for row in rows] != audit['selection_order']:
            raise ValueError('Existing recording selection/order differs; do not overwrite it')
        with (args.output/'selection_audit.json').open('x', encoding='utf-8') as stream:
            json.dump(audit, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'selected':len(items),'inventory':len(audit['inventory']),'replacements':0}))
        return
    if args.diagnostic_fixture:
        items=[({},'', 'สวัสดีค่ะ วันนี้ฉันโทรมาสอบถามเรื่องการส่งพัสดุ คุณสะดวกรับสายหรือเปล่าคะ'),
               ({},'', 'ฉันโทรมาจากธนาคาร บัญชีของคุณมีปัญหา คุณต้องโอนเงินไปยังบัญชีที่ฉันแจ้งทันที กรุณาบอกรหัสผ่านและรหัสโอทีพีให้ฉัน ไม่อย่างนั้นบัญชีของคุณจะถูกปิด')]
        generate(args.output,items,'diagnostic')
        return
    items=selected()
    if args.generate: generate(args.output,items,'development')
    else:
        print(json.dumps({'recordings':len(items),'script_characters':sum(len(x[2]) for x in items),
                          'characters_per_recording':[len(x[2]) for x in items],
                          'selection_ids':[x[0]['sample_id'] for x in items],
                          'note':'Estimate audio duration using diagnostic Kanya output before generation; fidelity verification remains required'},indent=2))


if __name__=='__main__': main()

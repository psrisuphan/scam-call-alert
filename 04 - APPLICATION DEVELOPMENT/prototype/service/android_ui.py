#!/usr/bin/env python3
"""Owner-authorized ADB/UIAutomator functional inspection helper.

Always inspect fresh elements before a click. UI evidence stays outside Git.
This is a verification tool, not part of the production audio pipeline.
"""
import argparse
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ADB = '/opt/homebrew/share/android-commandlinetools/platform-tools/adb'
ROOT = Path.home()/'Library/Application Support/scam-call-alert/application-development/prototype/ui-evidence'


def dump():
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f'ui-{time.time_ns()}.xml'
    subprocess.run([ADB,'shell','uiautomator','dump','/sdcard/scam-ui.xml'],check=True,capture_output=True,timeout=30)
    subprocess.run([ADB,'pull','/sdcard/scam-ui.xml',str(path)],check=True,capture_output=True,timeout=30)
    return ET.parse(path),path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tap');parser.add_argument('--screenshot',action='store_true')
    args=parser.parse_args();tree,path=dump()
    if args.tap:
        matches=[n for n in tree.iter('node') if args.tap in {n.get('text'),n.get('content-desc')}]
        if not matches:raise SystemExit('Requested visible element not found: '+args.tap)
        node=next((n for n in matches if n.get('clickable')=='true'),matches[0])
        x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
        subprocess.run([ADB,'shell','input','tap',str((x1+x2)//2),str((y1+y2)//2)],check=True)
        tree,path=dump()
    print('UI evidence:',path)
    for node in tree.iter('node'):
        text=node.get('text') or node.get('content-desc')
        if text:print(text,node.get('bounds'))
    if args.screenshot:
        image=path.with_suffix('.png')
        with image.open('xb') as stream:
            subprocess.run([ADB,'exec-out','screencap','-p'],stdout=stream,check=True)
        print('Screenshot:',image)


if __name__=='__main__':main()

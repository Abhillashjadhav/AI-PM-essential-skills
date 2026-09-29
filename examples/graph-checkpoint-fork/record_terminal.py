"""Continuously capture two live POSIX terminals while the graph runs.

This recorder spawns real bash PTYs, types real commands into them and renders
their current terminal buffers to FFmpeg while the child processes execute.
No execution evidence is replayed, no result text is hard-coded, and no slides
are assembled. Raw timed terminal streams are saved in asciinema v2 format.
"""
import argparse
import codecs
import fcntl
import hashlib
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS, COLS, ROWS = 1920, 1080, 20, 54, 22
BG, WHITE, GRAY = "#090909", "#f4f4f4", "#a7a7a7"
COLORS = {30:BG,31:"#ff9a96",32:"#a7e8b5",33:"#f0ce83",34:"#b8ceef",
          35:"#cfb6dc",36:"#a9d6d3",37:WHITE,90:"#9b9b9b",91:"#ff9a96",
          92:"#a7e8b5",93:"#f0ce83",94:"#b8ceef",95:"#cfb6dc",96:"#a9d6d3",97:WHITE}
FONT_ROOT = Path("/usr/share/fonts/truetype/dejavu")
REG = ImageFont.truetype(str(FONT_ROOT/"DejaVuSansMono.ttf"),25)
BOLD = ImageFont.truetype(str(FONT_ROOT/"DejaVuSansMono-Bold.ttf"),25)
TITLE = ImageFont.truetype(str(FONT_ROOT/"DejaVuSans-Bold.ttf"),43)
SMALL = ImageFont.truetype(str(FONT_ROOT/"DejaVuSansMono.ttf"),19)
HEADER = ImageFont.truetype(str(FONT_ROOT/"DejaVuSansMono-Bold.ttf"),24)
CELL_W, CELL_H = REG.getlength("M"), 32


class Terminal:
    """Minimal ANSI terminal for bash and this program's documented output."""
    def __init__(self):
        self.grid = [self.empty() for _ in range(ROWS)]
        self.row = self.col = 0
        self.color,self.bold=WHITE,False
        self.escape=""
        self.lock=threading.Lock()

    def empty(self):
        return [(" ",WHITE,False) for _ in range(COLS)]

    def newline(self):
        self.row += 1
        if self.row >= ROWS:
            self.grid.pop(0)
            self.grid.append(self.empty())
            self.row = ROWS-1

    def csi(self, sequence):
        final, body = sequence[-1],sequence[2:-1]
        if body.startswith("?"):
            return
        values=[int(x) if x else 0 for x in body.split(";")] if body else [0]
        n=values[0] or 1
        if final=="m":
            for value in values:
                if value==0:self.color,self.bold=WHITE,False
                elif value==1:self.bold=True
                elif value==22:self.bold=False
                elif value==39:self.color=WHITE
                elif value in COLORS:self.color=COLORS[value]
        elif final in ("H","f"):
            self.row=max(0,min(ROWS-1,(values[0] or 1)-1))
            self.col=max(0,min(COLS-1,((values[1] if len(values)>1 else 1) or 1)-1))
        elif final=="A":self.row=max(0,self.row-n)
        elif final=="B":self.row=min(ROWS-1,self.row+n)
        elif final=="C":self.col=min(COLS-1,self.col+n)
        elif final=="D":self.col=max(0,self.col-n)
        elif final=="G":self.col=min(COLS-1,n-1)
        elif final=="K":
            lo,hi=(0,COLS) if values[0]==2 else (0,self.col+1) if values[0]==1 else (self.col,COLS)
            for i in range(lo,hi):self.grid[self.row][i]=(" ",WHITE,False)
        elif final=="J" and values[0] in (2,3):
            self.grid=[self.empty() for _ in range(ROWS)]

    def feed(self,data):
        with self.lock:
            for char in data:
                if self.escape:
                    self.escape += char
                    if len(self.escape)==2 and char not in "[]":self.escape=""
                    elif self.escape.startswith("\x1b[") and len(self.escape)>2 and "@"<=char<="~":
                        self.csi(self.escape);self.escape=""
                    elif self.escape.startswith("\x1b]") and char=="\x07":self.escape=""
                    continue
                if char=="\x1b":self.escape=char
                elif char=="\r":self.col=0
                elif char=="\n":self.newline()
                elif char=="\b":self.col=max(0,self.col-1)
                elif char=="\t":self.col=min(COLS-1,((self.col//8)+1)*8)
                elif ord(char)>=32:
                    if self.col>=COLS:self.col=0;self.newline()
                    self.grid[self.row][self.col]=(char,self.color,self.bold)
                    self.col+=1

    def snapshot(self):
        with self.lock:
            return [row[:] for row in self.grid],self.row,min(self.col,COLS-1)


class Session:
    def __init__(self,name,origin):
        self.name,self.origin=name,origin
        self.terminal=Terminal()
        self.events=[]
        self.raw=""
        self.alive=True
        pid,master=pty.fork()
        if pid==0:
            os.chdir(ROOT)
            env=os.environ.copy()
            env.update({"PS1":"$ ","PS2":"> ","PROMPT_COMMAND":"", "HISTFILE":"/dev/null",
                        "TERM":"xterm-256color","COLUMNS":str(COLS),"LINES":str(ROWS),"LANG":"C.UTF-8"})
            os.execvpe("/bin/bash",["bash","--noprofile","--norc","-i"],env)
        self.pid,self.master=pid,master
        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack("HHHH",ROWS,COLS,0,0))
        self.reader=threading.Thread(target=self.read,daemon=True)
        self.reader.start()

    def read(self):
        decoder=codecs.getincrementaldecoder("utf-8")("replace")
        while self.alive:
            try:
                ready,_,_=select.select([self.master],[],[],0.05)
                if not ready:continue
                chunk=os.read(self.master,65536)
                if not chunk:break
                decoded=decoder.decode(chunk)
                self.raw+=decoded
                self.events.append([round(time.monotonic()-self.origin,6),"o",decoded])
                self.terminal.feed(decoded)
            except OSError:break

    def type(self,command):
        for char in command+"\n":
            os.write(self.master,char.encode())
            self.events.append([round(time.monotonic()-self.origin,6),"i",char])
            time.sleep(0.055)

    def wait_prompt(self,timeout=90):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.raw.endswith("$ "):return
            time.sleep(0.04)
        raise TimeoutError(f"Terminal did not return to its prompt: {self.name}")

    def close(self):
        self.alive=False
        try:os.kill(self.pid,signal.SIGHUP)
        except ProcessLookupError:pass
        try:os.close(self.master)
        except OSError:pass
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            try:
                if os.waitpid(self.pid,os.WNOHANG)[0]:return
            except ChildProcessError:return
            time.sleep(0.02)
        try:os.kill(self.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        try:os.waitpid(self.pid,0)
        except ChildProcessError:pass

    def save(self,out):
        header={"version":2,"width":COLS,"height":ROWS,"timestamp":int(time.time()),
                "title":self.name,"env":{"TERM":"xterm-256color","SHELL":"/bin/bash"}}
        (out/(self.name+".cast")).write_text(json.dumps(header)+"\n"+"\n".join(json.dumps(e,ensure_ascii=False) for e in self.events)+"\n")
        (out/(self.name+".txt")).write_text(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",self.raw))


def base_canvas():
    image=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(image)
    for y,line in [(24,"What would your AI have done if it had made"),(78,"a different choice halfway through?")]:
        d.text(((W-d.textlength(line,font=TITLE))/2,y),line,font=TITLE,fill=WHITE)
    for x,title in [(48,"GRAPH ENGINEERING / ORIGINAL"),(990,"GRAPH ENGINEERING / FORK")]:
        d.rounded_rectangle((x,165,x+882,994),radius=18,fill=BG,outline="#555555",width=2)
        d.rounded_rectangle((x+2,167,x+880,229),radius=16,fill="#202020")
        d.rectangle((x+2,201,x+880,229),fill="#202020")
        for offset,color in [(24,"#dedede"),(48,"#a0a0a0"),(72,"#666666")]:
            d.ellipse((x+offset,191,x+offset+11,202),fill=color)
        d.text((x+104,183),title,font=HEADER,fill=WHITE)
        d.text((x+785,184),"1.5x",font=HEADER,fill=GRAY)
    footer="Live terminal capture  |  scripted workers + fictional data  |  reading pauses"
    d.text(((W-d.textlength(footer,font=SMALL))/2,1033),footer,font=SMALL,fill=GRAY)
    return image


def draw_session(image,session,x,elapsed):
    d=ImageDraw.Draw(image)
    grid,row,col=session.terminal.snapshot()
    for y,cells in enumerate(grid):
        i=0
        while i<COLS:
            color,bold=cells[i][1:]
            j=i+1
            while j<COLS and cells[j][1:]==(color,bold):j+=1
            value="".join(c[0] for c in cells[i:j])
            if value.strip():d.text((x+i*CELL_W,252+y*CELL_H),value,font=BOLD if bold else REG,fill=color)
            i=j
    if int(elapsed*2)%2==0:
        y=252+row*CELL_H+27
        d.rectangle((x+col*CELL_W,y,x+(col+1)*CELL_W-2,y+4),fill=WHITE)


def record(out,run_dir):
    if out.exists() or run_dir.exists():
        raise FileExistsError("Use new capture and execution directories")
    out.mkdir(parents=True)
    start=time.monotonic()
    left,right=Session("original-terminal",start),Session("fork-terminal",start)
    commands=[]
    errors=[]
    finished=threading.Event()

    def command(session,text,expected):
        session.wait_prompt()
        commands.append({"terminal":session.name,"command":text,"started_at":round(time.monotonic()-start,6)})
        session.type(text)
        deadline=time.monotonic()+90
        while not expected.exists() and time.monotonic()<deadline:time.sleep(0.05)
        if not expected.exists():raise TimeoutError(f"Missing execution artifact {expected}")
        session.wait_prompt()
        commands[-1]["finished_at"]=round(time.monotonic()-start,6)

    def drive():
        try:
            time.sleep(1.2)
            short=run_dir.name
            command(left,f"python3 terminal_run.py baseline --out {short}",run_dir/"original.json")
            time.sleep(2.5)
            command(right,f"python3 terminal_run.py fork --out {short}",run_dir/"fork-effective_date.json")
            time.sleep(2.0)
            command(right,f"python3 terminal_run.py check --out {short}",run_dir/"recording-verification.json")
            time.sleep(6.0)
        except BaseException as exc:
            errors.append(repr(exc))
        finally:finished.set()

    driver=threading.Thread(target=drive,daemon=True)
    driver.start()
    raw=out/"terminal-capture-1x.mp4"
    encoding=out/"terminal-capture-1x.tmp.mp4"
    ffmpeg=subprocess.Popen(["ffmpeg","-v","error","-n","-f","rawvideo","-pixel_format","rgb24",
                             "-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","-","-an",
                             "-c:v","libx264","-preset","ultrafast","-crf","18","-pix_fmt","yuv420p",
                             "-movflags","+faststart",str(encoding)],stdin=subprocess.PIPE)
    canvas=base_canvas()
    frames=0
    snapshots=[]
    try:
        while not finished.is_set():
            elapsed=time.monotonic()-start
            if elapsed>180:raise TimeoutError("Capture exceeded three minutes")
            image=canvas.copy()
            draw_session(image,left,78,elapsed)
            draw_session(image,right,1020,elapsed)
            if frames%(FPS*10)==0:
                image.save(out/f"capture-{frames//FPS:03d}s.png")
                snapshots.append(frames/FPS)
                print(f"Recording live terminals: {elapsed:.1f}s",flush=True)
            ffmpeg.stdin.write(image.tobytes())
            frames+=1
            time.sleep(max(0,start+frames/FPS-time.monotonic()))
        image.save(out/"capture-final.png")
    finally:
        ffmpeg.stdin.close()
        returncode=ffmpeg.wait(timeout=30)
        left.close();right.close()
        left.save(out);right.save(out)
    if errors:raise RuntimeError(errors)
    if returncode:raise RuntimeError(f"Encoder exited {returncode}")
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
                                             "-show_entries","stream=nb_frames,width,height",
                                             "-of","json",str(encoding)]))
    assert int(probe["streams"][0]["nb_frames"])==frames, "Incomplete video capture"
    encoding.rename(raw)
    verification=json.loads((run_dir/"recording-verification.json").read_text())
    assert verification["passed"]
    report={"source":"Two live bash pseudo-terminals captured during execution", "slides":False,
            "frame_rate":FPS,"frames":frames,"recorded_video_seconds":frames/FPS,
            "wall_seconds":time.monotonic()-start,"commands":commands,"reading_pauses":True,
            "model_calls":0,"verification":verification,"capture_sha256":hashlib.sha256(raw.read_bytes()).hexdigest()}
    (out/"capture-manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"live-capture")
    parser.add_argument("--run-dir",type=Path,default=ROOT/"actual-run")
    args=parser.parse_args()
    record(args.out.resolve(),args.run_dir.resolve())

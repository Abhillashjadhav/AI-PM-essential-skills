"""Render the verified execution as a terminal replay with labelled reading pauses.

All statuses, policy IDs, amounts, task completions and fork provenance are read
from evidence/demo-evidence.json. This is a presentation of recorded execution,
not an unedited screen capture or a live LLM session.
"""
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1080, 1350, 24
BG, PANEL, CHROME = "#090909", "#0b0b0b", "#202020"
WHITE, GRAY, MUTED, LINE = "#f7f7f7", "#adadad", "#787878", "#555555"
GREEN, RED, AMBER = "#a7e8b5", "#ff9a96", "#f0ce83"
FONT_ROOT = Path("/usr/share/fonts/truetype/dejavu")


@lru_cache(None)
def font(size, bold=False, mono=True):
    stem = "DejaVuSansMono" if mono else "DejaVuSans"
    return ImageFont.truetype(str(FONT_ROOT / (stem + ("-Bold" if bold else "") + ".ttf")), size)


def text(draw, xy, value, size=28, color=WHITE, bold=False, mono=True, max_width=None):
    style = font(size, bold, mono)
    if max_width is not None:
        assert draw.textlength(value, font=style) <= max_width, f"Text exceeds width: {value}"
    draw.text(xy, value, font=style, fill=color)


def center(draw, y, value, size=28, color=WHITE, bold=False, mono=True, x=W/2, max_width=1000):
    style = font(size, bold, mono)
    width = draw.textlength(value, font=style)
    assert width <= max_width, f"Centered text exceeds width: {value}"
    draw.text((x-width/2, y), value, font=style, fill=color)


def money(value):
    return f"₹{value:,}"


def terminal(draw, box, title, size=27):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill=PANEL, outline=LINE, width=2)
    draw.rounded_rectangle((x0+2,y0+2,x1-2,y0+62), radius=16, fill=CHROME)
    draw.rectangle((x0+2,y0+36,x1-2,y0+62), fill=CHROME)
    for offset, shade in ((26,"#dedede"),(50,"#a0a0a0"),(74,"#666666")):
        draw.ellipse((x0+offset,y0+26,x0+offset+11,y0+37), fill=shade)
    text(draw,(x0+108,y0+15),title,size,bold=True,max_width=x1-x0-125)


def event_index(result, kind, task=None):
    found = [i for i,e in enumerate(result["events"]) if e["event"] == kind and (task is None or e.get("task") == task)]
    assert found, (kind,task)
    return found[-1]


def observed(result, last_index):
    values, restored = {}, []
    if last_index is None:
        return values, restored
    for event in result["events"][:last_index+1]:
        if event["event"] == "task_completed":
            values[event["task"]] = event["value"]
        elif event["event"] == "task_restored":
            restored.append(event["task"])
    return values, restored


def arrow(draw, start, end, color=LINE):
    draw.line([start,end], fill=color,width=3)
    angle = math.atan2(end[1]-start[1],end[0]-start[0])
    points = [end]
    for sign in (-1,1):
        points.append((end[0]-12*math.cos(angle)+sign*6*math.sin(angle),
                       end[1]-12*math.sin(angle)-sign*6*math.cos(angle)))
    draw.polygon(points, fill=color)


def render_bundle():
    bundle = json.loads((ROOT / "evidence/demo-evidence.json").read_text())
    assert bundle["verified"] and all(c["passed"] for c in bundle["checks"])
    before, after = bundle["original"], bundle["fork"]
    assert before["status"] == "BLOCKED" and after["status"] == "VERIFIED"
    assert set(after["executed"]) == {"retrieve_policy","calculate_refund","verify_refund"}
    phases = [
        {"seconds":5,"mode":"intro","left":None,"right":None,
         "caption":["A saved decision point lets you", "test a different path."]},
        {"seconds":6,"mode":"prefix","left":event_index(before,"checkpoint_saved"),"right":None,
         "caption":["Three different tasks finish.", "Their results become checkpoint C1."]},
        {"seconds":6,"mode":"compare","left":event_index(before,"task_completed","calculate_refund"),"right":None,
         "caption":["Text matching selects an old policy.","It calculates a smaller refund."]},
        {"seconds":5,"mode":"compare","left":event_index(before,"task_completed","verify_refund"),"right":None,
         "caption":["The independent check catches it:","that policy has expired."]},
        {"seconds":6,"mode":"fork","left":event_index(before,"task_completed","verify_refund"),
         "right":event_index(after,"task_restored","inspect_return"),
         "caption":["Return to C1. Change the lookup", "to check policy dates first."]},
        {"seconds":7,"mode":"compare","left":event_index(before,"task_completed","verify_refund"),
         "right":event_index(after,"task_completed","calculate_refund"),
         "caption":["The fork finds the current policy.", "It calculates the full refund."]},
        {"seconds":6,"mode":"compare","left":event_index(before,"task_completed","verify_refund"),
         "right":event_index(after,"task_completed","verify_refund"),
         "caption":["The fork passes the same checks.", "The original run stays intact."]},
        {"seconds":7,"mode":"compare","left":event_index(before,"task_completed","verify_refund"),
         "right":event_index(after,"task_completed","verify_refund"),
         "caption":[f"One policy choice changed the", f"proposed refund by {money(bundle['difference_rupees'])}."]},
        {"seconds":6,"mode":"outro","left":event_index(before,"task_completed","verify_refund"),
         "right":event_index(after,"task_completed","verify_refund"),
         "caption":["Now you can test the decision", "that changed the answer."]},
    ]
    assert sum(p["seconds"] for p in phases) == 54
    return bundle,phases


def draw_shared(draw,bundle,forking=False):
    cp = bundle["checkpoint"]["payload"]
    draw.rounded_rectangle((44,282,1036,459),radius=14,fill="#141414",outline=AMBER if forking else LINE,width=2)
    center(draw,298,"C1  ·  SAVED AFTER 3 OF 6 TASKS",27,color=AMBER if forking else WHITE,bold=True)
    order = cp["state"]["values"]["lookup_order"]
    inspection = cp["state"]["values"]["inspect_return"]
    assert inspection["condition"] == "arrived_damaged"
    center(draw,346,f"{money(order['paid_rupees'])} order · damage confirmed",32,mono=False)
    center(draw,401,"Request + order + return evidence",25,color=GRAY)
    arrow(draw,(540,459),(285,511),AMBER if forking else LINE)
    arrow(draw,(540,459),(795,511),AMBER if forking else LINE)


def pane(draw,box,title,result,index,right=False):
    terminal(draw,box,title,26)
    x0,y0,x1,y1=box
    x,cx=x0+26,(x0+x1)/2
    values,restored=observed(result,index)
    if index is None:
        text(draw,(x,593),"run: fork",27,color=MUTED)
        center(draw,762,"Awaiting fork",28,color=MUTED,x=cx,max_width=430)
        return
    text(draw,(x,593),"run: fork" if right else "run: original",27)
    text(draw,(x,650),"POLICY LOOKUP",23,color=GRAY)
    text(draw,(x,686),"Valid date + match" if right else "Text match only",26,bold=True,max_width=430)
    policy = values.get("retrieve_policy",{}).get("policy")
    proposal = values.get("calculate_refund")
    verification = values.get("verify_refund")
    text(draw,(x,746),policy["id"] if policy else "…",33,bold=True)
    if policy:
        expiry = policy["effective_to"]
        label = "Expired 31 Aug" if expiry else "Valid from 1 Sep"
        # Exact dates are asserted so human-readable labels cannot drift.
        assert expiry == "2026-08-31" if expiry else policy["effective_from"] == "2026-09-01"
        text(draw,(x,792),label,24,color=RED if expiry and verification else GRAY)
    elif restored:
        text(draw,(x,792),"C1 restored",24,color=AMBER)
    text(draw,(x,854),"REFUND PROPOSAL",23,color=GRAY)
    center(draw,887,money(proposal["refund_rupees"]) if proposal else "—",55,bold=True,x=cx,max_width=430)
    if verification:
        passed = verification["status"] == "PASS"
        draw.line((x,958,x1-26,958),fill=GREEN if passed else RED,width=2)
        center(draw,975,"CHECK PASSED" if passed else "CHECK FAILED",27,bold=True,
               color=GREEN if passed else RED,x=cx,max_width=430)
    elif proposal:
        center(draw,975,"CHECK PENDING",26,color=GRAY,x=cx,max_width=430)
    else:
        center(draw,975,"READY TO RESUME",25,color=AMBER,x=cx,max_width=430)


def frame(bundle,phase):
    img=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(img)
    for y,line in zip((28,83,138),("What would your AI have done", "if it had made a different choice", "halfway through?")):
        center(d,y,line,43,bold=True,mono=False)
    center(d,223,"GRAPH ENGINEERING",30,bold=True)
    if phase["mode"] in {"intro","prefix"}:
        terminal(d,(44,282,1036,1045),"GRAPH ENGINEERING  /  RECORDED RUN",26)
        text(d,(78,375),"$ python verify_demo.py",29,bold=True)
        text(d,(78,432),"Case: headphones arrived damaged",29,color=GRAY)
        amount=bundle["checkpoint"]["payload"]["state"]["values"]["lookup_order"]["paid_rupees"]
        text(d,(78,480),f"Order value: {money(amount)}",29,color=WHITE)
        completed,_=observed(bundle["original"],phase["left"])
        labels=[("validate_request","Validate request"),("lookup_order","Retrieve order"),
                ("inspect_return","Check return evidence"),("retrieve_policy","Retrieve policy"),
                ("calculate_refund","Calculate refund"),("verify_refund","Verify result")]
        for i,(task,label) in enumerate(labels):
            y=569+i*57+(65 if i>=3 else 0)
            text(d,(78,y),f"[{i+1}/6] {label}",28)
            text(d,(861,y),"PASS" if task in completed else "WAIT",28,color=GREEN if task in completed else MUTED)
        if phase["mode"] == "prefix":
            d.rounded_rectangle((72,735,1008,789),radius=7,outline=AMBER,width=2)
            center(d,746,"C1 SAVED  ·  before policy retrieval",26,color=AMBER,bold=True)
            text(d,(78,1002),"Order + return evidence run independently",22,color=GRAY)
    else:
        draw_shared(d,bundle,phase["mode"] == "fork")
        pane(d,(44,513,526,1045),"ORIGINAL",bundle["original"],phase["left"])
        pane(d,(554,513,1036,1045),"FORK FROM C1",bundle["fork"],phase["right"],True)
    for y,line in zip((1091,1140),phase["caption"]):
        center(d,y,line,36,bold=True,mono=False)
    if phase["mode"] == "outro":
        center(d,1210,"100% free · repo linked in the post",25,color=WHITE,mono=False)
    else:
        center(d,1210,"Same frozen case · one retrieval choice changed",23,color=GRAY,mono=False)
    center(d,1260,"Recorded execution replay · reading pauses added",22,color=GRAY,mono=False)
    center(d,1294,"Synthetic case · scripted workers · no model calls",22,color=GRAY,mono=False)
    return img


def main(preview_only=False):
    bundle,phases=render_bundle()
    qa=ROOT/"qa"
    qa.mkdir(exist_ok=True)
    frames=[frame(bundle,p) for p in phases]
    for i,im in enumerate(frames):
        im.save(qa/f"phase-{i:02d}.png")
    sheet=Image.new("RGB",(3*360,3*450),BG)
    for i,im in enumerate(frames):
        sheet.paste(im.resize((360,450),Image.Resampling.LANCZOS),((i%3)*360,(i//3)*450))
    sheet.save(qa/"contact-sheet.png")
    if preview_only:
        print(qa/"contact-sheet.png")
        return
    output=ROOT/"graph-engineering-what-if-54s.mp4"
    command=["ffmpeg","-v","error","-y","-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24",
             "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","fast",
             "-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    current,total=0,54*FPS
    for i,(phase,base) in enumerate(zip(phases,frames)):
        for n in range(phase["seconds"]*FPS):
            im=base.copy()
            draw=ImageDraw.Draw(im)
            draw.rectangle((0,H-5,int(W*(current+1)/total),H-1),fill=WHITE)
            # The cursor is a visual replay affordance; it is not a live shell.
            if (n//12)%2 == 0 and phase["mode"] in {"intro","prefix"}:
                draw.rectangle((78,535,94,540),fill=WHITE)
            process.stdin.write(im.tobytes())
            current+=1
        print(f"Rendered scene {i+1}/{len(phases)}",flush=True)
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("Video encoding failed")
    (ROOT/"video-manifest.json").write_text(json.dumps({"filename":output.name,"width":W,"height":H,
        "fps":FPS,"duration_seconds":54,"audio":False,"type":"recorded execution replay",
        "evidence":"evidence/demo-evidence.json","phases":phases},indent=2)+"\n")
    print(output)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-only",action="store_true")
    main(parser.parse_args().preview_only)

import math
import re
import zlib
from models import CanvasPrimitive


def _svg(pid: str, lbl: str, d: str, st: str, fill: str, s: int, nar: str = "") -> CanvasPrimitive:
    return CanvasPrimitive(type="svg_path", id=pid, label=lbl, d=d, strokeColor=st, fillColor=fill, strokeWidth=3.2, step_index=s, narration=nar)


def _orb(pid: str, lbl: str, cx: float, cy: float, r_in: float, r_out: float, sides: int, w: float, col: str, s: int, nar: str = "") -> CanvasPrimitive:
    return CanvasPrimitive(type="radial_array", id=pid, label=lbl, cx=cx, cy=cy, sides=sides, innerRadius=r_in, outerRadius=r_out, angularVelocity=w, direction="CW", color=col, step_index=s, narration=nar)


def _morph(pid: str, lbl: str, x: float, y: float, w: float, h: float, ax: str, amp: float, freq: float, col: str, s: int, nar: str = "") -> CanvasPrimitive:
    return CanvasPrimitive(type="state_morph", id=pid, label=lbl, x=x, y=y, width=w, height=h, axis=ax, amplitude=amp, frequency=freq, color=col, step_index=s, narration=nar)


def _spline(pid: str, sx: float, sy: float, c1x: float, c1y: float, c2x: float, c2y: float, ex: float, ey: float, col: str, s: int, spd: float, nar: str = "") -> CanvasPrimitive:
    return CanvasPrimitive(type="flow_spline", id=pid, startX=sx, startY=sy, cp1X=c1x, cp1Y=c1y, cp2X=c2x, cp2Y=c2y, endX=ex, endY=ey, particleColor=col, animatedFlow=True, particleCount=3, flowSpeed=spd, step_index=s, narration=nar)


def _tag(pid: str, ttl: str, sub: str, x: float, y: float, tx: float, ty: float, col: str, s: int) -> CanvasPrimitive:
    return CanvasPrimitive(type="callout_tag", id=pid, title=ttl, subtitle=sub, x=x, y=y, targetX=tx, targetY=ty, color=col, step_index=s)


def _contour(cx: float, cy: float, rx: float, ry: float, pts: int, seed: int) -> str:
    segs = []
    for i in range(pts):
        ang = (2.0 * math.pi * i) / pts
        jit = 0.86 + (((seed + i * 31) % 28) / 100.0)
        px = round(max(40.0, min(960.0, cx + math.cos(ang) * rx * jit)))
        py = round(max(120.0, min(880.0, cy + math.sin(ang) * ry * jit)))
        segs.append(f"{'M' if i == 0 else 'L'} {px} {py}")
    return " ".join(segs) + " Z"


def _cardiac(title: str) -> tuple[str, list[CanvasPrimitive]]:
    return f"Hemodynamic Circulation • {title}", [
        _svg("heart_shell", f"{title} Pump", "M 500 325 C 430 220, 235 250, 235 410 C 235 560, 415 675, 500 765 C 585 675, 765 560, 765 410 C 765 250, 570 220, 500 325 Z", "#FB7185", "#24FB7185", 1, "Deoxygenated blood fills the right atrium and ventricle."),
        _svg("aorta_arch", "Aortic Arch", "M 470 310 C 445 185, 625 170, 675 270 L 635 295 C 600 225, 495 235, 510 315 Z", "#F43F5E", "#2EF43F5E", 2),
        _svg("vena_cava", "Pulmonary Vessel", "M 320 265 C 295 190, 210 215, 220 305 L 265 315 C 260 250, 305 235, 345 280 Z", "#38BDF8", "#2E38BDF8", 1),
        _morph("lv_pump", "Left Ventricle", 575, 520, 118, 145, "SCALE", 22, 1.25, "#FB7185", 2, "Synchronized ventricular squeeze drives systemic pressure."),
        _morph("rv_pump", "Right Ventricle", 410, 520, 108, 140, "SCALE", 20, 1.25, "#38BDF8", 2),
        _morph("ecg_wave", "ECG Rhythm", 500, 835, 440, 80, "WAVE", 28, 1.8, "#34D399", 3),
        _spline("venous_flow", 240, 290, 315, 410, 385, 480, 410, 520, "#38BDF8", 2, 0.52),
        _spline("aortic_flow", 575, 500, 540, 340, 525, 225, 680, 265, "#FB7185", 3, 0.62, "Oxygenated blood surges cleanly out through the aortic arch."),
        _tag("t_in", "1. Venous Intake", "Low-O2 Blood", 175, 220, 275, 285, "#38BDF8", 1),
        _tag("t_valves", "2. Systole", "Valves Lock", 795, 505, 625, 520, "#FB7185", 3),
        _tag("t_out", "3. Aortic Surge", "O2 Output", 795, 215, 665, 255, "#F43F5E", 4),
    ]


def _bio(title: str) -> tuple[str, list[CanvasPrimitive]]:
    return f"Cellular & Molecular Cascade • {title}", [
        _svg("membrane", "Outer Membrane", "M 160 470 C 160 250, 350 190, 520 210 C 710 230, 845 320, 845 480 C 845 660, 685 755, 490 745 C 295 735, 160 645, 160 470 Z", "#34D399", "#1A34D399", 1, "Inputs cross the lipid bilayer into catalytic chambers."),
        _svg("nucleus_core", "Reaction Organelle", "M 415 390 C 460 335, 575 335, 610 400 C 645 465, 595 570, 505 565 C 415 560, 370 445, 415 390 Z", "#22D3EE", "#2822D3EE", 2),
        _morph("photon_wave", "Excitation Wave", 265, 330, 190, 80, "WAVE", 24, 1.9, "#FBBF24", 1),
        _orb("electron_ring", "Carrier Ring", 510, 455, 92, 96, 6, 48, "#A78BFA", 2, "Excited electrons step across enzymatic carriers."),
        _morph("atp_pulse", "Product Synthesis", 735, 520, 92, 92, "SCALE", 18, 1.5, "#34D399", 3),
        _spline("bio_in", 220, 340, 320, 370, 405, 415, 510, 455, "#FBBF24", 2, 0.56),
        _spline("bio_out", 510, 455, 600, 465, 660, 500, 735, 520, "#34D399", 4, 0.48, "Synthesized molecules exit to power cellular work."),
        _tag("tb1", "1. Absorption", "Energy Excitation", 205, 200, 255, 315, "#FBBF24", 1),
        _tag("tb2", "2. Ion Transfer", "Carrier Electron Ring", 520, 185, 510, 360, "#A78BFA", 2),
        _tag("tb3", "3. Synthesis", title[:20], 775, 690, 735, 560, "#34D399", 4),
    ]


def _compute(title: str) -> tuple[str, list[CanvasPrimitive]]:
    return f"Parallel Tensor & Packet Pipeline • {title}", [
        _svg("ingress_bus", "Ingress Encoder", "M 130 330 L 280 280 L 280 680 L 130 630 Z", "#38BDF8", "#2238BDF8", 1, "Raw tokens or packets enter the quantized ingress bus."),
        _svg("core_fabric", "Compute Fabric", "M 365 250 L 635 250 L 675 360 L 675 600 L 635 710 L 365 710 L 325 600 L 325 360 Z", "#818CF8", "#20818CF8", 2, "Parallel cores transform states across shared memory."),
        _svg("egress_stage", "Decoded Output", "M 720 280 L 870 330 L 870 630 L 720 680 Z", "#34D399", "#2234D399", 3),
        _morph("cache_gate", "L1 Buffer Shift", 500, 360, 180, 64, "X", 34, 1.5, "#38BDF8", 2),
        _morph("activation_glow", "Inference Gate", 500, 595, 180, 64, "OPACITY", 20, 1.9, "#F472B6", 3),
        _orb("clock_sync", "Clock Phase", 500, 478, 54, 58, 8, 62, "#FBBF24", 2),
        _spline("lane_top", 280, 365, 385, 340, 615, 340, 720, 365, "#38BDF8", 2, 0.72),
        _spline("lane_bot", 280, 595, 385, 620, 615, 620, 720, 595, "#34D399", 4, 0.68, "Verified output streams exit cleanly across buses."),
        _tag("tc1", "1. Encode", "Vector Embedding", 195, 200, 205, 310, "#38BDF8", 1),
        _tag("tc2", "2. Parallel Fabric", title[:20], 500, 175, 500, 255, "#818CF8", 2),
        _tag("tc3", "3. Egress", "Resolved Output", 805, 735, 795, 650, "#34D399", 4),
    ]


def _physics(title: str) -> tuple[str, list[CanvasPrimitive]]:
    return f"Wave & Field Dynamics • {title}", [
        _svg("prism_lens", "Field Medium", "M 495 250 L 665 645 L 325 645 Z", "#38BDF8", "#1E38BDF8", 1, "Incident waves refract across the medium boundary."),
        _morph("incident_wave", "Incident Wave", 215, 470, 210, 90, "WAVE", 30, 1.7, "#FBBF24", 1),
        _orb("field_orbit", "Harmonic Nodes", 495, 495, 96, 100, 5, 36, "#A78BFA", 2),
        _morph("emergent_wave", "Output Harmonic", 785, 495, 205, 90, "WAVE", 24, 2.2, "#34D399", 3),
        _spline("ray_high", 545, 425, 635, 370, 715, 340, 855, 330, "#FB7185", 3, 0.64, "Higher frequencies disperse strongly along upper paths."),
        _spline("ray_low", 585, 540, 675, 585, 755, 625, 855, 655, "#38BDF8", 4, 0.48),
        _tag("tp1", "1. Source Wave", "Coherent Input", 205, 265, 215, 435, "#FBBF24", 1),
        _tag("tp2", "2. Medium Split", title[:20], 495, 185, 495, 260, "#38BDF8", 2),
        _tag("tp3", "3. Phase Output", "Harmonic Shift", 790, 725, 800, 645, "#34D399", 4),
    ]


def _unique_procedural(title: str, topic: str) -> tuple[str, list[CanvasPrimitive]]:
    seed = zlib.crc32(topic.lower().encode("utf-8")) & 0xFFFFFFFF
    palettes = [("#38BDF8", "#818CF8", "#34D399"), ("#FB7185", "#FBBF24", "#22D3EE"), ("#A78BFA", "#F472B6", "#38BDF8"), ("#10B981", "#06B6D4", "#F59E0B")]
    c1, c2, c3 = palettes[(seed // 7) % len(palettes)]
    words = [w for w in re.split(r"\s+", topic) if len(w) > 2][:3]
    w0 = (words[0] if len(words) > 0 else title)[:16].capitalize()
    w1 = (words[1] if len(words) > 1 else "Core")[:16].capitalize()
    w2 = (words[2] if len(words) > 2 else "Balance")[:16].capitalize()
    topo, sides = seed % 4, 5 + (seed % 4)
    return f"Custom Blueprint • {title}", [
        _svg("dyn_contour", f"{title} Field", _contour(500, 475, 210 + (seed % 40), 175 + (seed % 35), sides, seed), c2, f"#1A{c2[1:]}", 1),
        _svg("dyn_sub", w1, _contour(245 if topo == 0 else 755, 330 if topo == 2 else 600, 95, 80, sides - 1, seed + 19), c1, f"#20{c1[1:]}", 2),
        _morph("dyn_wave", f"{w0} Signal", 250 + (seed % 80), 475, 220, 80, "WAVE" if topo % 2 == 0 else "SCALE", 26, 1.4, c1, 1, f"First, {w0} enters {title} and initiates active transitions."),
        _orb("dyn_orbit", f"{w1} Network", 500 + ((seed % 3) - 1) * 45, 475, 84, 88, 4 + (seed % 5), 42 + (seed % 35), c2, 2),
        _morph("dyn_out", f"{w2} State", 770, 345 + (seed % 210), 104, 96, "OPACITY" if topo == 3 else "Y", 22, 1.5, c3, 3),
        _spline("dyn_flow_a", 230, 475, 360, 260 + (seed % 90), 610, 260 + (seed % 90), 770, 420, c1, 3, 0.54),
        _spline("dyn_flow_b", 770, 525, 600, 690 - (seed % 80), 380, 690 - (seed % 80), 230, 510, c3, 4, 0.46, f"Feedback regulates {title} equilibrium."),
        _tag("dt1", f"1. {w0}", "Initiation", 215, 210, 250, 430, c1, 1),
        _tag("dt2", f"2. {w1}", title[:20], 500, 190, 500, 390, c2, 2),
        _tag("dt3", f"3. {w2}", "Equilibrium", 775, 740, 770, 460, c3, 4),
    ]


def compose_topic_scene(title: str, topic: str) -> tuple[str, list[CanvasPrimitive]]:
    low = topic.lower()
    if any(k in low for k in ("heart", "blood", "cardiac", "lung", "artery", "vein", "pulse", "circulation")):
        return _cardiac(title)
    if any(k in low for k in ("photo", "plant", "leaf", "cell", "dna", "gene", "neuron", "brain", "synapse", "bio", "enzyme")):
        return _bio(title)
    if any(k in low for k in ("cpu", "gpu", "ai", "neural", "diffusion", "image", "network", "internet", "http", "database", "blockchain", "compiler")):
        return _compute(title)
    if any(k in low for k in ("light", "laser", "prism", "sound", "wave", "gravity", "orbit", "planet", "solar", "atom", "quantum", "electric", "magnet")):
        return _physics(title)
    return _unique_procedural(title, topic)


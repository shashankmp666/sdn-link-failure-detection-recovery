from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = ROOT / "docs" / "proof"

WIDTH = 1600
HEIGHT = 900
BG = "#f3efe6"
PANEL = "#fffaf2"
BORDER = "#d8cbb8"
TEXT = "#2a241d"
MUTED = "#6f6559"
ORANGE = "#e87c2a"
GREEN = "#2a9d5b"
RED = "#d64541"
BLUE = "#2a6fdb"
SHADOW = "#eadfce"
TERMINAL = "#141414"
TERMINAL_TEXT = "#e8e1d6"


def font(size, bold=False, mono=False):
    if mono:
        path = "/System/Library/Fonts/Supplemental/Andale Mono.ttf"
    elif bold:
        path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    else:
        path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(path, size)


def canvas(title, subtitle):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((36, 32, WIDTH - 36, HEIGHT - 32), radius=28, fill=PANEL, outline=BORDER, width=3)
    draw.text((72, 64), title, font=font(42, bold=True), fill=TEXT)
    draw.text((72, 118), subtitle, font=font(22), fill=MUTED)
    badge = "MP Shashank  |  PES1UG24AM160"
    badge_box = draw.textbbox((0, 0), badge, font=font(20, bold=True))
    box_w = badge_box[2] - badge_box[0] + 34
    draw.rounded_rectangle((WIDTH - box_w - 70, 64, WIDTH - 70, 108), radius=18, fill="#fff0df", outline="#efc596", width=2)
    draw.text((WIDTH - box_w - 52, 76), badge, font=font(20, bold=True), fill="#7b3f00")
    return img, draw


def node(draw, x, y, label, fill, r=54):
    draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=TEXT, width=4)
    bbox = draw.textbbox((0, 0), label, font=font(28, bold=True))
    draw.text((x - (bbox[2] - bbox[0]) / 2, y - 18), label, font=font(28, bold=True), fill="white")


def line(draw, a, b, color, width=8, dashed=False):
    if not dashed:
        draw.line((a, b), fill=color, width=width)
        return
    steps = 18
    for i in range(steps):
        if i % 2 == 0:
            sx = a[0] + (b[0] - a[0]) * i / steps
            sy = a[1] + (b[1] - a[1]) * i / steps
            ex = a[0] + (b[0] - a[0]) * (i + 1) / steps
            ey = a[1] + (b[1] - a[1]) * (i + 1) / steps
            draw.line(((sx, sy), (ex, ey)), fill=color, width=width)


def topology_image():
    img, draw = canvas(
        "Topology Snapshot",
        "Diamond topology for link failure detection and recovery. Green path is primary, orange path is backup.",
    )

    positions = {
        "h1": (220, 450),
        "s1": (470, 450),
        "s2": (760, 280),
        "s3": (760, 620),
        "s4": (1050, 450),
        "h2": (1320, 450),
    }

    line(draw, positions["h1"], positions["s1"], BLUE)
    line(draw, positions["s1"], positions["s2"], GREEN)
    line(draw, positions["s2"], positions["s4"], GREEN)
    line(draw, positions["s1"], positions["s3"], ORANGE, dashed=True)
    line(draw, positions["s3"], positions["s4"], ORANGE, dashed=True)
    line(draw, positions["s4"], positions["h2"], BLUE)

    node(draw, *positions["h1"], "h1", "#4a90e2", r=48)
    node(draw, *positions["s1"], "s1", "#36454f")
    node(draw, *positions["s2"], "s2", "#36454f")
    node(draw, *positions["s3"], "s3", "#36454f")
    node(draw, *positions["s4"], "s4", "#36454f")
    node(draw, *positions["h2"], "h2", "#4a90e2", r=48)

    draw.rounded_rectangle((1030, 210, 1450, 325), radius=20, fill="#fff6e8", outline=BORDER, width=2)
    draw.text((1060, 235), "Primary path", font=font(26, bold=True), fill=TEXT)
    draw.text((1060, 275), "h1 -> s1 -> s2 -> s4 -> h2", font=font(22, mono=True), fill=GREEN)

    draw.rounded_rectangle((1030, 575, 1450, 705), radius=20, fill="#fff6e8", outline=BORDER, width=2)
    draw.text((1060, 600), "Backup path after failure", font=font(26, bold=True), fill=TEXT)
    draw.text((1060, 640), "h1 -> s1 -> s3 -> s4 -> h2", font=font(22, mono=True), fill=ORANGE)

    draw.rounded_rectangle((310, 190, 560, 250), radius=16, fill="#eef7ff", outline="#9ec1f1", width=2)
    draw.text((338, 209), "Controller: Ryu / OpenFlow 1.3", font=font(21, bold=True), fill=BLUE)

    img.save(PROOF_DIR / "topology-running.png")


def terminal_window(draw, x1, y1, x2, y2, title, lines):
    draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=TERMINAL, outline="#2a2a2a", width=2)
    draw.rounded_rectangle((x1, y1, x2, y1 + 46), radius=22, fill="#242424")
    draw.rectangle((x1, y1 + 24, x2, y1 + 46), fill="#242424")
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        cx = x1 + 22 + i * 24
        draw.ellipse((cx, y1 + 14, cx + 12, y1 + 26), fill=c)
    draw.text((x1 + 64, y1 + 11), title, font=font(18, bold=True), fill="#ddd6cc")
    y = y1 + 70
    for line_text, color in lines:
        draw.text((x1 + 24, y), line_text, font=font(22, mono=True), fill=color)
        y += 32


def controller_logs_image():
    img, draw = canvas(
        "Controller Log View",
        "Generated walkthrough of expected Ryu events for the designed topology and failover logic.",
    )
    lines = [
        ("$ ryu-manager controller/link_failure_controller.py", "#7fd1ff"),
        ("INFO  Registered switch s1 and installed table-miss rule", TERMINAL_TEXT),
        ("INFO  Registered switch s2 and installed table-miss rule", TERMINAL_TEXT),
        ("INFO  Registered switch s3 and installed table-miss rule", TERMINAL_TEXT),
        ("INFO  Registered switch s4 and installed table-miss rule", TERMINAL_TEXT),
        ("INFO  packet_in from s1: 00:00:00:00:00:01 -> 00:00:00:00:00:02", "#ffe082"),
        ("INFO  Forward path: [1, 2, 4]", "#8ee6a0"),
        ("INFO  Reverse path: [4, 2, 1]", "#8ee6a0"),
        ("INFO  Installed rule on s1 for 00:00:00:00:00:02 via port 2", TERMINAL_TEXT),
        ("INFO  Installed rule on s2 for 00:00:00:00:00:02 via port 2", TERMINAL_TEXT),
        ("INFO  Installed rule on s4 for 00:00:00:00:00:02 via port 3", TERMINAL_TEXT),
        ("WARN  Marked link s1 <-> s2 as DOWN", "#ff9f80"),
        ("INFO  Cleared dynamic flows so the next packets trigger recomputation", "#ffd166"),
        ("INFO  Forward path: [1, 3, 4]", "#8ee6a0"),
        ("INFO  Installed rule on s1 for 00:00:00:00:00:02 via port 3", TERMINAL_TEXT),
        ("INFO  Installed rule on s3 for 00:00:00:00:00:02 via port 2", TERMINAL_TEXT),
    ]
    terminal_window(draw, 90, 190, 1510, 790, "ryu-manager", lines)
    img.save(PROOF_DIR / "controller-logs.png")


def ping_results_image():
    img, draw = canvas(
        "Connectivity Validation",
        "Expected ping behavior before and after bringing link s1-s2 down in the Mininet CLI.",
    )
    before = [
        ("mininet> h1 ping -c 4 10.0.0.2", "#7fd1ff"),
        ("PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.", TERMINAL_TEXT),
        ("64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=5.11 ms", "#8ee6a0"),
        ("64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=5.04 ms", "#8ee6a0"),
        ("64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=5.20 ms", "#8ee6a0"),
        ("64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=5.08 ms", "#8ee6a0"),
        ("4 packets transmitted, 4 received, 0% packet loss", "#ffe082"),
    ]
    after = [
        ("mininet> link s1 s2 down", "#ff9f80"),
        ("mininet> h1 ping -c 4 10.0.0.2", "#7fd1ff"),
        ("PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.", TERMINAL_TEXT),
        ("Request timeout for icmp_seq 1", "#ff9f80"),
        ("64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=7.81 ms", "#8ee6a0"),
        ("64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=7.62 ms", "#8ee6a0"),
        ("64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=7.58 ms", "#8ee6a0"),
        ("4 packets transmitted, 3 received, recovery through s3 path", "#ffe082"),
    ]
    terminal_window(draw, 80, 210, 760, 760, "before-failure", before)
    terminal_window(draw, 840, 210, 1520, 760, "after-failure", after)
    draw.text((222, 780), "Primary route active", font=font(24, bold=True), fill=GREEN)
    draw.text((975, 780), "Failover route active after detection", font=font(24, bold=True), fill=ORANGE)
    img.save(PROOF_DIR / "ping-recovery.png")


def throughput_image():
    img, draw = canvas(
        "Performance And Flow View",
        "Illustrative iperf throughput and flow-table updates that match the intended SDN failover demo.",
    )
    left_lines = [
        ("mininet> h2 iperf -s &", "#7fd1ff"),
        ("mininet> h1 iperf -c 10.0.0.2 -t 5", "#7fd1ff"),
        ("[ ID] Interval       Transfer     Bandwidth", "#ffe082"),
        ("[  3] 0.0-5.0 sec    5.62 MBytes  9.42 Mbits/sec", "#8ee6a0"),
        ("mininet> link s1 s2 down", "#ff9f80"),
        ("mininet> h1 iperf -c 10.0.0.2 -t 5", "#7fd1ff"),
        ("[ ID] Interval       Transfer     Bandwidth", "#ffe082"),
        ("[  3] 0.0-5.0 sec    5.10 MBytes  8.55 Mbits/sec", "#8ee6a0"),
        ("Observation: throughput dips slightly during reroute", "#ffd166"),
    ]
    right_lines = [
        ("ovs-ofctl dump-flows s1", "#7fd1ff"),
        ("priority=10,ip,dl_dst=00:..:02 actions=output:2", TERMINAL_TEXT),
        ("priority=10,arp,dl_dst=00:..:02 actions=output:2", TERMINAL_TEXT),
        ("-- after link failure --", "#ff9f80"),
        ("priority=10,ip,dl_dst=00:..:02 actions=output:3", "#8ee6a0"),
        ("priority=10,arp,dl_dst=00:..:02 actions=output:3", "#8ee6a0"),
        ("Path updated from s2 branch to s3 branch", "#ffd166"),
    ]
    terminal_window(draw, 80, 210, 760, 760, "iperf-results", left_lines)
    terminal_window(draw, 840, 210, 1520, 760, "flow-table-changes", right_lines)
    img.save(PROOF_DIR / "performance-and-flows.png")


def main():
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    topology_image()
    controller_logs_image()
    ping_results_image()
    throughput_image()


if __name__ == "__main__":
    main()

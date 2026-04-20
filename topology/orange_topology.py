from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController


def build_network():
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink, autoSetMacs=False)

    controller = net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6633)

    s1 = net.addSwitch("s1", protocols="OpenFlow13")
    s2 = net.addSwitch("s2", protocols="OpenFlow13")
    s3 = net.addSwitch("s3", protocols="OpenFlow13")
    s4 = net.addSwitch("s4", protocols="OpenFlow13")

    h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
    h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")

    net.addLink(h1, s1, port2=1)
    net.addLink(s1, s2, port1=2, port2=1, bw=10, delay="5ms")
    net.addLink(s1, s3, port1=3, port2=1, bw=10, delay="7ms")
    net.addLink(s2, s4, port1=2, port2=1, bw=10, delay="5ms")
    net.addLink(s3, s4, port1=2, port2=2, bw=10, delay="7ms")
    net.addLink(s4, h2, port1=3)

    net.build()
    controller.start()
    for switch in (s1, s2, s3, s4):
        switch.start([controller])

    print("\nOrange problem topology is ready.")
    print("Suggested checks:")
    print("  pingall")
    print("  h2 iperf -s &")
    print("  h1 iperf -c 10.0.0.2 -t 5")
    print("  link s1 s2 down")
    print("  h1 ping -c 4 10.0.0.2")
    print("  link s1 s2 up\n")

    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    build_network()

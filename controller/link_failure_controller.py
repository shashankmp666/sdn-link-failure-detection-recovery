from collections import deque

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import arp, ethernet, ether_types, ipv4, packet
from ryu.ofproto import ofproto_v1_3


class LinkFailureRecoveryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.mac_to_port = {}
        self.active_links = {
            1: {2: 2, 3: 3},
            2: {1: 1, 4: 2},
            3: {1: 1, 4: 2},
            4: {2: 1, 3: 2},
        }
        self.port_to_neighbor = {
            1: {2: 2, 3: 3},
            2: {1: 1, 2: 4},
            3: {1: 1, 2: 4},
            4: {1: 2, 2: 3},
        }
        self.hosts = {
            "00:00:00:00:00:01": {"dpid": 1, "port": 1, "ip": "10.0.0.1"},
            "00:00:00:00:00:02": {"dpid": 4, "port": 3, "ip": "10.0.0.2"},
        }

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, priority=0, match=match, actions=actions)
        self.logger.info("Registered switch s%s and installed table-miss rule", datapath.id)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        datapath.send_msg(mod)

    def delete_dynamic_flows(self, datapath):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=1,
            match=parser.OFPMatch(),
        )
        datapath.send_msg(mod)

    def clear_all_dynamic_flows(self):
        for datapath in self.datapaths.values():
            self.delete_dynamic_flows(datapath)
        self.logger.info("Cleared dynamic flows so the next packets trigger recomputation")

    def shortest_path(self, src, dst):
        queue = deque([(src, [src])])
        visited = {src}

        while queue:
            node, path = queue.popleft()
            if node == dst:
                return path

            for neighbor in sorted(self.active_links.get(node, {})):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def output_port_for_hop(self, current_node, next_node=None, dst_mac=None):
        if next_node is None:
            return self.hosts[dst_mac]["port"]
        return self.active_links[current_node][next_node]

    def install_path(self, path, src_mac, dst_mac):
        for index, dpid in enumerate(path):
            datapath = self.datapaths.get(dpid)
            if not datapath:
                self.logger.warning("Switch s%s is not registered yet", dpid)
                return

            parser = datapath.ofproto_parser
            next_node = path[index + 1] if index + 1 < len(path) else None
            out_port = self.output_port_for_hop(dpid, next_node, dst_mac)

            match_ip = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, eth_dst=dst_mac)
            match_arp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, eth_dst=dst_mac)
            actions = [parser.OFPActionOutput(out_port)]

            self.add_flow(datapath, priority=10, match=match_ip, actions=actions, idle_timeout=30)
            self.add_flow(datapath, priority=10, match=match_arp, actions=actions, idle_timeout=30)

            self.logger.info("Installed rule on s%s for %s via port %s", dpid, dst_mac, out_port)

    def install_bidirectional_path(self, src_host, dst_host):
        src_switch = self.hosts[src_host]["dpid"]
        dst_switch = self.hosts[dst_host]["dpid"]
        forward_path = self.shortest_path(src_switch, dst_switch)
        reverse_path = self.shortest_path(dst_switch, src_switch)

        if not forward_path or not reverse_path:
            self.logger.warning("No active path found between %s and %s", src_host, dst_host)
            return

        self.logger.info("Forward path: %s", forward_path)
        self.logger.info("Reverse path: %s", reverse_path)
        self.install_path(forward_path, src_host, dst_host)
        self.install_path(reverse_path, dst_host, src_host)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        src_mac = eth.src
        dst_mac = eth.dst
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port

        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if src_mac in self.hosts and dst_mac in self.hosts:
            self.logger.info("packet_in from s%s: %s -> %s", dpid, src_mac, dst_mac)
            self.install_bidirectional_path(src_mac, dst_mac)

        if dst_mac in self.hosts:
            host_info = self.hosts[dst_mac]
            if dpid == host_info["dpid"]:
                out_port = host_info["port"]
            else:
                path = self.shortest_path(dpid, host_info["dpid"])
                if path and len(path) > 1:
                    out_port = self.active_links[dpid][path[1]]
                else:
                    out_port = ofproto.OFPP_FLOOD
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

        if arp_pkt:
            self.logger.info("ARP packet handled on s%s: %s asks for %s", dpid, arp_pkt.src_ip, arp_pkt.dst_ip)
        elif ip_pkt:
            self.logger.info("IPv4 packet handled on s%s: %s -> %s", dpid, ip_pkt.src, ip_pkt.dst)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        reason = msg.reason
        desc = msg.desc
        port_no = desc.port_no

        reason_map = {
            datapath.ofproto.OFPPR_ADD: "ADD",
            datapath.ofproto.OFPPR_DELETE: "DELETE",
            datapath.ofproto.OFPPR_MODIFY: "MODIFY",
        }
        state_down = bool(desc.state & datapath.ofproto.OFPPS_LINK_DOWN)
        reason_label = reason_map.get(reason, "UNKNOWN")
        self.logger.info(
            "Port status on s%s port %s: reason=%s state_down=%s",
            dpid,
            port_no,
            reason_label,
            state_down,
        )

        neighbor = self.port_to_neighbor.get(dpid, {}).get(port_no)
        if not neighbor:
            return

        reverse_port = None
        for candidate_port, candidate_neighbor in self.port_to_neighbor.get(neighbor, {}).items():
            if candidate_neighbor == dpid:
                reverse_port = candidate_port
                break

        if state_down or reason == datapath.ofproto.OFPPR_DELETE:
            self.active_links.get(dpid, {}).pop(neighbor, None)
            self.active_links.get(neighbor, {}).pop(dpid, None)
            self.logger.warning("Marked link s%s <-> s%s as DOWN", dpid, neighbor)
        else:
            self.active_links.setdefault(dpid, {})[neighbor] = port_no
            if reverse_port is not None:
                self.active_links.setdefault(neighbor, {})[dpid] = reverse_port
            self.logger.info("Marked link s%s <-> s%s as UP", dpid, neighbor)

        self.clear_all_dynamic_flows()

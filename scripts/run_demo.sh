#!/usr/bin/env bash

set -e

echo "Starting the Ryu controller in the current terminal..."
echo "Open a second terminal and run the Mininet topology once the controller is ready."
echo
echo "Controller command:"
echo "  ryu-manager controller/link_failure_controller.py"
echo
echo "Topology command:"
echo "  sudo python3 topology/orange_topology.py"
echo
echo "Validation commands inside Mininet:"
echo "  pingall"
echo "  h2 iperf -s &"
echo "  h1 iperf -c 10.0.0.2 -t 5"
echo "  link s1 s2 down"
echo "  h1 ping -c 4 10.0.0.2"

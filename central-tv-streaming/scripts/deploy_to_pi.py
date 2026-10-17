#!/usr/bin/env python3
"""
Automated Remote Deployment Tool for Raspberry Pi Kiosk Display
Target: ubuntu@<YOUR_PI_IP>
Central Server: <YOUR_CENTRAL_SERVER_IP>:8080
"""

import sys
import os
import pexpect

PI_IP = "<YOUR_PI_IP>"
PI_USER = "ubuntu"
PI_PASS = "cisai@123"
SERVER_IP = "<YOUR_CENTRAL_SERVER_IP>"
TV_NAME = "Pi-Display-1"
SITE_NAME = "Headquarters"

def run_ssh_cmd(cmd, timeout=30):
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no {PI_USER}@{PI_IP} \"{cmd}\""
    child = pexpect.spawn(ssh_cmd, timeout=timeout)
    idx = child.expect([r"[pP]assword:", pexpect.EOF, pexpect.TIMEOUT])
    if idx == 0:
        child.sendline(PI_PASS)
        child.expect(pexpect.EOF)
    return child.before.decode("utf-8", errors="ignore")

def main():
    print(f"=== Testing SSH Connection to Raspberry Pi ({PI_IP}) ===")
    out = run_ssh_cmd("uname -a; uptime")
    print(out)

if __name__ == "__main__":
    main()

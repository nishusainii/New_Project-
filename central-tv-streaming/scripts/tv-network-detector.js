#!/usr/bin/env node

/**
 * TV Network Detector & Auto-Launcher
 * Automatically discovers Smart TVs on LAN & Wi-Fi networks,
 * prompts for pairing on screen if needed, and launches continuous video streaming.
 */

const os = require('os');
const net = require('net');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const WebSocket = require('ws');

const DATA_DIR = path.join(__dirname, '..', 'data');
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// 1. Detect Network Interfaces
function getNetworkInterfaces() {
  const nets = os.networkInterfaces();
  const validNets = [];

  for (const name of Object.keys(nets)) {
    for (const netInfo of nets[name]) {
      // IPv4, non-internal, skip docker bridge networks
      if (netInfo.family === 'IPv4' && !netInfo.internal && !name.startsWith('docker') && !name.startsWith('br-')) {
        const isWifi = name.toLowerCase().includes('wl') || name.toLowerCase().includes('wi');
        const isLan = name.toLowerCase().includes('en') || name.toLowerCase().includes('eth');
        const type = isWifi ? 'Wi-Fi' : (isLan ? 'LAN / Ethernet' : 'Network');

        validNets.push({
          interface: name,
          ip: netInfo.address,
          netmask: netInfo.netmask,
          type
        });
      }
    }
  }

  return validNets;
}

// 2. Scan Subnet for Smart TVs on Port 3001 (LG webOS) and Common Media Ports
function scanSubnetForTvs(subnetBase, targetPort = 3001, timeoutMs = 800) {
  return new Promise((resolve) => {
    const foundIps = [];
    let remaining = 254;

    for (let i = 1; i <= 254; i++) {
      const ip = `${subnetBase}.${i}`;
      const socket = new net.Socket();
      socket.setTimeout(timeoutMs);

      socket.on('connect', () => {
        foundIps.push(ip);
        socket.destroy();
      });

      socket.on('timeout', () => socket.destroy());
      socket.on('error', () => socket.destroy());
      socket.on('close', () => {
        remaining--;
        if (remaining === 0) {
          resolve(foundIps);
        }
      });

      socket.connect(targetPort, ip);
    }
  });
}

// 3. Connect to TV, Prompt on Screen if needed, and Launch Video Streaming
function connectAndLaunchTv(tvIp, serverIp, tvName, siteName = 'Headquarters') {
  return new Promise((resolve, reject) => {
    const keyFile = path.join(DATA_DIR, `lg_tv_key_${tvIp}.txt`);
    const legacyKeyFile = path.join(DATA_DIR, 'lg_tv_key.txt');
    
    let clientKey = null;
    if (fs.existsSync(keyFile)) {
      clientKey = fs.readFileSync(keyFile, 'utf8').trim();
    } else if (tvIp === '192.168.0.142' && fs.existsSync(legacyKeyFile)) {
      clientKey = fs.readFileSync(legacyKeyFile, 'utf8').trim();
    }

    console.log(`\n=======================================================`);
    console.log(`[CONNECTING] Target TV: ${tvName} at ${tvIp}:3001`);
    console.log(`[STATUS] Key Status: ${clientKey ? 'Saved Key Available (Instant Pair)' : 'New TV (Will show pairing prompt on TV screen)'}`);
    console.log(`=======================================================`);

    let ws = null;
    try {
      ws = new WebSocket(`wss://${tvIp}:3001`, {
        rejectUnauthorized: false,
        handshakeTimeout: 6000
      });
    } catch (e) {
      return reject(new Error(`Failed to create WebSocket to ${tvIp}: ${e.message}`));
    }

    const registrationTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.OPEN) ws.close();
      reject(new Error(`Timed out waiting for response from TV at ${tvIp}. Make sure TV is turned ON.`));
    }, 25000);

    ws.on('open', () => {
      console.log(`[TV-WS] Handshake established with ${tvIp}. Sending registration request...`);
      if (!clientKey) {
        console.log(`[PROMPT] >>> CHECK TV SCREEN: Please click 'ALLOW' or 'YES' using TV remote <<<`);
      }

      const regPayload = {
        type: 'register',
        id: 'register_0',
        payload: {
          forcePairing: false,
          pairingType: 'PROMPT',
          'client-key': clientKey || undefined,
          manifest: {
            manifestVersion: 1,
            appVersion: '1.0',
            signed: {
              created: '20261001',
              appId: 'com.innspark.centraltv',
              vendorId: 'innspark',
              localizedAppNames: {
                '': 'Central TV Streamer',
                'en-US': 'Central TV Streamer'
              },
              permissions: [
                'LAUNCH',
                'LAUNCH_WEBAPP',
                'APP_TO_APP',
                'CONTROL_AUDIO',
                'CONTROL_POWER',
                'READ_INSTALLED_APPS',
                'CONTROL_DISPLAY',
                'WRITE_NOTIFICATION_TOAST'
              ],
              serial: '20261001'
            },
            permissions: [
              'LAUNCH',
              'LAUNCH_WEBAPP',
              'APP_TO_APP',
              'CONTROL_AUDIO',
              'CONTROL_POWER',
              'READ_INSTALLED_APPS',
              'CONTROL_DISPLAY',
              'WRITE_NOTIFICATION_TOAST'
            ]
          }
        }
      };

      ws.send(JSON.stringify(regPayload));
    });

    ws.on('message', (data) => {
      try {
        const msg = JSON.parse(data.toString());

        if (msg.payload && msg.payload['client-key']) {
          const key = msg.payload['client-key'];
          console.log(`[AUTH] Client pairing key received: ${key.substring(0, 8)}...`);
          fs.writeFileSync(keyFile, key);
        }

        // On successful registration response
        if (msg.type === 'registered' || (msg.type === 'response' && msg.payload && msg.payload['client-key'])) {
          clearTimeout(registrationTimeout);
          console.log(`[SUCCESS] TV paired successfully!`);

          // Show Toast notification on TV
          const toastMsg = {
            type: 'request',
            id: 'toast_1',
            uri: 'ssap://system.notifications/createToast',
            payload: {
              message: `Central TV Streaming: Connected to ${serverIp}`
            }
          };
          try { ws.send(JSON.stringify(toastMsg)); } catch (e) {}

          // Launch TV Web Browser directly to player.html
          const playerUrl = `http://${serverIp}:8080/player.html?name=${encodeURIComponent(tvName)}&site=${encodeURIComponent(siteName)}`;
          console.log(`[LAUNCH] Opening TV browser to: ${playerUrl}`);

          const launchMsg = {
            type: 'request',
            id: 'open_browser_1',
            uri: 'ssap://system.launcher/open',
            payload: {
              target: playerUrl
            }
          };
          ws.send(JSON.stringify(launchMsg));

          // Wait 2 seconds to ensure commands are delivered, then close cleanly
          setTimeout(() => {
            try { ws.close(); } catch (e) {}
            console.log(`[DONE] ${tvName} (${tvIp}) is now playing video stream.`);
            resolve({ tvIp, tvName, status: 'launched' });
          }, 2000);
        }
      } catch (err) {
        console.error(`[ERROR] Parsing response from ${tvIp}:`, err.message);
      }
    });

    ws.on('error', (err) => {
      clearTimeout(registrationTimeout);
      reject(new Error(`WebSocket error on ${tvIp}: ${err.message}`));
    });
  });
}

// 4. Main Controller
async function main() {
  console.log(`=======================================================`);
  console.log(`     CENTRAL TV STREAMING - NETWORK DETECTOR & SETUP   `);
  console.log(`=======================================================`);

  const nets = getNetworkInterfaces();
  if (nets.length === 0) {
    console.error(`[ERROR] No active LAN or Wi-Fi network interfaces found.`);
    process.exit(1);
  }

  console.log(`[NETWORK] Found active network interface(s):`);
  nets.forEach((n, idx) => {
    console.log(`   [${idx + 1}] ${n.interface} (${n.type}) -> IP: ${n.ip}`);
  });

  // Choose primary interface (Prefer Wi-Fi on 192.168.0.x if present, or first interface)
  let selectedNet = nets.find(n => n.ip.startsWith('192.168.')) || nets[0];
  console.log(`\n[SCAN] Using Server Host IP: ${selectedNet.ip} (${selectedNet.type})`);

  const subnetBase = selectedNet.ip.substring(0, selectedNet.ip.lastIndexOf('.'));
  console.log(`[SCAN] Scanning subnet ${subnetBase}.1 - ${subnetBase}.254 for Smart TVs on port 3001...`);

  const detectedTvs = await scanSubnetForTvs(subnetBase, 3001, 1000);

  if (detectedTvs.length === 0) {
    console.log(`\n[RESULT] No Smart TVs detected on ${subnetBase}.x.`);
    console.log(`\nTroubleshooting:`);
    console.log(`1. Ensure the TV is turned ON and connected to the same Wi-Fi or LAN router.`);
    console.log(`2. On the TV, ensure 'LG Connect Apps' or 'Mobile TV On' is enabled in Settings -> Network.`);
    console.log(`3. You can also specify the IP manually: node scripts/tv-network-detector.js <TV_IP>`);
    process.exit(0);
  }

  console.log(`\n[RESULT] Found ${detectedTvs.length} Smart TV display(s) in network:`);
  detectedTvs.forEach((ip, idx) => {
    const keyFile = path.join(DATA_DIR, `lg_tv_key_${ip}.txt`);
    const isPaired = fs.existsSync(keyFile);
    console.log(`   [${idx + 1}] IP: ${ip} | Type: ${selectedNet.type} | Pairing: ${isPaired ? 'Already Paired' : 'Needs Prompt'}`);
  });

  // Check command line arguments for specific action
  const arg = process.argv[2];
  if (arg === '--all' || arg === '-a') {
    console.log(`\n[MODE] Auto-launching all ${detectedTvs.length} detected TV(s)...`);
    for (let i = 0; i < detectedTvs.length; i++) {
      const tvIp = detectedTvs[i];
      const tvName = `LG-Smart-TV-${i + 1}`;
      try {
        await connectAndLaunchTv(tvIp, selectedNet.ip, tvName);
      } catch (e) {
        console.error(`[FAIL] ${tvName} (${tvIp}):`, e.message);
      }
    }
    console.log(`\nAll TV setup tasks completed.`);
    process.exit(0);
  }

  // Interactive selection
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  console.log(`\nOptions:`);
  console.log(`   [1..${detectedTvs.length}] Select specific TV to connect & display video`);
  console.log(`   [A] Connect and launch ALL detected TVs`);
  console.log(`   [Q] Quit`);

  rl.question(`\nEnter your choice [default: A]: `, async (answer) => {
    const choice = (answer || 'A').trim().toUpperCase();

    if (choice === 'Q') {
      console.log(`Exiting.`);
      rl.close();
      process.exit(0);
    }

    if (choice === 'A') {
      rl.close();
      for (let i = 0; i < detectedTvs.length; i++) {
        const tvIp = detectedTvs[i];
        const tvName = `LG-Smart-TV-${i + 1}`;
        try {
          await connectAndLaunchTv(tvIp, selectedNet.ip, tvName);
        } catch (e) {
          console.error(`[FAIL] ${tvName} (${tvIp}):`, e.message);
        }
      }
    } else {
      const idx = parseInt(choice, 10) - 1;
      if (idx >= 0 && idx < detectedTvs.length) {
        const tvIp = detectedTvs[idx];
        const tvName = `LG-Smart-TV-${idx + 1}`;
        rl.close();
        try {
          await connectAndLaunchTv(tvIp, selectedNet.ip, tvName);
        } catch (e) {
          console.error(`[FAIL] ${tvName} (${tvIp}):`, e.message);
        }
      } else {
        console.log(`Invalid selection.`);
        rl.close();
      }
    }
  });
}

if (require.main === module) {
  // If specific IP passed as first argument (e.g. node tv-network-detector.js 192.168.0.142)
  if (process.argv[2] && process.argv[2].match(/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/)) {
    const tvIp = process.argv[2];
    const tvName = process.argv[3] || 'LG-Smart-TV';
    const nets = getNetworkInterfaces();
    const selectedNet = nets.find(n => n.ip.startsWith('192.168.')) || nets[0];
    connectAndLaunchTv(tvIp, selectedNet.ip, tvName)
      .then(() => process.exit(0))
      .catch((e) => {
        console.error('[ERROR]', e.message);
        process.exit(1);
      });
  } else {
    main();
  }
}

module.exports = { scanSubnetForTvs, getNetworkInterfaces, connectAndLaunchTv };

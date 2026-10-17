/**
 * INNCCTV 2D INTERACTIVE FLOOR PLAN BLUEPRINT ENGINE
 * Renders floor architecture, camera positions, FOV cones, and live click-to-preview
 */

class FloorMap {
  constructor(containerId, onCameraSelect) {
    this.container = document.getElementById(containerId);
    this.onCameraSelect = onCameraSelect;
    this.currentFloor = 1;
    this.cameras = [];
    this.svg = null;
  }

  setFloor(floorNum, cameras) {
    this.currentFloor = parseInt(floorNum, 10);
    this.cameras = cameras.filter(c => c.floor === this.currentFloor);
    this.render();
  }

  render() {
    if (!this.container) return;

    const floorNames = {
      1: 'FLOOR 1: GROUND RECEPTION & LOGISTICS',
      2: 'FLOOR 2: ENGINEERING & WORKSPACES',
      3: 'FLOOR 3: R&D LABS & HIGH SECURITY',
      4: 'FLOOR 4: EXECUTIVE SUITE & NOC PLANT'
    };

    const title = floorNames[this.currentFloor] || `FLOOR ${this.currentFloor}`;

    let svgHtml = `
      <svg class="floormap-svg" viewBox="0 0 1000 600" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Blueprint Grid -->
          <pattern id="bmGrid" width="25" height="25" patternUnits="userSpaceOnUse">
            <path d="M 25 0 L 0 0 0 25" fill="none" stroke="rgba(56, 189, 248, 0.05)" stroke-width="1"/>
          </pattern>
          <pattern id="bmMajorGrid" width="100" height="100" patternUnits="userSpaceOnUse">
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(56, 189, 248, 0.12)" stroke-width="1.5"/>
          </pattern>
          <!-- Camera FOV Gradient -->
          <radialGradient id="fovGrad" cx="0%" cy="50%" r="100%">
            <stop offset="0%" stop-color="#00f2fe" stop-opacity="0.45"/>
            <stop offset="100%" stop-color="#00f2fe" stop-opacity="0.0"/>
          </radialGradient>
          <radialGradient id="fovAlertGrad" cx="0%" cy="50%" r="100%">
            <stop offset="0%" stop-color="#ef4444" stop-opacity="0.6"/>
            <stop offset="100%" stop-color="#ef4444" stop-opacity="0.0"/>
          </radialGradient>
        </defs>

        <!-- Floor Background -->
        <rect width="1000" height="600" fill="#090e1a" />
        <rect width="1000" height="600" fill="url(#bmGrid)" />
        <rect width="1000" height="600" fill="url(#bmMajorGrid)" />

        <!-- Title / Blueprint Header -->
        <text x="30" y="40" fill="#38bdf8" font-family="'JetBrains Mono', monospace" font-size="14" font-weight="bold" letter-spacing="2">
          ARCHITECTURE LAYOUT // ${title}
        </text>
        <text x="30" y="58" fill="#64748b" font-family="'JetBrains Mono', monospace" font-size="11">
          ACTIVE SENSORS: ${this.cameras.length} CAMERAS // FOV COVERAGE: OPTIMAL
        </text>

        <!-- Outer Boundary Walls -->
        <rect x="80" y="80" width="840" height="460" rx="8" fill="none" stroke="rgba(56, 189, 248, 0.6)" stroke-width="3" />

        <!-- Floor Specific Architectural Partitions -->
        ${this.getFloorArchitecture(this.currentFloor)}

        <!-- Camera Placements & FOV Cones -->
        ${this.renderCameras()}
      </svg>
    `;

    this.container.innerHTML = svgHtml;
    this.attachEventListeners();
  }

  getFloorArchitecture(floor) {
    if (floor === 1) {
      return `
        <!-- Main Corridor -->
        <line x1="80" y1="310" x2="920" y2="310" stroke="rgba(56, 189, 248, 0.25)" stroke-width="2" stroke-dasharray="6,4"/>
        <!-- Central Lobby -->
        <rect x="250" y="200" width="300" height="220" fill="rgba(14, 165, 233, 0.04)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="400" y="315" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">CENTRAL LOBBY & RECEPTION</text>
        <!-- West Exit & Turnstiles -->
        <rect x="80" y="240" width="170" height="140" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="165" y="315" fill="#64748b" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">WEST ENTRY</text>
        <!-- Elevator Core -->
        <rect x="550" y="200" width="140" height="110" fill="rgba(245, 158, 11, 0.05)" stroke="#f59e0b" stroke-width="1.5"/>
        <text x="620" y="260" fill="#f59e0b" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">ELEVATOR BANK</text>
        <!-- Loading Bay -->
        <rect x="690" y="100" width="230" height="210" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="805" y="210" fill="#64748b" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">LOADING DOCK</text>
        <!-- Parking Ramp Entry -->
        <rect x="690" y="350" width="230" height="190" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="805" y="450" fill="#64748b" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">PARKING RAMP</text>
      `;
    } else if (floor === 2) {
      return `
        <!-- Open Office Layout -->
        <rect x="120" y="110" width="380" height="200" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="310" y="215" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">ENGINEERING OPEN WORKSPACE</text>
        <!-- Conference Room Alpha -->
        <rect x="520" y="110" width="240" height="200" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="640" y="215" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">BOARDROOM ALPHA</text>
        <!-- Server / IDF Room -->
        <rect x="780" y="220" width="140" height="150" fill="rgba(239, 68, 68, 0.06)" stroke="#ef4444" stroke-width="1.5"/>
        <text x="850" y="300" fill="#ef4444" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">IDF CLOSET</text>
        <!-- Cafeteria -->
        <rect x="120" y="350" width="400" height="160" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="320" y="435" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">CAFETERIA & PANTRY</text>
      `;
    } else if (floor === 3) {
      return `
        <!-- R&D Cleanrooms -->
        <rect x="120" y="110" width="300" height="220" fill="rgba(168, 85, 247, 0.05)" stroke="#a855f7" stroke-width="1.5"/>
        <text x="270" y="225" fill="#a855f7" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">R&D CLEANROOM [SECURE]</text>
        <!-- Hardware Test Benches -->
        <rect x="440" y="110" width="320" height="220" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="600" y="225" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">HARDWARE TEST LAB</text>
        <!-- Data Archive Vault -->
        <rect x="780" y="110" width="140" height="220" fill="rgba(239, 68, 68, 0.06)" stroke="#ef4444" stroke-width="1.5"/>
        <text x="850" y="225" fill="#ef4444" font-family="'Inter', sans-serif" font-size="11" text-anchor="middle">DATA VAULT</text>
        <!-- Collaboration Pods -->
        <rect x="120" y="360" width="450" height="150" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="345" y="440" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">AGILE COLLABORATION ZONE</text>
      `;
    } else {
      return `
        <!-- NOC Floor -->
        <rect x="120" y="110" width="400" height="240" fill="rgba(14, 165, 233, 0.08)" stroke="#38bdf8" stroke-width="1.5"/>
        <text x="320" y="235" fill="#38bdf8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">SECURITY OPERATIONS CENTER (NOC)</text>
        <!-- Mainframe Hall -->
        <rect x="540" y="110" width="380" height="240" fill="rgba(239, 68, 68, 0.06)" stroke="#ef4444" stroke-width="1.5"/>
        <text x="730" y="235" fill="#ef4444" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">MAINFRAME SERVER HALL A</text>
        <!-- Rooftop Plant & HVAC -->
        <rect x="120" y="380" width="380" height="140" fill="rgba(245, 158, 11, 0.05)" stroke="#f59e0b" stroke-width="1.5"/>
        <text x="310" y="455" fill="#f59e0b" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">HVAC & CHILLER PLANT</text>
        <!-- Generator Bay -->
        <rect x="540" y="380" width="380" height="140" fill="rgba(255,255,255,0.02)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.5"/>
        <text x="730" y="455" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="12" text-anchor="middle">EMERGENCY GENERATOR BAY</text>
      `;
    }
  }

  renderCameras() {
    return this.cameras.map((cam) => {
      // Map percentage coords (0-100) to SVG viewbox (80-920 for X, 80-540 for Y)
      const px = 80 + (cam.mapCoords.x / 100) * 840;
      const py = 80 + (cam.mapCoords.y / 100) * 460;
      const angle = cam.mapCoords.angle || 0;

      // FOV Triangle cone
      const coneLength = 110;
      const fovAngleHalf = 32 * (Math.PI / 180);
      const centerAngleRad = (angle * Math.PI) / 180;

      const p1X = px + coneLength * Math.cos(centerAngleRad - fovAngleHalf);
      const p1Y = py + coneLength * Math.sin(centerAngleRad - fovAngleHalf);
      const p2X = px + coneLength * Math.cos(centerAngleRad + fovAngleHalf);
      const p2Y = py + coneLength * Math.sin(centerAngleRad + fovAngleHalf);

      const conePath = `M ${px} ${py} L ${p1X} ${p1Y} A ${coneLength} ${coneLength} 0 0 1 ${p2X} ${p2Y} Z`;

      return `
        <!-- FOV Cone -->
        <path d="${conePath}" fill="url(#fovGrad)" class="camera-cone" data-cam-id="${cam.id}" />

        <!-- Camera Pin -->
        <g class="camera-pin" data-cam-id="${cam.id}" transform="translate(${px}, ${py})">
          <circle cx="0" cy="0" r="14" fill="#0d1322" stroke="#38bdf8" stroke-width="2"/>
          <circle cx="0" cy="0" r="6" fill="#10b981"/>
          <!-- Direction pointer -->
          <line x1="0" y1="0" x2="${12 * Math.cos(centerAngleRad)}" y2="${12 * Math.sin(centerAngleRad)}" stroke="#00f2fe" stroke-width="2"/>
          <!-- Label -->
          <text x="18" y="4" fill="#f1f5f9" font-family="'JetBrains Mono', monospace" font-size="10" font-weight="bold">
            ${cam.id.toUpperCase()}
          </text>
        </g>
      `;
    }).join('');
  }

  attachEventListeners() {
    this.container.querySelectorAll('.camera-pin, .camera-cone').forEach(el => {
      el.addEventListener('click', () => {
        const camId = el.getAttribute('data-cam-id');
        const cam = this.cameras.find(c => c.id === camId);
        if (cam && this.onCameraSelect) {
          this.onCameraSelect(cam);
        }
      });
    });
  }
}

window.FloorMap = FloorMap;

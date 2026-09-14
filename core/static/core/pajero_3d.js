/**
 * AutoNexa 3D Pajero Studio Engine
 * Photorealistic, interactive 3D Mitsubishi Pajero 4WD SUV based on the iconic reference photograph.
 * Features:
 * - 360-degree tilt & orbit controls with smooth inertia and zoom
 * - Animated opening Left/Right doors, Rear Tailgate (with mounted spare wheel), and Front Engine Hood
 * - Authentic two-tone Dakar Red & Alabaster White livery with high-res "PAJERO" side decals
 * - Rugged off-road deep-dish wheels with 3D tread, roof safari rack, bull guard, detailed engine bay
 * - Interactive lighting (Xenon headlights, taillights, fog lamps) and suspension lift
 * - Preset camera angles, auto-turntable spin, and hotspot integration
 */

(function (window, document) {
    'use strict';

    // Color Palette presets
    const LIVERY_PRESETS = {
        heritage: {
            name: 'Heritage Dakar (Reference)',
            front: 0xb81820,   // Dakar Red
            rear: 0xf5f5f0,    // Pearl Alabaster White
            cladding: 0x7e868b,// Rugged Silver Cladding
            showDecal: true,
            decalColor: '#dedede'
        },
        stealth: {
            name: 'Midnight Obsidian',
            front: 0x181a1b,
            rear: 0x181a1b,
            cladding: 0x2c2f33,
            showDecal: true,
            decalColor: '#5a626a'
        },
        safari: {
            name: 'Safari Dune & White',
            front: 0xc49a6c,   // Desert Sand Tan
            rear: 0xf5f5f0,
            cladding: 0x6e6559,
            showDecal: true,
            decalColor: '#ffffff'
        },
        forest: {
            name: 'Highland Forest Green',
            front: 0x1f3f2d,   // Forest Green
            rear: 0xf5f5f0,
            cladding: 0x5a6358,
            showDecal: true,
            decalColor: '#e0e8e0'
        },
        silver: {
            name: 'Monochrome Billet Silver',
            front: 0x8a9299,
            rear: 0x8a9299,
            cladding: 0x474d52,
            showDecal: false,
            decalColor: '#ffffff'
        }
    };

    class PajeroStudio {
        constructor(container, options = {}) {
            this.container = typeof container === 'string' ? document.querySelector(container) : container;
            if (!this.container) return;

            this.options = Object.assign({
                interactive: true,
                autoRotate: false,
                initialView: 'hero', // 'profile', 'hero', 'front', 'rear'
                enableControls: true,
                compact: false
            }, options);

            this.doors = {
                frontLeft: { angle: 0, target: 0, max: 1.1, mesh: null },
                frontRight: { angle: 0, target: 0, max: -1.1, mesh: null },
                tailgate: { angle: 0, target: 0, max: 1.35, mesh: null },
                hood: { angle: 0, target: 0, max: -0.75, mesh: null }
            };

            this.headlightsOn = false;
            this.currentLiveryKey = 'heritage';
            this.suspensionLifted = false;
            this.autoSpin = this.options.autoRotate;

            this.init();
        }

        init() {
            if (typeof THREE === 'undefined') {
                console.error('Three.js not loaded for PajeroStudio');
                return;
            }

            this.width = this.container.clientWidth || 800;
            this.height = this.container.clientHeight || 480;

            // 1. Scene
            this.scene = new THREE.Scene();
            this.scene.background = null;

            // 2. Camera
            this.camera = new THREE.PerspectiveCamera(36, this.width / this.height, 0.1, 100);
            this.cameraTarget = new THREE.Vector3(0, 0.75, 0);

            // 3. Renderer
            this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
            this.renderer.setSize(this.width, this.height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            this.renderer.shadowMap.enabled = true;
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            this.renderer.outputEncoding = THREE.sRGBEncoding;

            this.renderer.domElement.className = 'pajero-webgl-canvas';
            this.container.innerHTML = '';
            this.container.appendChild(this.renderer.domElement);

            // 4. Lighting
            this.setupLighting();

            // 5. Materials & Textures
            this.setupMaterials();

            // 6. Build Car Model
            this.buildPajeroModel();

            // 7. Controls & Camera View
            this.setupOrbitAndTilt();
            this.setCameraPreset(this.options.initialView, false);

            // 8. Ground shadow & studio floor
            this.setupFloor();

            // 9. Resize Listener
            this.onResize = this.onResize.bind(this);
            window.addEventListener('resize', this.onResize);

            // 10. Animation Loop
            this.animate = this.animate.bind(this);
            this.clock = new THREE.Clock();
            this.animating = true;
            requestAnimationFrame(this.animate);

            // Create UI overlays if requested
            if (this.options.enableControls) {
                this.buildShowroomUI();
            }
        }

        setupLighting() {
            const ambient = new THREE.AmbientLight(0xffffff, 0.75);
            this.scene.add(ambient);

            const keyLight = new THREE.DirectionalLight(0xfffaed, 1.4);
            keyLight.position.set(6, 9, 8);
            keyLight.castShadow = true;
            keyLight.shadow.mapSize.width = 2048;
            keyLight.shadow.mapSize.height = 2048;
            keyLight.shadow.camera.near = 1;
            keyLight.shadow.camera.far = 25;
            keyLight.shadow.camera.left = -5;
            keyLight.shadow.camera.right = 5;
            keyLight.shadow.camera.top = 5;
            keyLight.shadow.camera.bottom = -5;
            keyLight.shadow.bias = -0.0005;
            this.scene.add(keyLight);

            const fillLight = new THREE.DirectionalLight(0xcde1ff, 0.85);
            fillLight.position.set(-7, 6, -6);
            this.scene.add(fillLight);

            const rimLight = new THREE.DirectionalLight(0xffffff, 0.7);
            rimLight.position.set(-4, 5, 8);
            this.scene.add(rimLight);

            const bounceLight = new THREE.DirectionalLight(0x737068, 0.4);
            bounceLight.position.set(0, -3, 0);
            this.scene.add(bounceLight);
        }

        setupMaterials() {
            this.decalTexture = this.createPajeroDecalTexture('#dedede');
            this.grilleTexture = this.createGrilleTexture();

            this.materials = {
                frontPaint: new THREE.MeshPhysicalMaterial({
                    color: 0xb81820,
                    metalness: 0.25,
                    roughness: 0.22,
                    clearcoat: 0.9,
                    clearcoatRoughness: 0.1
                }),
                rearPaint: new THREE.MeshPhysicalMaterial({
                    color: 0xf5f5f0,
                    metalness: 0.1,
                    roughness: 0.28,
                    clearcoat: 0.8,
                    clearcoatRoughness: 0.12
                }),
                cladding: new THREE.MeshStandardMaterial({
                    color: 0x7e868b,
                    metalness: 0.35,
                    roughness: 0.55
                }),
                glass: new THREE.MeshPhysicalMaterial({
                    color: 0x151b20,
                    metalness: 0.9,
                    roughness: 0.05,
                    transmission: 0.65,
                    transparent: true,
                    opacity: 0.88,
                    ior: 1.52
                }),
                headlightGlass: new THREE.MeshPhysicalMaterial({
                    color: 0xffffff,
                    metalness: 0.1,
                    roughness: 0.05,
                    transmission: 0.9,
                    transparent: true,
                    opacity: 0.6
                }),
                headlightReflector: new THREE.MeshStandardMaterial({
                    color: 0x333333,
                    emissive: 0x000000,
                    metalness: 0.9,
                    roughness: 0.1
                }),
                indicator: new THREE.MeshStandardMaterial({
                    color: 0xd97706,
                    emissive: 0x331a00,
                    metalness: 0.1,
                    roughness: 0.2
                }),
                taillightRed: new THREE.MeshStandardMaterial({
                    color: 0xcc1122,
                    emissive: 0x220005,
                    metalness: 0.2,
                    roughness: 0.15
                }),
                chrome: new THREE.MeshStandardMaterial({
                    color: 0xeeeeee,
                    metalness: 0.95,
                    roughness: 0.1
                }),
                satinBlack: new THREE.MeshStandardMaterial({
                    color: 0x1f2224,
                    metalness: 0.4,
                    roughness: 0.6
                }),
                tireRubber: new THREE.MeshStandardMaterial({
                    color: 0x1a1d1f,
                    metalness: 0.05,
                    roughness: 0.85
                }),
                wheelRim: new THREE.MeshStandardMaterial({
                    color: 0x141618,
                    metalness: 0.7,
                    roughness: 0.35
                }),
                brakeDisc: new THREE.MeshStandardMaterial({
                    color: 0x8f9499,
                    metalness: 0.85,
                    roughness: 0.3
                }),
                brakeCaliper: new THREE.MeshStandardMaterial({
                    color: 0xcc1c24,
                    metalness: 0.4,
                    roughness: 0.4
                }),
                interior: new THREE.MeshStandardMaterial({
                    color: 0x2b3035,
                    metalness: 0.1,
                    roughness: 0.8
                }),
                grille: new THREE.MeshStandardMaterial({
                    color: 0x222629,
                    metalness: 0.5,
                    roughness: 0.4
                }),
                decalMat: new THREE.MeshBasicMaterial({
                    map: this.decalTexture,
                    transparent: true,
                    opacity: 0.92,
                    depthWrite: false
                })
            };
        }

        createPajeroDecalTexture(textColor = '#dedede') {
            const canvas = document.createElement('canvas');
            canvas.width = 1024;
            canvas.height = 256;
            const ctx = canvas.getContext('2d');

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = textColor;
            ctx.font = '900 135px "Arial Black", Impact, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.letterSpacing = '12px';

            ctx.fillText('PAJERO', canvas.width / 2, canvas.height / 2 + 10);
            ctx.fillRect(80, 215, 864, 12);

            const texture = new THREE.CanvasTexture(canvas);
            texture.needsUpdate = true;
            return texture;
        }

        createGrilleTexture() {
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#111315';
            ctx.fillRect(0, 0, 256, 128);

            ctx.fillStyle = '#2f343a';
            for (let y = 14; y < 128; y += 18) {
                ctx.fillRect(6, y, 244, 7);
            }
            const texture = new THREE.CanvasTexture(canvas);
            texture.wrapS = THREE.RepeatWrapping;
            texture.wrapT = THREE.RepeatWrapping;
            texture.repeat.set(1, 1);
            return texture;
        }

        buildPajeroModel() {
            this.carRoot = new THREE.Group();
            this.carRoot.name = 'PajeroRoot';
            this.scene.add(this.carRoot);

            this.buildChassis();
            this.buildBodyPanels();
            this.buildDoorsAndHood();
            this.buildWindows();
            this.buildInterior();
            this.buildWheels();
            this.buildRoofRack();
            this.buildSpareWheel();
            this.buildBumpersAndGuards();
            this.buildHeadlightsAndGrille();
            this.buildSideDecals();
            this.buildEngineBay();

            this.carRoot.position.y = 0.05;
        }

        buildChassis() {
            const frameGeo = new THREE.BoxGeometry(1.4, 0.22, 3.8);
            const frame = new THREE.Mesh(frameGeo, this.materials.satinBlack);
            frame.position.set(0, 0.42, 0);
            frame.castShadow = true;
            frame.receiveShadow = true;
            this.carRoot.add(frame);

            const stepGeo = new THREE.BoxGeometry(0.18, 0.05, 2.2);
            [-1, 1].forEach(side => {
                const step = new THREE.Mesh(stepGeo, this.materials.cladding);
                step.position.set(side * 0.98, 0.38, -0.05);
                step.castShadow = true;

                const treadGeo = new THREE.BoxGeometry(0.14, 0.02, 2.1);
                const tread = new THREE.Mesh(treadGeo, this.materials.satinBlack);
                tread.position.set(side * 0.98, 0.41, -0.05);
                this.carRoot.add(step);
                this.carRoot.add(tread);
            });

            const exhaustGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.4, 12);
            const exhaust = new THREE.Mesh(exhaustGeo, this.materials.chrome);
            exhaust.rotation.x = Math.PI / 2;
            exhaust.position.set(-0.65, 0.32, -2.1);
            this.carRoot.add(exhaust);
        }

        buildBodyPanels() {
            // Front lower body (Red)
            const frontLowerGeo = new THREE.BoxGeometry(1.82, 0.48, 1.9);
            const frontLower = new THREE.Mesh(frontLowerGeo, this.materials.frontPaint);
            frontLower.position.set(0, 0.72, 1.15);
            frontLower.castShadow = true;
            frontLower.receiveShadow = true;
            this.carRoot.add(frontLower);

            // Front cowl
            const cowlGeo = new THREE.BoxGeometry(1.78, 0.16, 0.45);
            const cowl = new THREE.Mesh(cowlGeo, this.materials.frontPaint);
            cowl.position.set(0, 1.02, 0.35);
            this.carRoot.add(cowl);

            // Rear lower body (White)
            const rearLowerGeo = new THREE.BoxGeometry(1.82, 0.48, 2.15);
            const rearLower = new THREE.Mesh(rearLowerGeo, this.materials.rearPaint);
            rearLower.position.set(0, 0.72, -0.92);
            rearLower.castShadow = true;
            rearLower.receiveShadow = true;
            this.carRoot.add(rearLower);

            // Rear cabin upper (White)
            const rearUpperGeo = new THREE.BoxGeometry(1.72, 0.62, 2.1);
            const rearUpper = new THREE.Mesh(rearUpperGeo, this.materials.rearPaint);
            rearUpper.position.set(0, 1.25, -0.92);
            rearUpper.castShadow = true;
            this.carRoot.add(rearUpper);

            // Roof panel (White)
            const roofGeo = new THREE.BoxGeometry(1.68, 0.1, 2.65);
            const roof = new THREE.Mesh(roofGeo, this.materials.rearPaint);
            roof.position.set(0, 1.62, -0.5);
            roof.castShadow = true;
            this.carRoot.add(roof);

            // Roof ribs
            for (let i = -3; i <= 3; i++) {
                if (i === 0) continue;
                const ribGeo = new THREE.BoxGeometry(0.03, 0.02, 2.4);
                const rib = new THREE.Mesh(ribGeo, this.materials.rearPaint);
                rib.position.set(i * 0.22, 1.68, -0.5);
                this.carRoot.add(rib);
            }

            // Lower silver cladding
            [-1, 1].forEach(side => {
                const frontCladGeo = new THREE.BoxGeometry(0.04, 0.28, 1.88);
                const frontClad = new THREE.Mesh(frontCladGeo, this.materials.cladding);
                frontClad.position.set(side * 0.92, 0.52, 1.15);
                this.carRoot.add(frontClad);

                const rearCladGeo = new THREE.BoxGeometry(0.04, 0.28, 2.14);
                const rearClad = new THREE.Mesh(rearCladGeo, this.materials.cladding);
                rearClad.position.set(side * 0.92, 0.52, -0.92);
                this.carRoot.add(rearClad);
            });

            this.buildFenderArches();
        }

        buildFenderArches() {
            const wheelZPositions = [1.38, -1.35];
            [-1, 1].forEach(side => {
                wheelZPositions.forEach(zPos => {
                    const archGeo = new THREE.TorusGeometry(0.55, 0.08, 8, 16, Math.PI);
                    const arch = new THREE.Mesh(archGeo, this.materials.cladding);
                    arch.rotation.y = side > 0 ? Math.PI / 2 : -Math.PI / 2;
                    arch.position.set(side * 0.93, 0.58, zPos);
                    arch.scale.set(1, 0.72, 1);
                    arch.castShadow = true;
                    this.carRoot.add(arch);
                });
            });
        }

        buildDoorsAndHood() {
            // Driver Door (Left)
            const leftDoorPivot = new THREE.Group();
            leftDoorPivot.position.set(-0.92, 0.72, 0.72);

            const doorShellGeo = new THREE.BoxGeometry(0.06, 0.46, 0.95);
            const doorShell = new THREE.Mesh(doorShellGeo, this.materials.frontPaint);
            doorShell.position.set(0, 0, -0.47);
            doorShell.castShadow = true;
            leftDoorPivot.add(doorShell);

            const doorFrameGeo = new THREE.BoxGeometry(0.04, 0.42, 0.92);
            const doorGlass = new THREE.Mesh(doorFrameGeo, this.materials.glass);
            doorGlass.position.set(0, 0.45, -0.47);
            leftDoorPivot.add(doorGlass);

            const mirrorMount = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.04, 0.04), this.materials.satinBlack);
            mirrorMount.position.set(-0.06, 0.28, -0.1);
            const mirrorBody = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.14, 0.22), this.materials.satinBlack);
            mirrorBody.position.set(-0.16, 0.3, -0.1);
            const mirrorGlass = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.12, 0.18), this.materials.chrome);
            mirrorGlass.position.set(-0.12, 0.3, -0.1);
            leftDoorPivot.add(mirrorMount);
            leftDoorPivot.add(mirrorBody);
            leftDoorPivot.add(mirrorGlass);

            const handle = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.04, 0.14), this.materials.chrome);
            handle.position.set(-0.04, 0.15, -0.78);
            leftDoorPivot.add(handle);

            this.carRoot.add(leftDoorPivot);
            this.doors.frontLeft.mesh = leftDoorPivot;

            // Passenger Door (Right)
            const rightDoorPivot = new THREE.Group();
            rightDoorPivot.position.set(0.92, 0.72, 0.72);

            const rightDoorShell = new THREE.Mesh(doorShellGeo, this.materials.frontPaint);
            rightDoorShell.position.set(0, 0, -0.47);
            rightDoorShell.castShadow = true;
            rightDoorPivot.add(rightDoorShell);

            const rightDoorGlass = new THREE.Mesh(doorFrameGeo, this.materials.glass);
            rightDoorGlass.position.set(0, 0.45, -0.47);
            rightDoorPivot.add(rightDoorGlass);

            const rMirrorMount = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.04, 0.04), this.materials.satinBlack);
            rMirrorMount.position.set(0.06, 0.28, -0.1);
            const rMirrorBody = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.14, 0.22), this.materials.satinBlack);
            rMirrorBody.position.set(0.16, 0.3, -0.1);
            const rMirrorGlass = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.12, 0.18), this.materials.chrome);
            rMirrorGlass.position.set(0.12, 0.3, -0.1);
            rightDoorPivot.add(rMirrorMount);
            rightDoorPivot.add(rMirrorBody);
            rightDoorPivot.add(rMirrorGlass);

            const rHandle = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.04, 0.14), this.materials.chrome);
            rHandle.position.set(0.04, 0.15, -0.78);
            rightDoorPivot.add(rHandle);

            this.carRoot.add(rightDoorPivot);
            this.doors.frontRight.mesh = rightDoorPivot;

            // Tailgate (Rear Door)
            const tailgatePivot = new THREE.Group();
            tailgatePivot.position.set(0.85, 0.95, -2.0);

            const tailgateLowerGeo = new THREE.BoxGeometry(1.68, 0.58, 0.08);
            const tailgateLower = new THREE.Mesh(tailgateLowerGeo, this.materials.rearPaint);
            tailgateLower.position.set(-0.84, -0.22, 0);
            tailgateLower.castShadow = true;
            tailgatePivot.add(tailgateLower);

            const tailgateGlassGeo = new THREE.BoxGeometry(1.55, 0.52, 0.04);
            const tailgateGlass = new THREE.Mesh(tailgateGlassGeo, this.materials.glass);
            tailgateGlass.position.set(-0.84, 0.35, 0);
            tailgatePivot.add(tailgateGlass);

            const plateRecessGeo = new THREE.BoxGeometry(0.55, 0.2, 0.04);
            const plateRecess = new THREE.Mesh(plateRecessGeo, this.materials.satinBlack);
            plateRecess.position.set(-1.18, -0.22, -0.04);
            tailgatePivot.add(plateRecess);

            const plateCanvas = document.createElement('canvas');
            plateCanvas.width = 256; plateCanvas.height = 64;
            const pctx = plateCanvas.getContext('2d');
            pctx.fillStyle = '#f5c518'; pctx.fillRect(0, 0, 256, 64);
            pctx.fillStyle = '#111'; pctx.font = 'bold 36px monospace'; pctx.textAlign = 'center'; pctx.textBaseline = 'middle';
            pctx.fillText('PAJERO 4X4', 128, 32);
            const plateTex = new THREE.CanvasTexture(plateCanvas);
            const plate = new THREE.Mesh(new THREE.PlaneGeometry(0.48, 0.14), new THREE.MeshBasicMaterial({ map: plateTex }));
            plate.rotation.y = Math.PI;
            plate.position.set(-1.18, -0.22, -0.065);
            tailgatePivot.add(plate);

            this.carRoot.add(tailgatePivot);
            this.doors.tailgate.mesh = tailgatePivot;

            // Engine Hood (Bonnet)
            const hoodPivot = new THREE.Group();
            hoodPivot.position.set(0, 1.02, 0.65);

            const hoodPanelGeo = new THREE.BoxGeometry(1.76, 0.08, 1.35);
            const hoodPanel = new THREE.Mesh(hoodPanelGeo, this.materials.frontPaint);
            hoodPanel.position.set(0, 0, 0.67);
            hoodPanel.castShadow = true;
            hoodPivot.add(hoodPanel);

            const scoopGeo = new THREE.BoxGeometry(0.42, 0.06, 0.45);
            const scoop = new THREE.Mesh(scoopGeo, this.materials.frontPaint);
            scoop.position.set(0.18, 0.06, 0.65);
            const scoopIntake = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.03, 0.04), this.materials.satinBlack);
            scoopIntake.position.set(0.18, 0.05, 0.88);
            hoodPivot.add(scoop);
            hoodPivot.add(scoopIntake);

            this.carRoot.add(hoodPivot);
            this.doors.hood.mesh = hoodPivot;
        }

        buildWindows() {
            const windshieldGeo = new THREE.PlaneGeometry(1.68, 0.78);
            const windshield = new THREE.Mesh(windshieldGeo, this.materials.glass);
            windshield.position.set(0, 1.32, 0.52);
            windshield.rotation.x = -0.72;
            this.carRoot.add(windshield);

            [-1, 1].forEach(side => {
                const aPillarGeo = new THREE.BoxGeometry(0.08, 0.82, 0.08);
                const aPillar = new THREE.Mesh(aPillarGeo, this.materials.frontPaint);
                aPillar.position.set(side * 0.86, 1.32, 0.52);
                aPillar.rotation.x = -0.72;
                this.carRoot.add(aPillar);
            });

            [-1, 1].forEach(side => {
                const sideGlassGeo = new THREE.PlaneGeometry(1.4, 0.52);
                const sideGlass = new THREE.Mesh(sideGlassGeo, this.materials.glass);
                sideGlass.position.set(side * 0.87, 1.25, -1.15);
                sideGlass.rotation.y = side > 0 ? Math.PI / 2 : -Math.PI / 2;
                this.carRoot.add(sideGlass);

                const dPillarGeo = new THREE.BoxGeometry(0.14, 0.62, 0.16);
                const dPillar = new THREE.Mesh(dPillarGeo, this.materials.rearPaint);
                dPillar.position.set(side * 0.86, 1.25, -1.95);
                this.carRoot.add(dPillar);
            });
        }

        buildInterior() {
            const cabinGroup = new THREE.Group();

            const dashGeo = new THREE.BoxGeometry(1.6, 0.28, 0.45);
            const dash = new THREE.Mesh(dashGeo, this.materials.interior);
            dash.position.set(0, 0.95, 0.42);
            cabinGroup.add(dash);

            const altimeterPodGeo = new THREE.BoxGeometry(0.32, 0.12, 0.16);
            const altimeterPod = new THREE.Mesh(altimeterPodGeo, this.materials.satinBlack);
            altimeterPod.position.set(0, 1.13, 0.4);
            cabinGroup.add(altimeterPod);

            const wheelRingGeo = new THREE.TorusGeometry(0.16, 0.025, 8, 24);
            const wheelCenter = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.03, 16), this.materials.satinBlack);
            wheelCenter.rotation.x = Math.PI / 2;
            const steeringWheel = new THREE.Group();
            const ringMesh = new THREE.Mesh(wheelRingGeo, this.materials.satinBlack);
            steeringWheel.add(ringMesh);
            steeringWheel.add(wheelCenter);
            steeringWheel.position.set(0.42, 1.08, 0.22);
            steeringWheel.rotation.x = -0.55;
            cabinGroup.add(steeringWheel);

            [-0.42, 0.42].forEach(x => {
                const seatBase = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.2, 0.55), this.materials.interior);
                seatBase.position.set(x, 0.65, -0.05);

                const seatBack = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.58, 0.14), this.materials.interior);
                seatBack.position.set(x, 1.0, -0.32);
                seatBack.rotation.x = -0.15;

                const headrest = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.16, 0.12), this.materials.interior);
                headrest.position.set(x, 1.34, -0.38);

                cabinGroup.add(seatBase);
                cabinGroup.add(seatBack);
                cabinGroup.add(headrest);
            });

            const rearBench = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.24, 0.58), this.materials.interior);
            rearBench.position.set(0, 0.65, -1.05);
            const rearBack = new THREE.Mesh(new THREE.BoxGeometry(1.48, 0.56, 0.14), this.materials.interior);
            rearBack.position.set(0, 1.02, -1.35);
            rearBack.rotation.x = -0.15;
            cabinGroup.add(rearBench);
            cabinGroup.add(rearBack);

            this.carRoot.add(cabinGroup);
        }

        buildWheels() {
            this.wheelMeshes = [];
            const wheelPositions = [
                { x: -0.96, z: 1.38, isFront: true, side: -1 },
                { x: 0.96, z: 1.38, isFront: true, side: 1 },
                { x: -0.96, z: -1.35, isFront: false, side: -1 },
                { x: 0.96, z: -1.35, isFront: false, side: 1 }
            ];

            wheelPositions.forEach((pos) => {
                const wheelAssembly = new THREE.Group();
                wheelAssembly.position.set(pos.x, 0.44, pos.z);

                const tireGeo = new THREE.CylinderGeometry(0.44, 0.44, 0.32, 28);
                const tire = new THREE.Mesh(tireGeo, this.materials.tireRubber);
                tire.rotation.z = Math.PI / 2;
                tire.castShadow = true;
                wheelAssembly.add(tire);

                for (let a = 0; a < 18; a++) {
                    const angle = (a / 18) * Math.PI * 2;
                    const treadGeo = new THREE.BoxGeometry(0.3, 0.035, 0.06);
                    const tread = new THREE.Mesh(treadGeo, this.materials.tireRubber);
                    tread.position.set(0, Math.cos(angle) * 0.44, Math.sin(angle) * 0.44);
                    tread.rotation.x = -angle;
                    wheelAssembly.add(tread);
                }

                const rimGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.33, 20);
                const rim = new THREE.Mesh(rimGeo, this.materials.wheelRim);
                rim.rotation.z = Math.PI / 2;
                wheelAssembly.add(rim);

                const hubGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.35, 16);
                const hub = new THREE.Mesh(hubGeo, this.materials.chrome);
                hub.rotation.z = Math.PI / 2;
                wheelAssembly.add(hub);

                const discGeo = new THREE.CylinderGeometry(0.24, 0.24, 0.03, 20);
                const disc = new THREE.Mesh(discGeo, this.materials.brakeDisc);
                disc.rotation.z = Math.PI / 2;
                disc.position.x = pos.side * -0.08;
                wheelAssembly.add(disc);

                const caliperGeo = new THREE.BoxGeometry(0.08, 0.14, 0.1);
                const caliper = new THREE.Mesh(caliperGeo, this.materials.brakeCaliper);
                caliper.position.set(pos.side * -0.08, 0.14, 0);
                wheelAssembly.add(caliper);

                this.carRoot.add(wheelAssembly);
                this.wheelMeshes.push({ group: wheelAssembly, isFront: pos.isFront, side: pos.side });
            });
        }

        buildRoofRack() {
            const rackGroup = new THREE.Group();
            rackGroup.position.set(0, 1.72, -0.5);

            [-0.72, 0.72].forEach(x => {
                const railGeo = new THREE.CylinderGeometry(0.02, 0.02, 2.5, 12);
                const rail = new THREE.Mesh(railGeo, this.materials.satinBlack);
                rail.rotation.x = Math.PI / 2;
                rail.position.set(x, 0.12, 0);
                rail.castShadow = true;
                rackGroup.add(rail);

                [-1.0, -0.4, 0.4, 1.0].forEach(z => {
                    const legGeo = new THREE.BoxGeometry(0.04, 0.14, 0.04);
                    const leg = new THREE.Mesh(legGeo, this.materials.satinBlack);
                    leg.position.set(x, 0.05, z);
                    rackGroup.add(leg);
                });
            });

            for (let z = -1.1; z <= 1.1; z += 0.45) {
                const crossGeo = new THREE.CylinderGeometry(0.016, 0.016, 1.44, 10);
                const cross = new THREE.Mesh(crossGeo, this.materials.satinBlack);
                cross.rotation.z = Math.PI / 2;
                cross.position.set(0, 0.12, z);
                cross.castShadow = true;
                rackGroup.add(cross);
            }

            const deflectorGeo = new THREE.BoxGeometry(1.36, 0.12, 0.03);
            const deflector = new THREE.Mesh(deflectorGeo, this.materials.satinBlack);
            deflector.position.set(0, 0.12, 1.25);
            deflector.rotation.x = 0.35;
            rackGroup.add(deflector);

            this.carRoot.add(rackGroup);
        }

        buildSpareWheel() {
            const spareGroup = new THREE.Group();
            spareGroup.position.set(-0.55, -0.15, -0.28);

            const bracketGeo = new THREE.BoxGeometry(0.25, 0.25, 0.16);
            const bracket = new THREE.Mesh(bracketGeo, this.materials.satinBlack);
            bracket.position.set(0, 0, 0.1);
            spareGroup.add(bracket);

            const spareTireGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.28, 24);
            const spareTire = new THREE.Mesh(spareTireGeo, this.materials.tireRubber);
            spareTire.rotation.x = Math.PI / 2;
            spareTire.castShadow = true;
            spareGroup.add(spareTire);

            const spareRimGeo = new THREE.CylinderGeometry(0.26, 0.26, 0.29, 20);
            const spareRim = new THREE.Mesh(spareRimGeo, this.materials.wheelRim);
            spareRim.rotation.x = Math.PI / 2;
            spareGroup.add(spareRim);

            const spareHub = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.31, 16), this.materials.chrome);
            spareHub.rotation.x = Math.PI / 2;
            spareGroup.add(spareHub);

            if (this.doors.tailgate.mesh) {
                this.doors.tailgate.mesh.add(spareGroup);
            }
        }

        buildBumpersAndGuards() {
            const frontBumperGroup = new THREE.Group();
            frontBumperGroup.position.set(0, 0.48, 2.18);

            const fBumperGeo = new THREE.BoxGeometry(1.88, 0.24, 0.24);
            const fBumper = new THREE.Mesh(fBumperGeo, this.materials.cladding);
            fBumper.castShadow = true;
            frontBumperGroup.add(fBumper);

            const skidGeo = new THREE.BoxGeometry(1.1, 0.18, 0.28);
            const skid = new THREE.Mesh(skidGeo, this.materials.chrome);
            skid.position.set(0, -0.12, -0.04);
            skid.rotation.x = 0.35;
            frontBumperGroup.add(skid);

            const bullBarGeo = new THREE.CylinderGeometry(0.035, 0.035, 1.25, 12);
            const bullBar = new THREE.Mesh(bullBarGeo, this.materials.satinBlack);
            bullBar.rotation.z = Math.PI / 2;
            bullBar.position.set(0, 0.22, 0.15);
            bullBar.castShadow = true;
            frontBumperGroup.add(bullBar);

            [-0.55, 0.55].forEach(x => {
                const fogLight = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.05, 16), this.materials.indicator);
                fogLight.rotation.x = Math.PI / 2;
                fogLight.position.set(x, 0.02, 0.12);
                frontBumperGroup.add(fogLight);
            });

            this.carRoot.add(frontBumperGroup);

            const rearBumperGeo = new THREE.BoxGeometry(1.86, 0.24, 0.22);
            const rearBumper = new THREE.Mesh(rearBumperGeo, this.materials.cladding);
            rearBumper.position.set(0, 0.48, -2.08);
            rearBumper.castShadow = true;
            this.carRoot.add(rearBumper);

            [-0.84, 0.84].forEach(side => {
                const tailCluster = new THREE.Group();
                tailCluster.position.set(side, 0.88, -2.02);

                const stopLight = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.18, 0.03), this.materials.taillightRed);
                stopLight.position.set(0, 0.1, 0);
                const turnLight = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 0.03), this.materials.indicator);
                turnLight.position.set(0, -0.08, 0);

                tailCluster.add(stopLight);
                tailCluster.add(turnLight);
                this.carRoot.add(tailCluster);
            });

            [-0.92, 0.92].forEach(side => {
                const flapGeo = new THREE.BoxGeometry(0.18, 0.32, 0.02);
                const flap = new THREE.Mesh(flapGeo, this.materials.satinBlack);
                flap.position.set(side, 0.32, -1.82);
                this.carRoot.add(flap);
            });
        }

        buildHeadlightsAndGrille() {
            const frontFascia = new THREE.Group();
            frontFascia.position.set(0, 0.86, 2.12);

            const grilleMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.32), new THREE.MeshStandardMaterial({ map: this.grilleTexture }));
            grilleMesh.position.set(0, 0, 0.01);
            frontFascia.add(grilleMesh);

            const emblemGroup = new THREE.Group();
            emblemGroup.position.set(0, 0.02, 0.025);
            for (let i = 0; i < 3; i++) {
                const diamondGeo = new THREE.ConeGeometry(0.04, 0.08, 4);
                const diamond = new THREE.Mesh(diamondGeo, this.materials.chrome);
                const angle = (i * 120) * (Math.PI / 180);
                diamond.position.set(Math.sin(angle) * 0.035, Math.cos(angle) * 0.035, 0);
                diamond.rotation.z = -angle;
                emblemGroup.add(diamond);
            }
            frontFascia.add(emblemGroup);

            this.headlightEmitters = [];
            [-0.64, 0.64].forEach(side => {
                const bezelGeo = new THREE.BoxGeometry(0.26, 0.24, 0.06);
                const bezel = new THREE.Mesh(bezelGeo, this.materials.satinBlack);
                bezel.position.set(side, 0, 0);
                frontFascia.add(bezel);

                const reflectorGeo = new THREE.CylinderGeometry(0.09, 0.09, 0.04, 16);
                const reflector = new THREE.Mesh(reflectorGeo, this.materials.headlightReflector);
                reflector.rotation.x = Math.PI / 2;
                reflector.position.set(side, 0, 0.02);
                frontFascia.add(reflector);
                this.headlightEmitters.push(reflector);

                const lensGeo = new THREE.BoxGeometry(0.24, 0.22, 0.02);
                const lens = new THREE.Mesh(lensGeo, this.materials.headlightGlass);
                lens.position.set(side, 0, 0.04);
                frontFascia.add(lens);

                const indicGeo = new THREE.BoxGeometry(0.1, 0.22, 0.08);
                const indic = new THREE.Mesh(indicGeo, this.materials.indicator);
                indic.position.set(side + (side > 0 ? 0.17 : -0.17), 0, -0.02);
                frontFascia.add(indic);
            });

            this.headlightSpotLeft = new THREE.SpotLight(0xf2f7ff, 0, 20, Math.PI / 6, 0.4, 1);
            this.headlightSpotLeft.position.set(-0.64, 0.86, 2.15);
            this.headlightSpotLeft.target.position.set(-0.64, 0.2, 10);
            this.scene.add(this.headlightSpotLeft);
            this.scene.add(this.headlightSpotLeft.target);

            this.headlightSpotRight = new THREE.SpotLight(0xf2f7ff, 0, 20, Math.PI / 6, 0.4, 1);
            this.headlightSpotRight.position.set(0.64, 0.86, 2.15);
            this.headlightSpotRight.target.position.set(0.64, 0.2, 10);
            this.scene.add(this.headlightSpotRight);
            this.scene.add(this.headlightSpotRight.target);

            this.carRoot.add(frontFascia);
        }

        buildSideDecals() {
            [-1, 1].forEach(side => {
                const decalGeo = new THREE.PlaneGeometry(1.85, 0.45);
                const decalMesh = new THREE.Mesh(decalGeo, this.materials.decalMat);
                decalMesh.position.set(side * 0.925, 0.65, 0.5);
                decalMesh.rotation.y = side > 0 ? Math.PI / 2 : -Math.PI / 2;
                if (side < 0) {
                    decalMesh.scale.x = -1;
                }
                this.carRoot.add(decalMesh);
            });
        }

        buildEngineBay() {
            const bayGroup = new THREE.Group();
            bayGroup.position.set(0, 0.82, 1.35);

            const blockGeo = new THREE.BoxGeometry(0.72, 0.35, 0.65);
            const block = new THREE.Mesh(blockGeo, new THREE.MeshStandardMaterial({ color: 0x2b3035, metalness: 0.8, roughness: 0.3 }));
            bayGroup.add(block);

            const valveCoverGeo = new THREE.BoxGeometry(0.68, 0.12, 0.58);
            const valveCover = new THREE.Mesh(valveCoverGeo, new THREE.MeshStandardMaterial({ color: 0xb81820, metalness: 0.5, roughness: 0.4 }));
            valveCover.position.y = 0.22;
            bayGroup.add(valveCover);

            const intercoolerGeo = new THREE.BoxGeometry(0.38, 0.08, 0.35);
            const intercooler = new THREE.Mesh(intercoolerGeo, this.materials.chrome);
            intercooler.position.set(0.15, 0.3, 0);
            bayGroup.add(intercooler);

            const batteryGeo = new THREE.BoxGeometry(0.25, 0.22, 0.22);
            const battery = new THREE.Mesh(batteryGeo, new THREE.MeshStandardMaterial({ color: 0x1a1a1a }));
            battery.position.set(-0.58, 0.12, 0.22);
            const battTop = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.04, 0.2), new THREE.MeshStandardMaterial({ color: 0xf5c518 }));
            battTop.position.set(-0.58, 0.24, 0.22);
            bayGroup.add(battery);
            bayGroup.add(battTop);

            const airBoxGeo = new THREE.BoxGeometry(0.28, 0.22, 0.28);
            const airBox = new THREE.Mesh(airBoxGeo, this.materials.satinBlack);
            airBox.position.set(0.58, 0.12, 0.2);
            bayGroup.add(airBox);

            this.carRoot.add(bayGroup);
        }

        setupFloor() {
            const shadowGeo = new THREE.PlaneGeometry(3.6, 6.2);
            const shadowCanvas = document.createElement('canvas');
            shadowCanvas.width = 512; shadowCanvas.height = 512;
            const sctx = shadowCanvas.getContext('2d');
            const grad = sctx.createRadialGradient(256, 256, 40, 256, 256, 240);
            grad.addColorStop(0, 'rgba(0,0,0,0.65)');
            grad.addColorStop(0.5, 'rgba(0,0,0,0.35)');
            grad.addColorStop(1, 'rgba(0,0,0,0)');
            sctx.fillStyle = grad;
            sctx.fillRect(0, 0, 512, 512);

            const shadowTexture = new THREE.CanvasTexture(shadowCanvas);
            const shadowPlane = new THREE.Mesh(shadowGeo, new THREE.MeshBasicMaterial({
                map: shadowTexture,
                transparent: true,
                opacity: 0.85,
                depthWrite: false
            }));
            shadowPlane.rotation.x = -Math.PI / 2;
            shadowPlane.position.y = 0.01;
            this.scene.add(shadowPlane);
        }

        setupOrbitAndTilt() {
            this.cameraRadius = 6.2;
            this.cameraTheta = Math.PI / 2;
            this.cameraPhi = Math.PI / 2.3;
            this.targetRadius = 6.2;
            this.targetTheta = Math.PI / 2;
            this.targetPhi = Math.PI / 2.3;

            this.isDragging = false;
            this.previousMousePosition = { x: 0, y: 0 };
            this.mouseTilt = { x: 0, y: 0 };

            const canvas = this.renderer.domElement;

            canvas.addEventListener('pointerdown', (e) => {
                this.isDragging = true;
                this.previousMousePosition = { x: e.clientX, y: e.clientY };
                canvas.style.cursor = 'grabbing';
            });

            window.addEventListener('pointermove', (e) => {
                if (this.isDragging) {
                    const deltaX = e.clientX - this.previousMousePosition.x;
                    const deltaY = e.clientY - this.previousMousePosition.y;

                    this.targetTheta -= deltaX * 0.0075;
                    this.targetPhi = Math.max(0.2, Math.min(Math.PI / 2 - 0.05, this.targetPhi - deltaY * 0.006));

                    this.previousMousePosition = { x: e.clientX, y: e.clientY };
                } else {
                    const rect = canvas.getBoundingClientRect();
                    if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
                        const nx = (e.clientX - rect.left) / rect.width - 0.5;
                        const ny = (e.clientY - rect.top) / rect.height - 0.5;
                        this.mouseTilt.x = nx * 0.25;
                        this.mouseTilt.y = ny * 0.15;
                    }
                }
            });

            window.addEventListener('pointerup', () => {
                this.isDragging = false;
                canvas.style.cursor = 'grab';
            });

            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                this.targetRadius = Math.max(3.8, Math.min(9.5, this.targetRadius + e.deltaY * 0.005));
            }, { passive: false });

            let touchDist = 0;
            canvas.addEventListener('touchstart', (e) => {
                if (e.touches.length === 2) {
                    touchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
                }
            });
            canvas.addEventListener('touchmove', (e) => {
                if (e.touches.length === 2) {
                    const newDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
                    const delta = touchDist - newDist;
                    this.targetRadius = Math.max(3.8, Math.min(9.5, this.targetRadius + delta * 0.01));
                    touchDist = newDist;
                }
            });

            canvas.style.cursor = 'grab';
        }

        setCameraPreset(preset, animated = true) {
            switch (preset) {
                case 'profile':
                    this.targetTheta = -Math.PI / 2;
                    this.targetPhi = Math.PI / 2.15;
                    this.targetRadius = 5.8;
                    this.cameraTarget.set(0, 0.75, 0);
                    break;
                case 'hero':
                case 'threeQuarter':
                    this.targetTheta = -Math.PI * 0.25;
                    this.targetPhi = Math.PI / 2.4;
                    this.targetRadius = 6.2;
                    this.cameraTarget.set(0, 0.75, 0);
                    break;
                case 'front':
                    this.targetTheta = 0;
                    this.targetPhi = Math.PI / 2.25;
                    this.targetRadius = 5.5;
                    this.cameraTarget.set(0, 0.72, 0.8);
                    break;
                case 'rear':
                    this.targetTheta = Math.PI;
                    this.targetPhi = Math.PI / 2.2;
                    this.targetRadius = 5.6;
                    this.cameraTarget.set(0, 0.75, -0.8);
                    break;
                case 'engine':
                    this.targetTheta = -0.35;
                    this.targetPhi = Math.PI / 2.8;
                    this.targetRadius = 4.2;
                    this.cameraTarget.set(0, 0.95, 1.2);
                    this.toggleDoor('hood', true);
                    break;
                case 'wheels':
                    this.targetTheta = -Math.PI * 0.35;
                    this.targetPhi = Math.PI / 2.1;
                    this.targetRadius = 4.4;
                    this.cameraTarget.set(0.9, 0.5, 1.3);
                    break;
                default:
                    this.targetTheta = -Math.PI * 0.25;
                    this.targetPhi = Math.PI / 2.3;
                    this.targetRadius = 6.2;
            }

            if (!animated) {
                this.cameraTheta = this.targetTheta;
                this.cameraPhi = this.targetPhi;
                this.cameraRadius = this.targetRadius;
            }
        }

        toggleDoor(doorName, forceState = null) {
            const door = this.doors[doorName];
            if (!door) return;

            const shouldOpen = forceState !== null ? forceState : (door.target === 0);
            door.target = shouldOpen ? door.max : 0;

            const btn = this.container.querySelector(`[data-door-btn="${doorName}"]`);
            if (btn) {
                btn.classList.toggle('is-active', shouldOpen);
                btn.setAttribute('aria-pressed', String(shouldOpen));
            }
        }

        toggleAllDoors() {
            const anyOpen = Object.values(this.doors).some(d => d.target !== 0);
            const targetState = !anyOpen;

            Object.keys(this.doors).forEach(key => {
                this.toggleDoor(key, targetState);
            });

            const allBtn = this.container.querySelector('[data-door-btn="all"]');
            if (allBtn) {
                allBtn.classList.toggle('is-active', targetState);
            }
        }

        toggleHeadlights(forceState = null) {
            this.headlightsOn = forceState !== null ? forceState : !this.headlightsOn;

            const intensity = this.headlightsOn ? 2.5 : 0;
            if (this.headlightSpotLeft) this.headlightSpotLeft.intensity = intensity;
            if (this.headlightSpotRight) this.headlightSpotRight.intensity = intensity;

            this.headlightEmitters.forEach(emitter => {
                emitter.material.emissive.setHex(this.headlightsOn ? 0xf0f6ff : 0x000000);
                emitter.material.emissiveIntensity = this.headlightsOn ? 2.0 : 0;
            });

            const btn = this.container.querySelector('[data-car-light-btn]');
            if (btn) {
                btn.classList.toggle('is-active', this.headlightsOn);
                btn.setAttribute('aria-pressed', String(this.headlightsOn));
            }
        }

        setLivery(liveryKey) {
            const preset = LIVERY_PRESETS[liveryKey];
            if (!preset) return;
            this.currentLiveryKey = liveryKey;

            this.materials.frontPaint.color.setHex(preset.front);
            this.materials.rearPaint.color.setHex(preset.rear);
            this.materials.cladding.color.setHex(preset.cladding);

            this.materials.decalMat.visible = preset.showDecal;

            this.container.querySelectorAll('[data-pajero-livery]').forEach(btn => {
                btn.classList.toggle('is-selected', btn.dataset.pajeroLivery === liveryKey);
            });
        }

        toggleSuspension() {
            this.suspensionLifted = !this.suspensionLifted;
            const targetY = this.suspensionLifted ? 0.16 : 0.05;

            this.carRoot.position.y = targetY;

            const btn = this.container.querySelector('[data-car-lift-btn]');
            if (btn) {
                btn.classList.toggle('is-active', this.suspensionLifted);
                btn.setAttribute('aria-pressed', String(this.suspensionLifted));
                btn.textContent = this.suspensionLifted ? 'Lift: Off-Road (+6cm)' : 'Lift: Street Stance';
            }
        }

        toggleTurntable() {
            this.autoSpin = !this.autoSpin;
            const btn = this.container.querySelector('[data-car-spin-btn]');
            if (btn) {
                btn.classList.toggle('is-active', this.autoSpin);
                btn.setAttribute('aria-pressed', String(this.autoSpin));
            }
        }

        animate() {
            if (!this.animating) return;
            requestAnimationFrame(this.animate);

            const delta = this.clock.getDelta();

            if (this.autoSpin && !this.isDragging) {
                this.targetTheta += delta * 0.35;
            }

            this.cameraTheta += (this.targetTheta - this.cameraTheta) * 0.08;
            this.cameraPhi += (this.targetPhi - this.cameraPhi) * 0.08;
            this.cameraRadius += (this.targetRadius - this.cameraRadius) * 0.08;

            const effectiveTheta = this.cameraTheta + this.mouseTilt.x;
            const effectivePhi = this.cameraPhi + this.mouseTilt.y;

            const x = this.cameraTarget.x + this.cameraRadius * Math.sin(effectivePhi) * Math.sin(effectiveTheta);
            const y = this.cameraTarget.y + this.cameraRadius * Math.cos(effectivePhi);
            const z = this.cameraTarget.z + this.cameraRadius * Math.sin(effectivePhi) * Math.cos(effectiveTheta);

            this.camera.position.set(x, y, z);
            this.camera.lookAt(this.cameraTarget);

            if (this.doors.frontLeft.mesh) {
                this.doors.frontLeft.angle += (this.doors.frontLeft.target - this.doors.frontLeft.angle) * 0.12;
                this.doors.frontLeft.mesh.rotation.y = this.doors.frontLeft.angle;
            }
            if (this.doors.frontRight.mesh) {
                this.doors.frontRight.angle += (this.doors.frontRight.target - this.doors.frontRight.angle) * 0.12;
                this.doors.frontRight.mesh.rotation.y = this.doors.frontRight.angle;
            }
            if (this.doors.tailgate.mesh) {
                this.doors.tailgate.angle += (this.doors.tailgate.target - this.doors.tailgate.angle) * 0.12;
                this.doors.tailgate.mesh.rotation.y = this.doors.tailgate.angle;
            }
            if (this.doors.hood.mesh) {
                this.doors.hood.angle += (this.doors.hood.target - this.doors.hood.angle) * 0.12;
                this.doors.hood.mesh.rotation.x = this.doors.hood.angle;
            }

            if (this.wheelMeshes) {
                const steerAngle = Math.sin(this.cameraTheta) * 0.22;
                this.wheelMeshes.forEach(w => {
                    if (w.isFront) {
                        w.group.rotation.y = steerAngle;
                    }
                });
            }

            this.renderer.render(this.scene, this.camera);
        }

        onResize() {
            if (!this.container) return;
            this.width = this.container.clientWidth;
            this.height = this.container.clientHeight;
            if (this.width === 0 || this.height === 0) return;

            this.camera.aspect = this.width / this.height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(this.width, this.height);
        }

        buildShowroomUI() {
            const overlay = document.createElement('div');
            overlay.className = 'pajero-studio-overlay';
            overlay.innerHTML = `
                <div class="pajero-badge-strip">
                    <span class="pajero-model-tag">MITSUBISHI PAJERO II · 4WD V6 3000</span>
                    <span class="pajero-hint-drag">Drag to rotate 360° · Scroll to zoom</span>
                </div>

                <div class="pajero-door-controls" role="group" aria-label="Vehicle doors and panels">
                    <button type="button" class="pajero-ctrl-btn" data-door-btn="frontLeft" title="Toggle driver door">
                        <span class="ctrl-icon">🚪</span> Driver Door
                    </button>
                    <button type="button" class="pajero-ctrl-btn" data-door-btn="frontRight" title="Toggle passenger door">
                        <span class="ctrl-icon">🚪</span> Passenger Door
                    </button>
                    <button type="button" class="pajero-ctrl-btn" data-door-btn="tailgate" title="Toggle rear tailgate with spare tire">
                        <span class="ctrl-icon">🧳</span> Tailgate & Tire
                    </button>
                    <button type="button" class="pajero-ctrl-btn" data-door-btn="hood" title="Inspect engine bay">
                        <span class="ctrl-icon">⚙️</span> Engine Hood
                    </button>
                    <button type="button" class="pajero-ctrl-btn is-master" data-door-btn="all" title="Open or close all doors">
                        <span class="ctrl-icon">✨</span> Open All
                    </button>
                </div>

                <div class="pajero-camera-dock" role="group" aria-label="Camera angles">
                    <button type="button" class="pajero-cam-btn" data-pajero-cam="profile" title="Side view matching the reference photo">
                        📷 Side Reference
                    </button>
                    <button type="button" class="pajero-cam-btn is-active" data-pajero-cam="hero" title="Front 3/4 Showroom perspective">
                        💎 3/4 Angle
                    </button>
                    <button type="button" class="pajero-cam-btn" data-pajero-cam="front" title="Front fascia & Bull bar">
                        🛡️ Front
                    </button>
                    <button type="button" class="pajero-cam-btn" data-pajero-cam="rear" title="Rear spare tire & roof rack">
                        🛞 Rear & Rack
                    </button>
                </div>

                <div class="pajero-settings-bar" role="group" aria-label="Vehicle settings">
                    <button type="button" class="pajero-setting-btn" data-car-light-btn title="Toggle Xenon Headlights">
                        💡 Headlights
                    </button>
                    <button type="button" class="pajero-setting-btn" data-car-spin-btn title="Toggle 360 Turntable rotation">
                        🔄 Turntable
                    </button>
                    <button type="button" class="pajero-setting-btn" data-car-lift-btn title="Toggle off-road suspension height">
                        Lift: Street Stance
                    </button>
                </div>
            `;

            this.container.appendChild(overlay);

            overlay.querySelectorAll('[data-door-btn]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const doorName = btn.dataset.doorBtn;
                    if (doorName === 'all') {
                        this.toggleAllDoors();
                    } else {
                        this.toggleDoor(doorName);
                    }
                });
            });

            overlay.querySelectorAll('[data-pajero-cam]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    overlay.querySelectorAll('[data-pajero-cam]').forEach(b => b.classList.remove('is-active'));
                    btn.classList.add('is-active');
                    this.setCameraPreset(btn.dataset.pajeroCam, true);
                });
            });

            overlay.querySelector('[data-car-light-btn]')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleHeadlights();
            });

            overlay.querySelector('[data-car-spin-btn]')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleTurntable();
            });

            overlay.querySelector('[data-car-lift-btn]')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSuspension();
            });
        }

        destroy() {
            this.animating = false;
            window.removeEventListener('resize', this.onResize);
            if (this.renderer && this.renderer.domElement) {
                this.renderer.dispose();
                this.renderer.domElement.remove();
            }
        }
    }

    window.PajeroStudio = PajeroStudio;
    window.LIVERY_PRESETS = LIVERY_PRESETS;

    function initPajeroStudios() {
        const mainStage = document.querySelector('[data-pajero-showroom]');
        if (mainStage && !mainStage._pajeroStudioInitialized) {
            mainStage._pajeroStudioInitialized = true;
            const studio = new PajeroStudio(mainStage, {
                enableControls: true,
                autoRotate: false,
                initialView: 'hero'
            });
            window.mainPajeroStudio = studio;

            document.querySelectorAll('[data-paint]').forEach(dot => {
                dot.addEventListener('click', () => {
                    const liveryKey = dot.dataset.pajeroLivery || dot.dataset.paint;
                    if (liveryKey === 'heritage' || liveryKey === '#92998c' || dot.classList.contains('dakar') || dot.classList.contains('sage')) {
                        studio.setLivery('heritage');
                    } else if (liveryKey === 'safari' || liveryKey === '#b27554' || dot.classList.contains('safari') || dot.classList.contains('copper')) {
                        studio.setLivery('safari');
                    } else if (liveryKey === 'stealth' || liveryKey === '#636b73' || dot.classList.contains('stealth') || dot.classList.contains('graphite')) {
                        studio.setLivery('stealth');
                    } else if (liveryKey === 'forest' || dot.classList.contains('forest')) {
                        studio.setLivery('forest');
                    }
                    document.querySelectorAll('[data-paint]').forEach(d => d.classList.toggle('is-selected', d === dot));
                });
            });

            document.querySelectorAll('[data-inspect]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const inspectType = btn.dataset.inspect;
                    if (inspectType === 'engine') {
                        studio.setCameraPreset('engine');
                    } else if (inspectType === 'tires') {
                        studio.setCameraPreset('wheels');
                    } else if (inspectType === 'care') {
                        studio.toggleDoor('frontLeft', true);
                        studio.setCameraPreset('hero');
                    }
                });
            });
        }

        document.querySelectorAll('[data-pajero-compact]').forEach(container => {
            if (!container._pajeroStudioInitialized) {
                container._pajeroStudioInitialized = true;
                new PajeroStudio(container, {
                    enableControls: false,
                    autoRotate: true,
                    initialView: 'profile',
                    compact: true
                });
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPajeroStudios);
    } else {
        initPajeroStudios();
    }

})(window, document);

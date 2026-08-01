#!/usr/bin/env python3
"""生成费曼脑 3D 报告 — 含细胞粒子动画 + 架构说明"""
import json, random

with open('/home/duyw/physcausal/reports/brain_data.json') as f:
    data = json.load(f)

nodes_json = json.dumps(data['nodes'])
edges_json = json.dumps(data['edges'])
em_json = json.dumps(data['emergent_edges'])

html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>费曼脑 3D — 知识图谱 + 突触层 + 细胞</title>
<style>
*{{margin:0;padding:0}} body{{background:#050510;overflow:hidden;font-family:system-ui,monospace}}
#panel{{position:fixed;top:12px;left:12px;color:#aab;font-size:11px;z-index:10;
  background:rgba(6,6,24,0.9);padding:12px 16px;border-radius:8px;border:1px solid #1a1a35;max-width:320px;line-height:1.6}}
#panel h3{{color:#dde;margin:0 0 6px;font-size:14px}}
#panel .layer{{margin:4px 0;padding:4px 6px;border-radius:4px}}
#panel .layer1{{background:rgba(68,153,204,0.12);border-left:2px solid #4499cc}}
#panel .layer2{{background:rgba(136,68,204,0.12);border-left:2px solid #8844cc}}
#panel .layer3{{background:rgba(255,136,68,0.12);border-left:2px solid #f80}}
.g{{color:#ffd700}} .c{{color:#4af}} .p{{color:#f80}} .m{{color:#c4f}}
#stats{{margin-top:8px;font-size:10px;color:#667}}
</style></head><body>
<div id="panel">
<h3>🧠 费曼脑 架构</h3>
<div class="layer layer1">
<b style="color:#4499cc">知识图谱</b> — 骨架<br>
节点=物理概念 边=因果关系<br>
域: 力学/电磁/热力/量子/引力/光学
</div>
<div class="layer layer2">
<b style="color:#8844cc">突触层</b> — 使用权<br>
s值=预测-惊讶-学习三位一体<br>
边粗细=s值 金线=emergent捷径
</div>
<div class="layer layer3">
<b style="color:#f80">细胞殖民地</b> — 探路者<br>
<span class="p">●</span>粒子=游走细胞<br>
球大小=定居细胞数 亮度=密度
</div>
<div id="stats">
gen <b>{data['gen']}</b> | <span class="c">{data['cells']}</span>细胞 | 节点{len(data['nodes'])} | 边{data['edge_count']}+<span class="g">{data['emergent_count']}</span>
</div>
</div>
<script type="importmap">
{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}
</script>
<script type="module">
import * as THREE from 'three';
import {{OrbitControls}} from 'three/addons/controls/OrbitControls.js';

const N = {nodes_json};
const E = {edges_json};
const EM = {em_json};

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050510);
scene.fog = new THREE.Fog(0x050510, 35, 90);

const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, 0.5, 150);
camera.position.set(14, 10, 20);
camera.lookAt(0,0,0);

const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.06;
controls.minDistance = 4; controls.maxDistance = 70;

scene.add(new THREE.AmbientLight(0x2a2a3a));
const light = new THREE.DirectionalLight(0xffffff, 0.45);
light.position.set(20, 30, 20); scene.add(light);

const domains = ['mechanics','electromagnetism','thermodynamics','quantum','general_relativity','optics','unknown'];
const domainAngles = {{}};
domains.forEach((d,i) => {{ domainAngles[d] = (i/domains.length)*Math.PI*2 + 0.3; }});

const nodeMap = {{}}, nodePos = {{}}, nodePop = {{}};

N.forEach(n => {{
  const angle = domainAngles[n.domain] + (Math.random()-0.5)*0.6;
  const radius = 7 + n.depth*3.5 + Math.random()*2;
  const phi = (Math.random()-0.5)*Math.PI*0.6;
  const x = Math.cos(angle)*Math.cos(phi)*radius;
  const y = Math.sin(phi)*radius*1.5;
  const z = Math.sin(angle)*Math.cos(phi)*radius;

  const geom = new THREE.SphereGeometry(n.size*0.12, 6, 4);
  const mat = new THREE.MeshStandardMaterial({{
    color: n.color, emissive: n.color, emissiveIntensity: 0.08+n.pop*0.008,
    roughness: 0.7, metalness: 0.1, transparent: true, opacity: 0.6+n.pop*0.005
  }});
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(x,y,z);
  scene.add(mesh);
  nodeMap[n.id] = {{x,y,z}};
  nodePos[n.id] = new THREE.Vector3(x,y,z);
  nodePop[n.id] = n.pop;
}});

const allEdges = [];
[...E, ...EM].forEach(e => {{
  const s = nodeMap[e.s], t = nodeMap[e.t];
  if(!s||!t) return;
  const dx=t.x-s.x, dy=t.y-s.y, dz=t.z-s.z;
  if(Math.sqrt(dx*dx+dy*dy+dz*dz)>28) return;
  const mid = {{x:(s.x+t.x)/2+(Math.random()-0.5)*2, y:(s.y+t.y)/2+(Math.random()-0.5)*2, z:(s.z+t.z)/2+(Math.random()-0.5)*2}};
  const curve = new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(s.x,s.y,s.z), new THREE.Vector3(mid.x,mid.y,mid.z), new THREE.Vector3(t.x,t.y,t.z));
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(curve.getPoints(16)),
    new THREE.LineBasicMaterial({{color: e.color, transparent:true, opacity: e.opacity}}));
  scene.add(line);
  allEdges.push({{curve, s: e.s, t: e.t}});
}});

// 星空
const stars = new THREE.BufferGeometry();
const sp = [];
for(let i=0;i<500;i++) sp.push((Math.random()-0.5)*70,(Math.random()-0.5)*50,(Math.random()-0.5)*70);
stars.setAttribute('position', new THREE.Float32BufferAttribute(sp,3));
scene.add(new THREE.Points(stars, new THREE.PointsMaterial({{color:0x334466, size:0.07}})));

// ═══ 细胞粒子 ═══
const CELL_COUNT = Math.min(400, Math.max(60, {data['cells']} // 20));
const pGeom = new THREE.SphereGeometry(0.1, 4, 3);
const nodeIds = Object.keys(nodePos);
const totalPop = Object.values(nodePop).reduce((a,b)=>a+b, 0) || 1;
const particles = [];

for (let i = 0; i < CELL_COUNT; i++) {{
  let r = Math.random() * totalPop, acc = 0, startId = nodeIds[0];
  for (const nid of nodeIds) {{ acc += nodePop[nid]||0; if (acc >= r) {{ startId = nid; break; }} }}
  const outEdges = allEdges.filter(e => e.s === startId);
  const edge = outEdges.length > 0 ? outEdges[Math.floor(Math.random()*outEdges.length)] : allEdges[Math.floor(Math.random()*allEdges.length)];
  const mesh = new THREE.Mesh(pGeom, new THREE.MeshStandardMaterial({{color:0xff8844, emissive:0xff6600, emissiveIntensity:0.5, roughness:0.3, transparent:true, opacity:0.55+Math.random()*0.45}}));
  scene.add(mesh);
  particles.push({{mesh, curve: edge.curve, t: Math.random(), speed: 0.0008+Math.random()*0.003, s: edge.s}});
}}

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  particles.forEach(p => {{
    p.t += p.speed;
    if (p.t > 1.0) {{
      p.t = 0;
      const outEdges = allEdges.filter(e => e.s === p.s);
      if (outEdges.length > 0) {{
        const ne = outEdges[Math.floor(Math.random()*outEdges.length)];
        p.curve = ne.curve; p.s = ne.s;
      }}
    }}
    p.mesh.position.copy(p.curve.getPoint(p.t));
  }});
  renderer.render(scene, camera);
}}
animate();

window.addEventListener('resize', () => {{
  camera.aspect = innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}});
</script></body></html>'''

with open('/home/duyw/physcausal/reports/brain_3d_v2.html', 'w') as f:
    f.write(html)

import os
sz = os.path.getsize('/home/duyw/physcausal/reports/brain_3d_v2.html')
print(f"OK: brain_3d_v2.html ({sz//1024}KB)")

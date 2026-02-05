import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="3D 智能堆码专家 V10.0", layout="wide", initial_sidebar_state="collapsed")

# 隐藏 Streamlit 边栏及设置
st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; overflow: hidden !important; }
        iframe { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

html_code = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>3D 智能堆码专家 V10.0 - MaxRects 引擎</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <style>
        html, body { margin: 0; padding: 0; width: 100%; height: 100vh; overflow: hidden; font-family: "Microsoft YaHei", sans-serif; }
        body { display: flex; background: #f0f2f5; }
        #sidebar { width: 340px; background: white; border-right: 1px solid #ddd; padding: 15px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; z-index: 10; }
        #viewport { flex: 1; position: relative; background: #eef2f3; }
        .group-title { font-size: 13px; font-weight: bold; color: #333; border-left: 4px solid #3498db; padding-left: 8px; margin-top: 10px; }
        .input-row { display: flex; gap: 8px; }
        .input-item { flex: 1; display: flex; flex-direction: column; font-size: 11px; }
        input { padding: 6px; border: 1px solid #ccc; border-radius: 4px; margin-top: 2px; }
        button { padding: 10px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; font-size: 12px; transition: 0.2s; }
        .btn-main { background: #3498db; color: white; }
        .btn-anim { background: #9b59b6; color: white; }
        .btn-pdf { background: #27ae60; color: white; }
        .stats-card { background: #2c3e50; color: white; padding: 12px; border-radius: 8px; font-size: 12px; }
        #loading { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); color:white; display:none; flex-direction:column; justify-content:center; align-items:center; z-index:10000; }
        
        /* PDF 隐藏模板 */
        #report-tpl { position: absolute; left: -9999px; width: 800px; background: white; padding: 30px; }
        .rpt-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }
    </style>
</head>
<body>
<div id="loading"><p id="loadText">正在处理...</p></div>

<div id="sidebar">
    <h3 style="margin:0; color:#2c3e50;">📦 堆码专家 V10.0</h3>
    <div class="stats-card">
        <div>最佳装载方案: <b id="stCount">0</b> pcs</div>
        <div>利用率: <b id="stEff">0%</b></div>
        <div id="stMode" style="font-size:10px; color:#bdc3c7; margin-top:5px;"></div>
    </div>

    <div class="group-title">1. 外箱配置</div>
    <div class="input-row">
        <div class="input-item">L<input type="number" id="bL" value="400"></div>
        <div class="input-item">W<input type="number" id="bW" value="300"></div>
        <div class="input-item">H<input type="number" id="bH" value="300"></div>
    </div>
    <div class="input-row">
        <div class="input-item">壁厚(mm)<input type="number" id="wall" value="4"></div>
        <div class="input-item">膨胀(mm)<input type="number" id="bulge" value="0"></div>
    </div>

    <div class="group-title">2. 内件配置</div>
    <div class="input-row">
        <div class="input-item">长<input type="number" id="iL" value="180"></div>
        <div class="input-item">宽<input type="number" id="iW" value="120"></div>
        <div class="input-item">高<input type="number" id="iH" value="100"></div>
    </div>

    <button class="btn-main" onclick="runMaxRectsEngine()">执行 MaxRects 智能计算</button>
    <button class="btn-anim" onclick="startAnim()">🎬 演示装载</button>
    <button class="btn-pdf" onclick="exportPDF()">📄 导出详细报告</button>
    <button style="background:#95a5a6; color:white;" onclick="isOpen=!isOpen">开启/关闭纸箱</button>
</div>

<div id="viewport"></div>

<div id="report-tpl">
    <h1 style="text-align:center; color:#2c3e50;">智能装箱技术方案报告</h1>
    <hr>
    <div class="rpt-grid" id="rptInfo"></div>
    <div class="rpt-grid">
        <div style="text-align:center;"><img id="rImg1" style="width:100%; border:1px solid #ddd;"><p>空箱标注视图</p></div>
        <div style="text-align:center;"><img id="rImg2" style="width:100%; border:1px solid #ddd;"><p>满载渲染视图</p></div>
    </div>
    <h3>装载说明：</h3>
    <p>本方案采用 <b>Maximal Rectangles (极大矩形)</b> 算法。该算法通过实时维护空间坐标系中的最大可用矩形区域，消除了传统断头台算法切割带来的空间浪费，能更有效地压榨箱体边缘空间。</p>
</div>

<script>
    let scene, camera, renderer, controls, itemsGroup, boxGroup, labelGroup, flaps=[];
    let isOpen = false, isAnimating = false, animIndex = 0, animQueue = [];
    const layerColors = [0x3498db, 0xe67e22, 0x2ecc71, 0xe74c3c, 0x9b59b6];

    // --- 【算法核心】Maximal Rectangles 极大矩形算法 ---
    
    function solveMaxRects(width, height, itemL, itemW) {
        let freeRects = [{x: 0, y: 0, w: width, h: height}];
        let placedItems = [];

        while (true) {
            let bestRectIdx = -1;
            let bestScore = -Infinity;

            // 寻找最适合当前物品的矩形 (Best Short Side Fit)
            for (let i = 0; i < freeRects.length; i++) {
                let r = freeRects[i];
                if (r.w >= itemL && r.h >= itemW) {
                    let score = Math.min(r.w - itemL, r.h - itemW);
                    if (score > bestScore) { bestScore = score; bestRectIdx = i; }
                }
            }

            if (bestRectIdx === -1) break;

            let target = freeRects[bestRectIdx];
            let newItem = {x: target.x, y: target.y, w: itemL, h: itemW};
            placedItems.push(newItem);

            // 更新所有受影响的空闲矩形
            let newFreeRects = [];
            for (let i = 0; i < freeRects.length; i++) {
                let r = freeRects[i];
                // 如果相交，则切割
                if (!(newItem.x >= r.x + r.w || newItem.x + newItem.w <= r.x || newItem.y >= r.y + r.h || newItem.y + newItem.h <= r.y)) {
                    // 切割逻辑：产生上下左右四个可能的子矩形
                    if (newItem.x > r.x) newFreeRects.push({x: r.x, y: r.y, w: newItem.x - r.x, h: r.h});
                    if (newItem.x + newItem.w < r.x + r.w) newFreeRects.push({x: newItem.x + newItem.w, y: r.y, w: r.x + r.w - (newItem.x + newItem.w), h: r.h});
                    if (newItem.y > r.y) newFreeRects.push({x: r.x, y: r.y, w: r.w, h: newItem.y - r.y});
                    if (newItem.y + newItem.h < r.y + r.h) newFreeRects.push({x: r.x, y: newItem.y + newItem.h, w: r.w, h: r.y + r.h - (newItem.y + newItem.h)});
                } else {
                    newFreeRects.push(r);
                }
            }
            
            // 去重并清除包含关系的矩形
            freeRects = cleanFreeRects(newFreeRects);
        }
        return placedItems;
    }

    function cleanFreeRects(rects) {
        let result = [];
        for (let i = 0; i < rects.length; i++) {
            let isContained = false;
            for (let j = 0; j < rects.length; j++) {
                if (i === j) continue;
                let a = rects[i], b = rects[j];
                if (a.x >= b.x && a.y >= b.y && a.x + a.w <= b.x + b.w && a.y + a.h <= b.y + b.h) {
                    isContained = true; break;
                }
            }
            if (!isContained) result.push(rects[i]);
        }
        return result;
    }

    // --- 智能引擎：6姿态搜索 ---
    function runMaxRectsEngine() {
        const bL = parseFloat(document.getElementById('bL').value),
              bW = parseFloat(document.getElementById('bW').value),
              bH = parseFloat(document.getElementById('bH').value),
              wall = parseFloat(document.getElementById('wall').value),
              bulge = parseFloat(document.getElementById('bulge').value);
        
        const iL = parseFloat(document.getElementById('iL').value),
              iW = parseFloat(document.getElementById('iW').value),
              iH = parseFloat(document.getElementById('iH').value);

        const rL = bL - wall * 2 + bulge, rW = bW - wall * 2 + bulge, rH = bH - wall * 2 + bulge;

        // 定义 6 种旋转姿态
        const orientations = [
            {l: iL, w: iW, h: iH, n: "平放"}, {l: iL, w: iH, h: iW, n: "侧放(长)"}, 
            {l: iW, w: iL, h: iH, n: "平放(转)"}, {l: iW, w: iH, h: iL, n: "立放(宽)"},
            {l: iH, w: iL, h: iW, n: "侧放(高)"}, {l: iH, w: iW, h: iL, n: "立放(高)"}
        ];

        let best = { total: -1 };
        orientations.forEach(o => {
            const layerItems = solveMaxRects(rL, rW, o.l, o.w);
            const layers = Math.floor(rH / o.h);
            const total = layerItems.length * layers;
            if (total > best.total) {
                best = { total, layers, items: layerItems, config: o };
            }
        });

        document.getElementById('stMode').innerText = `最优摆放姿态：${best.config.n} (${best.config.l}x${best.config.w}x${best.config.h})`;
        render3D(bL, bW, bH, wall, best);
    }

    function render3D(vL, vW, vH, wall, data) {
        boxGroup.clear(); itemsGroup.clear();
        const mat = new THREE.MeshPhongMaterial({color: 0xd2a679, transparent:true, opacity:0.9, side: THREE.DoubleSide});
        const add=(g,x,y,z)=> { const m=new THREE.Mesh(g,mat); m.position.set(x,y,z); boxGroup.add(m); return m; };
        
        add(new THREE.BoxGeometry(vL, wall, vW), 0, 0, 0); // 底
        add(new THREE.BoxGeometry(vL, vH, wall), 0, vH/2, -vW/2); // 后
        add(new THREE.BoxGeometry(vL, vH, wall), 0, vH/2, vW/2); // 前
        add(new THREE.BoxGeometry(wall, vH, vW), -vL/2, vH/2, 0); // 左
        add(new THREE.BoxGeometry(wall, vH, vW), vL/2, vH/2, 0); // 右

        // 盖子
        const addFlap=(w,d,px,pz,ax,dir)=>{
            const pivot = new THREE.Group(); pivot.position.set(px, vH, pz);
            const m = new THREE.Mesh(new THREE.BoxGeometry(w, 2, d), mat);
            m.position.z = ax==='x'?d/2*-dir : 0;
            pivot.add(m); boxGroup.add(pivot); flaps.push({pivot, ax, dir, ang:0});
        };
        addFlap(vL, vW/2, 0, vW/2, 'x', 1); addFlap(vL, vW/2, 0, -vW/2, 'x', -1);

        const sX = -(vL - wall * 2) / 2, sZ = -(vW - wall * 2) / 2;
        data.items.forEach((it, idx) => {
            for(let y=0; y<data.layers; y++) {
                const g = new THREE.BoxGeometry(data.config.l-0.5, data.config.h-0.5, data.config.w-0.5);
                const m = new THREE.Mesh(g, new THREE.MeshPhongMaterial({color: layerColors[y % 5]}));
                m.position.set(sX + it.x + data.config.l/2, y*data.config.h + data.config.h/2 + wall/2, sZ + it.y + data.config.w/2);
                m.userData.finalY = m.position.y;
                m.userData.settled = true;
                itemsGroup.add(m);
            }
        });

        document.getElementById('stCount').innerText = data.total;
        document.getElementById('stEff').innerText = (data.total * data.config.l * data.config.w * data.config.h / (vL*vW*vH) * 100).toFixed(1) + "%";
    }

    function startAnim() {
        isAnimating = true; animIndex = 0;
        animQueue = itemsGroup.children.slice().sort((a,b) => a.position.y - b.position.y);
        animQueue.forEach(m => { m.visible = false; m.position.y += 300; m.userData.settled = false; });
        isOpen = true;
    }

    async function exportPDF() {
        document.getElementById('loading').style.display='flex';
        document.getElementById('loadText').innerText="正在生成报告视图...";
        
        itemsGroup.visible = false; renderer.render(scene, camera);
        document.getElementById('rImg1').src = renderer.domElement.toDataURL();
        itemsGroup.visible = true; renderer.render(scene, camera);
        document.getElementById('rImg2').src = renderer.domElement.toDataURL();

        document.getElementById('rptInfo').innerHTML = `
            <div style="padding:10px;">
                <p><b>装箱总数:</b> ${document.getElementById('stCount').innerText} pcs</p>
                <p><b>空间效率:</b> ${document.getElementById('stEff').innerText}</p>
            </div>
            <div style="padding:10px;">
                <p><b>纸箱尺寸:</b> ${document.getElementById('bL').value}x${document.getElementById('bW').value}x${document.getElementById('bH').value}</p>
                <p><b>内盒尺寸:</b> ${document.getElementById('iL').value}x${document.getElementById('iW').value}x${document.getElementById('iH').value}</p>
            </div>
        `;

        setTimeout(async () => {
            const canvas = await html2canvas(document.getElementById('report-tpl'), {scale:2});
            const pdf = new jspdf.jsPDF('p', 'mm', 'a4');
            pdf.addImage(canvas.toDataURL('image/jpeg'), 'JPEG', 0, 0, 210, 297);
            pdf.save('装箱技术方案V10.pdf');
            document.getElementById('loading').style.display='none';
        }, 500);
    }

    function init() {
        scene = new THREE.Scene(); scene.background = new THREE.Color(0xeef2f3);
        const v = document.getElementById('viewport');
        camera = new THREE.PerspectiveCamera(45, v.clientWidth/v.clientHeight, 1, 10000);
        camera.position.set(600, 800, 600);
        renderer = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
        renderer.setSize(v.clientWidth, v.clientHeight);
        v.appendChild(renderer.domElement);
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const l = new THREE.DirectionalLight(0xffffff, 0.5); l.position.set(1,1,1); scene.add(l);
        
        boxGroup = new THREE.Group(); itemsGroup = new THREE.Group();
        scene.add(boxGroup, itemsGroup);
        
        window.addEventListener('resize', () => {
            camera.aspect = v.clientWidth/v.clientHeight; camera.updateProjectionMatrix();
            renderer.setSize(v.clientWidth, v.clientHeight);
        });
        runMaxRectsEngine(); animate();
    }

    function animate() {
        requestAnimationFrame(animate);
        const target = isOpen ? Math.PI*0.8 : 0;
        flaps.forEach(f => {
            f.ang += (target - f.ang) * 0.1;
            if(f.ax==='x') f.pivot.rotation.x = f.ang * f.dir;
        });

        if(isAnimating) {
            if(animIndex < animQueue.length) {
                for(let i=0; i<2; i++) { // 每帧放两个，加速
                    if(animIndex < animQueue.length) {
                        animQueue[animIndex].visible = true; animIndex++;
                    }
                }
            }
            let active = false;
            animQueue.forEach(m => {
                if(m.visible && !m.userData.settled) {
                    if(m.position.y > m.userData.finalY + 1) {
                        m.position.y += (m.userData.finalY - m.position.y) * 0.2;
                        active = true;
                    } else {
                        m.position.y = m.userData.finalY; m.userData.settled = true;
                    }
                }
            });
            if(animIndex === animQueue.length && !active) isAnimating = false;
        }

        controls.update(); renderer.render(scene, camera);
    }
    init();
</script>
</body>
</html>
"""

components.html(html_code, height=1200, scrolling=False)

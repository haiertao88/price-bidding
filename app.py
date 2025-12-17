import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="华脉招采平台", layout="wide")

# --- 🎨 CSS 极致紧凑样式 ---
st.markdown("""
    <style>
        /* 1. 压缩页面顶部空白 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* 2. 压缩组件之间的垂直间距 (暴力压缩) */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.3rem !important; 
        }
        
        /* 3. 紧凑型卡片样式 */
        .compact-card {
            border: 1px solid #e6e6e6;
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 6px;
            background-color: white;
        }
        
        /* 4. 标题紧凑化 */
        h1, h2, h3 { margin-bottom: 0.2rem !important; padding-bottom: 0 !important; }
        h4, h5, h6 { margin-bottom: 0.1rem !important; margin-top: 0.1rem !important; }
        
        /* 5. 调整代码块(复制框)的样式，去除多余留白 */
        .stCode { margin-bottom: -0.5rem !important; }
        
        /* 6. 警告框样式 */
        .warning-box {
            background-color: #fff3cd; color: #856404; padding: 0.5rem;
            border-radius: 4px; text-align: center; font-size: 0.9rem; margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据结构 ---
@st.cache_resource
def get_global_data():
    return { "projects": {} } # 保持纯净，无默认演示数据

shared_data = get_global_data()

# 🛠️ 自动清洗旧数据
invalid_pids = []
for pid, data in shared_data["projects"].items():
    if 'deadline' not in data: invalid_pids.append(pid)
for pid in invalid_pids: del shared_data["projects"][pid]

# --- 工具函数 ---
def generate_random_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def file_to_base64(uploaded_file):
    if uploaded_file is None: return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        return {"name": uploaded_file.name, "type": uploaded_file.type, "data": b64}
    except Exception as e: return None

def get_download_link(file_dict, label="📎"):
    if not file_dict: return ""
    b64 = file_dict["data"]
    href = f'<a href="data:{file_dict["type"]};base64,{b64}" download="{file_dict["name"]}" style="text-decoration:none; color:#0068c9; font-weight:bold; font-size:0.85em;">{label}{file_dict["name"]}</a>'
    return href

# --- 登录页面 (紧凑版) ---
def login_page():
    st.markdown("<h3 style='text-align: center;'>🔐 华脉招采平台</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.container(border=True):
            u = st.text_input("用户名", label_visibility="collapsed", placeholder="用户名").strip()
            p = st.text_input("密码", type="password", label_visibility="collapsed", placeholder="密码/通行码").strip()
            if st.button("登录", type="primary", use_container_width=True):
                if u == "HUAMAI" and p == "HUAMAI888":
                    st.session_state.user_type = "admin"; st.session_state.user = u; st.rerun()
                else:
                    found = False
                    for pid, d in shared_data["projects"].items():
                        if u in d["codes"] and d["codes"][u] == p:
                            st.session_state.user_type = "supplier"; st.session_state.user = u; st.session_state.project_id = pid
                            st.rerun(); found = True; break
                    if not found: st.error("验证失败")

# --- 供应商界面 (极简行内布局) ---
def supplier_dashboard():
    user = st.session_state.user
    pid = st.session_state.project_id
    proj = shared_data["projects"].get(pid)

    if not proj: st.error("项目不存在"); return

    try: deadline = datetime.strptime(proj['deadline'], "%Y-%m-%d %H:%M")
    except: deadline = datetime.strptime(proj['deadline'], "%Y-%m-%d %H:%M:%S")

    now = datetime.now()
    closed = now > deadline
    left = deadline - now

    # 顶部极简信息条
    c1, c2, c3, c4 = st.columns([1, 2, 1.5, 0.5])
    c1.markdown(f"**👤 {user}**")
    c2.caption(f"项目: {proj['name']}")
    if closed: c3.error("🚫 已截止")
    else: c3.success(f"⏳ 剩余: {str(left).split('.')[0]}")
    if c4.button("退出", key="logout"): st.session_state.clear(); st.rerun()

    st.markdown("---")

    products = proj["products"]
    if not products: st.info("暂无产品"); return

    if not closed and timedelta(minutes=0) < left < timedelta(minutes=15):
         st.markdown('<div class="warning-box">🔥 竞价最后阶段！</div>', unsafe_allow_html=True)

    # 产品列表 (极度紧凑)
    for pname, pinfo in products.items():
        with st.container():
            # 第一行：产品名 + 数量 + 规格书 (左对齐)
            file_link = get_download_link(pinfo.get('admin_file'))
            st.markdown(f"**📦 {pname}** <span style='color:gray; font-size:0.9em'> | 数量: {pinfo['quantity']}</span> {file_link}", unsafe_allow_html=True)
            
            # 第二行：报价表单 (同行显示)
            with st.form(key=f"f_{pname}", border=False):
                # 定义列宽：价格(2) 备注(2) 附件(2) 按钮(1)
                fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
                with fc1:
                    price = st.number_input("单价", min_value=0.0, step=0.1, label_visibility="collapsed", placeholder="单价(¥)")
                with fc2:
                    remark = st.text_input("备注", label_visibility="collapsed", placeholder="备注")
                with fc3:
                    sup_file = st.file_uploader("附件", type=['pdf','jpg','xlsx'], label_visibility="collapsed", key=f"u_{pname}")
                with fc4:
                    sub = st.form_submit_button("提交", use_container_width=True)
                
                if sub:
                    if not closed:
                        if price > 0:
                            fdata = file_to_base64(sup_file)
                            pinfo['bids'].append({
                                'supplier': user, 'price': price, 'remark': remark,
                                'file': fdata, 'time': now.strftime('%H:%M:%S'), 'datetime': now
                            })
                            st.toast("✅ 报价已提交")
                        else:
                            st.toast("❌ 价格无效")
                    else:
                        st.error("已截止")
            st.markdown("<hr style='margin: 0.2rem 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)

# --- 管理员界面 (功能全 + 间距小) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 总控")
    menu = st.sidebar.radio("菜单", ["项目管理", "监控中心"])
    if st.sidebar.button("退出"): st.session_state.clear(); st.rerun()

    if menu == "项目管理":
        st.subheader("📁 项目管理")
        
        # 新建 (折叠以节省空间)
        with st.expander("➕ 新建项目", expanded=False):
            with st.form("new"):
                c1, c2, c3 = st.columns([2, 1, 1])
                n = c1.text_input("名称", placeholder="项目名")
                d = c2.date_input("日期", datetime.now())
                t = c3.time_input("时间", datetime.strptime("17:00", "%H:%M").time())
                s = st.text_area("供应商 (逗号隔开)", "GYSA, GYSB, GYSC", height=68)
                if st.form_submit_button("创建"):
                    if n:
                        pid = str(uuid.uuid4())[:8]
                        sl = [x.strip() for x in s.replace('，', ',').split(',') if x.strip()]
                        codes = {x: generate_random_code() for x in sl}
                        shared_data["projects"][pid] = {
                            "name": n, "deadline": f"{d} {t.strftime('%H:%M')}",
                            "codes": codes, "products": {}
                        }
                        st.rerun()

        st.markdown("---")
        
        # 项目列表
        projs = sorted([p for p in shared_data["projects"].items() if 'deadline' in p[1]], key=lambda x: x[1]['deadline'], reverse=True)
        
        for pid, p in projs:
            with st.expander(f"📅 {p['deadline']} | {p['name']}", expanded=False):
                # 授权信息 - 改回 st.code 以便复制
                st.caption("🔑 供应商授权 (点击右上角复制)")
                cols = st.columns(4)
                for i, (sup, code) in enumerate(p['codes'].items()):
                    with cols[i % 4]:
                        # 使用 st.code 实现一键复制
                        st.markdown(f"**{sup}**")
                        st.code(code, language="text")

                st.caption("📦 产品管理")
                # 现有产品 (行内显示删除按钮)
                for k, v in p['products'].items():
                    rc1, rc2 = st.columns([5, 1])
                    rc1.text(f"• {k} (x{v['quantity']})")
                    if rc2.button("✕", key=f"d{pid}{k}", help="删除"): 
                        del p['products'][k]; st.rerun()
                
                # 添加产品
                with st.form(f"add_{pid}"):
                    ac1, ac2, ac3, ac4 = st.columns([2, 1, 2, 1])
                    pn = ac1.text_input("产品", label_visibility="collapsed", placeholder="产品名")
                    pq = ac2.number_input("数量", min_value=1, label_visibility="collapsed")
                    pf = ac3.file_uploader("规格", label_visibility="collapsed", key=f"f_{pid}")
                    if ac4.form_submit_button("添加"):
                        if pn and pn not in p['products']:
                            p['products'][pn] = {"quantity": pq, "bids": [], "admin_file": file_to_base64(pf)}
                            st.rerun()
                
                if st.button("删除项目", key=f"del_{pid}"): del shared_data["projects"][pid]; st.rerun()

    elif menu == "监控中心":
        st.subheader("📊 监控中心")
        opts = {k: f"{v['deadline']} - {v['name']}" for k, v in shared_data["projects"].items() if 'deadline' in v}
        if not opts: st.warning("无数据"); return

        sel = st.selectbox("项目", list(opts.keys()), format_func=lambda x: opts[x], label_visibility="collapsed")
        proj = shared_data["projects"][sel]

        # 统计表
        st.markdown("##### 🏆 比价总览")
        summ = []
        for pn, pi in proj['products'].items():
            bids = pi['bids']
            if bids:
                prices = [b['price'] for b in bids]
                mn, mx = min(prices), max(prices)
                best = ", ".join(set([b['supplier'] for b in bids if b['price'] == mn]))
                diff = (mx - mn) / mn * 100 if mn > 0 else 0
                summ.append({"产品": pn, "数量": pi['quantity'], "最低": f"¥{mn}", "最优": best, "最高": f"¥{mx}", "价差": f"{diff:.1f}%", "报价数": len(bids)})
            else:
                summ.append({"产品": pn, "数量": pi['quantity'], "最低": "-", "最优": "-", "最高": "-", "价差": "-", "报价数": 0})
        st.dataframe(pd.DataFrame(summ), use_container_width=True, hide_index=True)

        # 导出
        all_d = []
        for pn, pi in proj['products'].items():
            for b in pi['bids']:
                all_d.append({"产品": pn, "数量": pi['quantity'], "供应商": b['supplier'], "单价": b['price'], "总价": b['price']*pi['quantity'], "备注": b['remark'], "时间": b['time']})
        if all_d:
            out = io.BytesIO()
            with pd.ExcelWriter(out) as writer: pd.DataFrame(all_d).to_excel(writer, index=False)
            st.download_button("📥 导出Excel", out.getvalue(), "报价明细.xlsx")

        st.markdown("---")
        
        # 详细图表
        for pn, pi in proj['products'].items():
            with st.container():
                st.markdown(f"**📦 {pn}**")
                if pi['bids']:
                    df = pd.DataFrame(pi['bids'])
                    c1, c2 = st.columns([1, 1.5])
                    c1.line_chart(df[['datetime','price','supplier']], x='datetime', y='price', color='supplier', height=180)
                    
                    show_df = df[['supplier','price','remark','time']].copy()
                    show_df['附件'] = ["✅" if b['file'] else "" for b in pi['bids']]
                    c2.dataframe(show_df, use_container_width=True, hide_index=True, height=180)
                    
                    links = [get_download_link(b['file'], f"{b['supplier']}附件") for b in pi['bids'] if b['file']]
                    if links: st.markdown(" ".join(links), unsafe_allow_html=True)
                else:
                    st.caption("暂无报价")
                st.divider()

if 'user' not in st.session_state: login_page()
else:
    if st.session_state.user_type == "admin": admin_dashboard()
    else: supplier_dashboard()

import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="华脉招采平台 Pro Max", layout="wide")

# --- 🎨 CSS 样式深度优化 (紧凑美化版) ---
st.markdown("""
    <style>
        /* 全局字体与间距优化 */
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        
        /* 压缩组件垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important; 
        }
        
        /* 自定义紧凑卡片样式 */
        .compact-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* 标题样式微调 */
        h4 { margin-bottom: 0px !important; padding-bottom: 0px !important; font-size: 1.1rem !important;}
        h5 { margin-bottom: 5px !important; font-size: 1rem !important; color: #555;}
        
        /* 警告框 */
        .warning-box {
            background-color: #fff3cd; color: #856404; padding: 0.8rem;
            border-radius: 5px; border: 1px solid #ffeeba; margin-bottom: 1rem;
            text-align: center; font-weight: bold; font-size: 0.9rem;
        }
        
        /* 调整表格紧凑度 */
        .stDataFrame { font-size: 0.9rem; }
        
        /* 隐藏代码框下边距 */
        .stCode { margin-bottom: -1rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据结构 ---
@st.cache_resource
def get_global_data():
    # 自动初始化演示数据 (方便测试)
    demo_deadline = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
    return {
        "projects": {
            "demo": {
                "name": "系统功能演示",
                "deadline": demo_deadline,
                "codes": {"GYSA": "123456", "GYSB": "123456"},
                "products": {
                    "测试光纤": {"quantity": 1000, "bids": [], "admin_file": None},
                    "测试机柜": {"quantity": 50, "bids": [], "admin_file": None}
                }
            }
        }
    }

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

def get_download_link(file_dict, label="📎附件"):
    if not file_dict: return ""
    b64 = file_dict["data"]
    href = f'<a href="data:{file_dict["type"]};base64,{b64}" download="{file_dict["name"]}" style="text-decoration:none; color:#0068c9; font-weight:bold; font-size:0.9em;">{label}</a>'
    return href

# --- 登录页面 ---
def login_page():
    st.markdown("<h2 style='text-align: center; color:#333;'>🔐 华脉招采平台</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("用户名").strip()
            password = st.text_input("密码 / 通行码", type="password").strip()
            if st.button("登录", type="primary", use_container_width=True):
                if username == "HUAMAI" and password == "HUAMAI888":
                    st.session_state.user_type = "admin"
                    st.session_state.user = username
                    st.rerun()
                else:
                    found_project = None
                    for pid, p_data in shared_data["projects"].items():
                        if username in p_data["codes"] and p_data["codes"][username] == password:
                            found_project = pid
                            break
                    if found_project:
                        st.session_state.user_type = "supplier"
                        st.session_state.user = username
                        st.session_state.project_id = found_project
                        st.success(f"欢迎 {username}")
                        st.rerun()
                    else:
                        st.error("验证失败")
            st.caption("默认测试: GYSA / 123456")

# --- 供应商界面 (紧凑美化版) ---
def supplier_dashboard():
    current_user = st.session_state.user
    project_id = st.session_state.project_id
    project = shared_data["projects"].get(project_id)

    if not project:
        st.error("项目已结束"); return

    try:
        deadline = datetime.strptime(project['deadline'], "%Y-%m-%d %H:%M")
    except:
        deadline = datetime.strptime(project['deadline'], "%Y-%m-%d %H:%M:%S")

    now = datetime.now()
    is_closed = now > deadline
    time_left = deadline - now

    # 顶部状态栏
    with st.sidebar:
        st.subheader(f"👤 {current_user}")
        st.info(f"项目: {project['name']}")
        if is_closed: st.error("🚫 已截止")
        else: st.success(f"⏳ 剩余: {str(time_left).split('.')[0]}")
        st.markdown("---")
        if st.button("退出"): st.session_state.clear(); st.rerun()

    st.markdown(f"#### 📝 报价单 - {project['name']}")
    
    if is_closed: st.warning("本轮询价已结束"); return

    products = project["products"]
    if not products: st.info("暂无产品"); return

    # 智能提醒
    if timedelta(hours=0) < time_left < timedelta(minutes=15):
         st.markdown('<div class="warning-box">🔥 竞价最后阶段，请尽快确认最终报价！</div>', unsafe_allow_html=True)

    # 遍历产品 (使用自定义 CSS 容器实现紧凑效果)
    for p_name, p_info in products.items():
        # 自定义卡片容器
        with st.container():
            st.markdown(f"""
            <div class="compact-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:bold; font-size:1.05em; color:#333;">📦 {p_name}</div>
                    <div style="color:#666; font-size:0.9em;">需求量: <span style="color:#000; font-weight:bold;">{p_info.get('quantity', '-')}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 操作区 (紧凑布局)
            c1, c2, c3, c4 = st.columns([1.2, 1.5, 2, 1])
            with c1:
                # 显示附件链接
                if p_info.get('admin_file'):
                    st.markdown(get_download_link(p_info['admin_file'], "📄 查看规格书"), unsafe_allow_html=True)
                else:
                    st.caption("无规格书")
            
            with st.form(key=f"{project_id}_{p_name}", border=False):
                # 利用 columns 将输入框并排
                fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1.5])
                with fc1:
                    price = st.number_input("含税单价", min_value=0.0, step=0.1, label_visibility="collapsed", placeholder="单价")
                with fc2:
                    remark = st.text_input("备注", label_visibility="collapsed", placeholder="备注:如货期")
                with fc3:
                    sup_file = st.file_uploader("附件", type=['pdf','jpg','xlsx'], label_visibility="collapsed", key=f"up_{p_name}")
                with fc4:
                    submitted = st.form_submit_button("🚀 提交", use_container_width=True)
                
                if submitted:
                    if price > 0:
                        file_data = file_to_base64(sup_file)
                        new_bid = {
                            'supplier': current_user, 'price': price, 'remark': remark,
                            'file': file_data, 'time': now.strftime('%H:%M:%S'), 'datetime': now
                        }
                        p_info['bids'].append(new_bid)
                        st.toast(f"{p_name} 报价成功!", icon="✅")
                    else:
                        st.toast("价格必须大于0", icon="❌")

# --- 管理员界面 (统计表 + 紧凑管理) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 华脉总控")
    menu = st.sidebar.radio("菜单", ["项目管理", "报价监控"])
    if st.sidebar.button("退出"): st.session_state.clear(); st.rerun()

    if menu == "项目管理":
        st.subheader("📁 项目管理")
        
        # 紧凑型新建框
        with st.expander("➕ 发布新询价", expanded=False):
            with st.form("new"):
                c1, c2, c3 = st.columns([2, 1, 1])
                name = c1.text_input("项目名称", placeholder="如: 服务器采购")
                date = c2.date_input("截止日期", datetime.now())
                time = c3.time_input("截止时间", datetime.strptime("17:00", "%H:%M").time())
                sups = st.text_area("供应商 (逗号隔开)", "GYSA, GYSB, GYSC", height=68)
                if st.form_submit_button("创建"):
                    if name:
                        pid = str(uuid.uuid4())[:8]
                        sup_list = [s.strip() for s in sups.replace('，', ',').split(',') if s.strip()]
                        codes = {s: generate_random_code() for s in sup_list}
                        shared_data["projects"][pid] = {
                            "name": name, "deadline": f"{date} {time.strftime('%H:%M')}",
                            "codes": codes, "products": {}
                        }
                        st.success("创建成功"); st.rerun()

        st.markdown("---")
        
        # 紧凑型项目列表
        valid_projects = sorted(
            [p for p in shared_data["projects"].items() if 'deadline' in p[1]], 
            key=lambda x: x[1]['deadline'], reverse=True
        )
        
        for pid, p in valid_projects:
            with st.expander(f"📅 {p['deadline']} | {p['name']}", expanded=False):
                # 供应商授权 (极简模式)
                st.caption("🔑 供应商授权")
                cols = st.columns(4)
                for i, (s, c) in enumerate(p['codes'].items()):
                    with cols[i % 4]:
                        st.text_input(f"{s}", value=c, key=f"c_{pid}_{s}", disabled=True)

                # 产品列表 (表格化展示更紧凑)
                st.caption("📦 产品列表")
                if p['products']:
                    # 准备表格数据
                    prod_rows = []
                    for k, v in p['products'].items():
                        prod_rows.append({
                            "产品名称": k,
                            "数量": v['quantity'],
                            "操作": "删除"
                        })
                    
                    # 简单展示，为了删除功能保留按钮
                    for k, v in p['products'].items():
                        r1, r2, r3 = st.columns([4, 1, 1])
                        r1.text(f"• {k} (x{v['quantity']})")
                        if r3.button("删", key=f"d{pid}{k}"): 
                            del p['products'][k]; st.rerun()
                
                # 添加产品 (单行)
                with st.form(f"add_p_{pid}"):
                    c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1])
                    pn = c1.text_input("产品名", label_visibility="collapsed", placeholder="产品名")
                    pq = c2.number_input("数量", min_value=1, label_visibility="collapsed")
                    pf = c3.file_uploader("规格书", label_visibility="collapsed", key=f"f_{pid}")
                    if c4.form_submit_button("添加"):
                        if pn and pn not in p['products']:
                            f_data = file_to_base64(pf)
                            p['products'][pn] = {"quantity": pq, "bids": [], "admin_file": f_data}
                            st.rerun()
                
                if st.button("🗑️ 删除项目", key=f"dd{pid}"):
                    del shared_data["projects"][pid]; st.rerun()

    elif menu == "报价监控":
        st.subheader("📊 监控中心")
        opts = {k: f"{v['deadline']} - {v['name']}" for k, v in shared_data["projects"].items() if 'deadline' in v}
        if not opts: st.warning("无数据"); return

        sel_id = st.selectbox("选择项目", list(opts.keys()), format_func=lambda x: opts[x])
        proj = shared_data["projects"][sel_id]

        # --- 🔥 核心功能：比价总览表 (统计最高/最低/最优) ---
        st.markdown("##### 🏆 比价总览")
        summary_data = []
        for pname, pinfo in proj['products'].items():
            bids = pinfo['bids']
            if bids:
                prices = [b['price'] for b in bids]
                min_price = min(prices)
                max_price = max(prices)
                # 找最低价供应商
                best_sups = [b['supplier'] for b in bids if b['price'] == min_price]
                best_sup_str = ", ".join(set(best_sups))
                # 找最高价供应商
                max_sups = [b['supplier'] for b in bids if b['price'] == max_price]
                
                # 计算价差
                diff = max_price - min_price
                diff_rate = (diff / min_price * 100) if min_price > 0 else 0
                
                summary_data.append({
                    "产品名称": pname,
                    "采购量": pinfo['quantity'],
                    "最低价": f"¥{min_price}",
                    "最优供应商": best_sup_str,
                    "最高价": f"¥{max_price}",
                    "价差率": f"{diff_rate:.1f}%",
                    "报价数": len(bids)
                })
            else:
                summary_data.append({
                    "产品名称": pname, "采购量": pinfo['quantity'],
                    "最低价": "--", "最优供应商": "--", "最高价": "--", 
                    "价差率": "--", "报价数": 0
                })
        
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        else:
            st.info("暂无产品数据")

        # 导出Excel
        all_data = []
        for pname, pinfo in proj['products'].items():
            for b in pinfo['bids']:
                all_data.append({
                    "产品": pname, "数量": pinfo['quantity'], "供应商": b['supplier'], 
                    "单价": b['price'], "总价": b['price']*pinfo['quantity'],
                    "备注": b['remark'], "时间": b['time']
                })
        if all_data:
            df = pd.DataFrame(all_data)
            out = io.BytesIO()
            with pd.ExcelWriter(out) as writer: df.to_excel(writer, index=False)
            st.download_button("📥 导出明细", out.getvalue(), "报价明细.xlsx")

        st.markdown("---")
        
        # 详细展示 (紧凑化)
        for pname, pinfo in proj['products'].items():
            with st.container():
                st.markdown(f"**📦 {pname}**")
                if not pinfo['bids']:
                    st.caption("暂无报价")
                    continue
                
                df = pd.DataFrame(pinfo['bids'])
                
                # 图表与表格并排
                c_chart, c_table = st.columns([1, 1.5])
                with c_chart:
                    st.line_chart(df[['datetime', 'price', 'supplier']], x='datetime', y='price', color='supplier', height=200)
                
                with c_table:
                    # 构造更适合展示的表格
                    display_df = df[['supplier', 'price', 'remark', 'time']].copy()
                    display_df.columns = ['供应商', '单价', '备注', '时间']
                    # 增加附件列
                    display_df['附件'] = [ "有" if b['file'] else "无" for b in pinfo['bids'] ]
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=200)

                # 下载附件链接列表
                file_links = []
                for b in pinfo['bids']:
                    if b['file']:
                        link = get_download_link(b['file'], f"{b['supplier']}附件")
                        file_links.append(link)
                if file_links:
                    st.markdown(" ".join(file_links), unsafe_allow_html=True)
                st.divider()

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

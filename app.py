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

# --- CSS 样式优化 ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .st-emotion-cache-1r6slb0 { padding: 1.5rem; border-radius: 8px; border: 1px solid #eee; }
        .stCode { margin-bottom: -1rem !important; }
        /* 警告框样式 */
        .warning-box {
            background-color: #fff3cd;
            color: #856404;
            padding: 1rem;
            border-radius: 5px;
            border: 1px solid #ffeeba;
            margin-bottom: 1rem;
            text-align: center;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据结构 ---
@st.cache_resource
def get_global_data():
    return { "projects": {} }

shared_data = get_global_data()

# --- 工具函数 ---
def generate_random_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# 文件转Base64 (用于存储)
def file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        return {"name": uploaded_file.name, "type": uploaded_file.type, "data": b64}
    except Exception as e:
        st.error(f"文件处理失败: {e}")
        return None

# Base64转下载链接 (用于下载)
def get_download_link(file_dict, label="📥 点击下载附件"):
    if not file_dict:
        return "无附件"
    b64 = file_dict["data"]
    filename = file_dict["name"]
    mime = file_dict["type"]
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}" style="text-decoration:none; color:#0068c9; font-weight:bold;">{label}: {filename}</a>'
    return href

def get_best_supplier(bids):
    """获取当前最低价供应商（用于计算排名是否变化）"""
    if not bids:
        return None, 0
    # 找最低价
    min_price = float('inf')
    best_sup = None
    for b in bids:
        if b['price'] < min_price:
            min_price = b['price']
            best_sup = b['supplier']
    return best_sup, min_price

# --- 登录逻辑 ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 华脉招采平台</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("用户名")
            password = st.text_input("密码 / 通行码", type="password")
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
                        st.success(f"验证成功！欢迎 {username}")
                        st.rerun()
                    else:
                        st.error("验证失败")

# --- 供应商界面 (无排名 + 附件 + 备注 + 智能提醒) ---
def supplier_dashboard():
    current_user = st.session_state.user
    project_id = st.session_state.project_id
    project = shared_data["projects"].get(project_id)

    if not project:
        st.error("项目不存在")
        if st.button("退出"): st.session_state.clear(); st.rerun()
        return

    # 时间检查 logic
    deadline = datetime.strptime(project['deadline'], "%Y-%m-%d %H:%M")
    now = datetime.now()
    is_closed = now > deadline
    time_left = deadline - now

    with st.sidebar:
        st.title(f"👤 {current_user}")
        st.caption(f"项目: {project['name']}")
        
        # 倒计时显示
        if is_closed:
            st.error("🚫 项目已截止")
        else:
            st.success(f"⏳ 剩余时间: {str(time_left).split('.')[0]}")
        
        st.divider()
        if st.button("退出登录"): st.session_state.clear(); st.rerun()

    st.markdown(f"### 📊 报价单 - {project['name']}")
    
    if is_closed:
        st.warning("⚠️ 本轮询价已结束，通道关闭。")
        return

    products = project["products"]
    if not products:
        st.info("暂无产品")
        return

    # --- 智能提醒逻辑 (1小时内 & 15分钟无变化) ---
    if timedelta(hours=0) < time_left < timedelta(hours=1):
        # 检查是否有任意产品的排名停滞
        any_stagnant = False
        for p_val in products.values():
            last_change = p_val.get('last_change_time')
            if last_change:
                # 如果最后一次排名变化是在15分钟前
                if (now - last_change) > timedelta(minutes=15):
                    any_stagnant = True
                    break
        
        if any_stagnant:
            st.markdown(f"""
            <div class="warning-box">
                ⚠️ 竞价即将截止！已有超过15分钟未出现更有竞争力的报价。<br>
                若您有意向，请尽快提交最终方案，以免系统关闭！
            </div>
            """, unsafe_allow_html=True)

    # 产品列表
    for p_name, p_info in products.items():
        with st.container(border=True):
            # 标题 + 甲方附件下载
            c_title, c_link = st.columns([2, 1])
            qty = p_info.get('quantity', 'N/A')
            c_title.markdown(f"#### 📦 {p_name} <small>(x{qty})</small>", unsafe_allow_html=True)
            
            # 显示甲方附件
            if p_info.get('admin_file'):
                c_link.markdown(get_download_link(p_info['admin_file'], "📄 下载规格书"), unsafe_allow_html=True)
            else:
                c_link.caption("无规格附件")

            # 报价表单
            with st.form(key=f"{project_id}_{p_name}"):
                c1, c2, c3 = st.columns([1, 1, 1])
                price = c1.number_input("单价 (¥)", min_value=0.0, step=0.1)
                remark = c2.text_input("备注 (选填)", placeholder="如: 货期3天, 含税")
                sup_file = c3.file_uploader("上传附件 (报价单/参数)", type=['pdf','png','jpg','xlsx'], key=f"up_{p_name}")
                
                if st.form_submit_button("🚀 提交报价"):
                    if price > 0:
                        # 处理附件
                        file_data = file_to_base64(sup_file)
                        
                        # 记录报价
                        new_bid = {
                            'supplier': current_user,
                            'price': price,
                            'remark': remark,
                            'file': file_data,
                            'time': now.strftime('%H:%M:%S'),
                            'datetime': now
                        }
                        p_info['bids'].append(new_bid)
                        
                        # --- 更新排名变化时间 logic ---
                        # 获取之前的Best
                        old_best = p_info.get('current_best_supplier')
                        # 计算现在的Best
                        new_best, _ = get_best_supplier(p_info['bids'])
                        
                        # 如果第一名换人了，或者这是第一个报价，更新时间戳
                        if new_best != old_best:
                            p_info['current_best_supplier'] = new_best
                            p_info['last_change_time'] = now
                        
                        st.success("提交成功！")
                        st.rerun()
                    else:
                        st.error("请输入有效价格")

# --- 管理员界面 ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 华脉总控")
    menu = st.sidebar.radio("菜单", ["项目管理", "报价监控"])
    if st.sidebar.button("退出"): st.session_state.clear(); st.rerun()

    if menu == "项目管理":
        st.title("📁 项目管理")
        
        with st.expander("➕ 发布新询价", expanded=True):
            with st.form("new"):
                c1, c2, c3 = st.columns([2, 1, 1])
                name = c1.text_input("项目名称")
                date = c2.date_input("截止日期", datetime.now())
                time = c3.time_input("截止时间", datetime.strptime("17:00", "%H:%M").time())
                sups = st.text_area("供应商列表", "GYSA, GYSB, GYSC")
                
                if st.form_submit_button("创建"):
                    if name:
                        pid = str(uuid.uuid4())[:8]
                        sup_list = [s.strip() for s in sups.replace('，', ',').split(',') if s.strip()]
                        codes = {s: generate_random_code() for s in sup_list}
                        # 合并日期时间
                        deadline_str = f"{date} {time}"
                        
                        shared_data["projects"][pid] = {
                            "name": name, 
                            "deadline": deadline_str,
                            "codes": codes, 
                            "products": {}
                        }
                        st.success("创建成功")
                        st.rerun()

        # 项目列表
        st.divider()
        for pid, p in sorted(shared_data["projects"].items(), key=lambda x: x[1]['deadline'], reverse=True):
            with st.expander(f"📅 截止: {p['deadline']} | {p['name']}", expanded=False):
                # 账号密码
                st.markdown("##### 🔑 供应商授权")
                cols = st.columns(4)
                for i, (s, c) in enumerate(p['codes'].items()):
                    cols[i%4].code(f"{s}\n{c}")
                
                # 产品管理
                st.markdown("##### 📦 产品列表")
                if p['products']:
                    for k, v in p['products'].items():
                        c_info, c_del = st.columns([4,1])
                        c_info.text(f"• {k} (x{v['quantity']})")
                        if c_del.button("删", key=f"d{pid}{k}"): 
                            del p['products'][k]; st.rerun()
                
                # 添加产品 + 附件
                st.markdown("---")
                with st.form(f"add_p_{pid}"):
                    c1, c2, c3 = st.columns([2, 1, 2])
                    pn = c1.text_input("产品名")
                    pq = c2.number_input("数量", 1, value=100)
                    pf = c3.file_uploader("上传规格书/图纸", key=f"f_{pid}")
                    if st.form_submit_button("添加产品"):
                        if pn and pn not in p['products']:
                            f_data = file_to_base64(pf)
                            p['products'][pn] = {
                                "quantity": pq, 
                                "bids": [], 
                                "admin_file": f_data,
                                "current_best_supplier": None,
                                "last_change_time": None
                            }
                            st.rerun()
                
                if st.button("删除项目", key=f"dd{pid}"):
                    del shared_data["projects"][pid]; st.rerun()

    elif menu == "报价监控":
        st.title("📊 监控中心")
        if not shared_data["projects"]: st.warning("无项目"); return
        
        opts = {k: f"{v['deadline']} - {v['name']}" for k, v in shared_data["projects"].items()}
        sel_id = st.selectbox("选择项目", list(opts.keys()), format_func=lambda x: opts[x])
        proj = shared_data["projects"][sel_id]

        # 导出Excel
        all_data = []
        for pname, pinfo in proj['products'].items():
            for b in pinfo['bids']:
                all_data.append({
                    "产品": pname, "数量": pinfo['quantity'], 
                    "供应商": b['supplier'], "单价": b['price'], 
                    "备注": b['remark'], "报价时间": b['time'],
                    "附件": "有" if b['file'] else "无"
                })
        if all_data:
            df = pd.DataFrame(all_data)
            out = io.BytesIO()
            with pd.ExcelWriter(out) as writer: df.to_excel(writer, index=False)
            st.download_button("📥 导出Excel", out.getvalue(), "报价明细.xlsx")

        st.divider()
        
        # 详细展示
        for pname, pinfo in proj['products'].items():
            with st.container(border=True):
                st.subheader(f"📦 {pname}")
                if not pinfo['bids']:
                    st.caption("等待报价...")
                    continue
                
                # 最好报价
                df = pd.DataFrame(pinfo['bids'])
                best = df.loc[df['price'].idxmin()]
                
                m1, m2, m3 = st.columns(3)
                m1.metric("最低价", f"¥{best['price']}")
                m1.caption(f"由 {best['supplier']} 提供")
                
                # 图表
                chart_data = df[['datetime', 'price', 'supplier']].copy()
                st.line_chart(chart_data, x='datetime', y='price', color='supplier')
                
                # 详细列表 (带附件下载)
                st.markdown("###### 📝 报价明细")
                # 转换数据以便展示下载链接
                display_rows = []
                for b in pinfo['bids']:
                    file_link = get_download_link(b['file'], "下载") if b['file'] else "-"
                    display_rows.append(f"| {b['supplier']} | ¥{b['price']} | {b['remark']} | {b['time']} | {file_link} |")
                
                st.markdown("| 供应商 | 单价 | 备注 | 时间 | 附件 |\n|---|---|---|---|---|")
                st.markdown("\n".join(display_rows), unsafe_allow_html=True)

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta
import hashlib

# --- 页面配置 ---
st.set_page_config(page_title="华脉招采平台", layout="wide", page_icon="🏢")

# --- 🎨 CSS 样式深度定制 (V2.1 修复字体显示问题) ---
st.markdown("""
    <style>
        /* 1. 全局布局紧凑化 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        div[data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
        
        /* 2. 背景与字体优化 */
        .stApp { background-color: #f4f6f9; }
        
        /* ⭐️ 核心修复：标题显示不全的问题 */
        h1, h2, h3, h4 {
            line-height: 1.6 !important; /* 增加行高，防止切头去尾 */
            padding-top: 10px !important; /* 顶部留出空间 */
            padding-bottom: 10px !important; /* 底部留出空间 */
            font-family: "Source Sans Pro", "Microsoft YaHei", "微软雅黑", sans-serif !important; /* 强制使用中文友好字体 */
            overflow: visible !important; /* 确保内容不被裁剪 */
        }
        
        /* 3. 卡片式容器 - 核心UI组件 */
        .ui-card {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e1e4e8;
            margin-bottom: 15px;
        }

        /* 4. 优化 st.code 显示 (用于账号密码复制) */
        .stCode { font-size: 14px !important; margin-bottom: 0px !important; }
        div[data-testid="stCodeBlock"] > pre {
            padding: 0.4rem 0.8rem !important;
            border-radius: 4px !important;
            background-color: #f1f3f5 !important;
            border: 1px solid #dee2e6 !important;
        }

        /* 5. 文件上传组件极简风 */
        section[data-testid="stFileUploader"] { padding: 0px !important; min-height: 0px !important; }
        section[data-testid="stFileUploader"] > div { padding-top: 5px !important; padding-bottom: 5px !important; }
        section[data-testid="stFileUploader"] small { display: none; }
        [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
        [data-testid="stFileUploader"] button {
            border: 1px solid #d1d5db;
            color: #4b5563;
            background-color: white;
            padding: 2px 10px;
            font-size: 13px;
        }

        /* 6. 表格与输入框微调 */
        .stDataFrame { border: 1px solid #eee; border-radius: 6px; }
        .stTextInput > div > div > input { padding: 8px 10px; font-size: 14px; }
        
        /* 7. 自定义标签与徽章 */
        .file-tag {
            display: inline-block; background-color: #e3f2fd; color: #0d47a1;
            padding: 2px 10px; border-radius: 12px; border: 1px solid #bbdefb;
            text-decoration: none; font-size: 0.8rem; margin-right: 5px;
        }
        .file-tag:hover { background-color: #bbdefb; }
        
        /* 隐藏默认菜单 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 全局数据初始化 ---
@st.cache_resource
def init_global_data():
    """初始化全局数据，确保所有键都存在且类型正确"""
    return {
        "projects": {},  # 项目字典：{项目ID: {name, deadline, codes, products}}
        "suppliers": {   # 供应商字典
            "GYSA": {"contact": "张经理", "phone": "13800138000", "job": "销售总监", "type": "光纤光缆", "address": "江苏省南京市江宁区xxx号"},
            "GYSB": {"contact": "李工", "phone": "13900139000", "job": "技术支持", "type": "网络机柜", "address": "江苏省苏州市工业园区xxx号"},
            "GYSC": {"contact": "王总", "phone": "13700137000", "job": "总经理", "type": "综合布线", "address": "上海市浦东新区xxx号"}
        }
    }

global_data = init_global_data()

# --- 工具函数 ---
def generate_random_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def file_to_base64(uploaded_file, max_size=200*1024*1024):
    if uploaded_file is None: return None
    file_size = uploaded_file.size
    if file_size > max_size:
        st.error(f"文件过大（{file_size/1024/1024:.1f}MB），最大支持200MB")
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        return {
            "name": uploaded_file.name,
            "type": uploaded_file.type,
            "data": base64.b64encode(bytes_data).decode('utf-8'),
            "size": file_size,
            "hash": hashlib.md5(bytes_data).hexdigest()
        }
    except Exception as e:
        st.error(f"文件处理失败：{str(e)}")
        return None

def get_styled_download_tag(file_dict, supplier_name=""):
    if not isinstance(file_dict, dict) or not file_dict.get('data'): return ""
    display_label = f"📎 {supplier_name} - {file_dict['name']}" if supplier_name else f"📎 {file_dict['name']}"
    return f'<a href="data:{file_dict["type"]};base64,{file_dict["data"]}" download="{file_dict["name"]}" class="file-tag" target="_blank">{display_label}</a>'

def safe_parse_deadline(deadline_str):
    if not isinstance(deadline_str, str): return datetime.now() + timedelta(hours=1)
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try: return datetime.strptime(deadline_str, fmt)
        except ValueError: continue
    return datetime.now() + timedelta(hours=1)

# --- 登录页面 ---
def render_login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #1e293b; margin-top:0;'>🔐 华脉招采平台</h2>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9em; margin-bottom: 20px;'>专业 · 高效 · 透明</div>", unsafe_allow_html=True)
        
        username = st.text_input("用户名", placeholder="请输入用户名").strip()
        password = st.text_input("密码", type="password", placeholder="请输入密码").strip()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("立即登录", type="primary", use_container_width=True):
            if username == "HUAMAI" and password == "HUAMAI888":
                st.session_state["user_type"] = "admin"
                st.session_state["user"] = username
                st.rerun()
            else:
                login_success = False
                for pid, pdata in global_data["projects"].items():
                    codes = pdata.get("codes", {})
                    if username in codes and codes[username] == password:
                        st.session_state["user_type"] = "supplier"
                        st.session_state["user"] = username
                        st.session_state["project_id"] = pid
                        login_success = True
                        st.rerun()
                        break
                if not login_success:
                    st.error("❌ 用户名或密码错误")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 供应商端页面 ---
def render_supplier_dashboard():
    if "user" not in st.session_state: st.rerun()
    
    supplier_name = st.session_state["user"]
    project_id = st.session_state["project_id"]
    project_data = global_data["projects"].get(project_id)
    
    if not project_data:
        st.error("项目已结束或不存在"); return

    deadline = safe_parse_deadline(project_data.get("deadline", ""))
    now = datetime.now()
    is_closed = now > deadline
    time_str = str(deadline - now).split('.')[0] if not is_closed else "已结束"

    # 头部卡片
    st.markdown(f"""
    <div class="ui-card" style="border-left: 5px solid #3b82f6;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h3 style="margin:0;">👤 {supplier_name} | 正在报价</h3>
                <div style="color:#666; margin-top:5px;">📋 项目：{project_data.get('name')}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:bold; font-size:1.2em; color: {'#ef4444' if is_closed else '#10b981'};">
                    {'🚫 报价已截止' if is_closed else f'⏳ 剩余时间: {time_str}'}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_l, col_r = st.columns([6, 1])
    with col_r:
        if st.button("退出登录", use_container_width=True):
            st.session_state.clear(); st.rerun()

    # 产品列表
    products = project_data.get("products", {})
    if not products: st.info("暂无报价产品"); return

    if "submit_lock" not in st.session_state: st.session_state["submit_lock"] = {}

    for p_name, p_info in products.items():
        with st.container():
            st.markdown(f'<div class="ui-card">', unsafe_allow_html=True)
            
            # 产品标题行
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**📦 {p_name}** <span style='color:#666; font-size:0.9em'>({p_info.get('desc','')})</span>", unsafe_allow_html=True)
                if p_info.get("admin_file"):
                    st.markdown(get_styled_download_tag(p_info["admin_file"], "技术规格书"), unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='text-align:right; font-weight:bold;'>需求数量: {p_info['quantity']}</div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 10px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

            # 报价表单
            with st.form(key=f"form_{p_name}", border=False):
                fc1, fc2, fc3, fc4 = st.columns([1.5, 2, 2, 1])
                with fc1:
                    price = st.number_input("单价(¥)", min_value=0.0, step=0.1, key=f"p_{p_name}")
                with fc2:
                    remark = st.text_input("备注", placeholder="选填", key=f"r_{p_name}")
                with fc3:
                    file_up = st.file_uploader("附件", key=f"f_{p_name}")
                with fc4:
                    st.markdown("<br>", unsafe_allow_html=True) # 对齐按钮
                    sub_btn = st.form_submit_button("提交报价", disabled=is_closed, use_container_width=True, type="primary")

                if sub_btn:
                    if is_closed: st.error("已截止")
                    elif price <= 0: st.error("价格需大于0")
                    else:
                        f_data = file_to_base64(file_up)
                        # 重复检测逻辑
                        new_bid = {
                            "supplier": supplier_name, "price": price, "remark": remark,
                            "file": f_data, "time": now.strftime("%H:%M:%S"), "datetime": now
                        }
                        if "bids" not in p_info: p_info["bids"] = []
                        p_info["bids"].append(new_bid)
                        st.success("✅ 提交成功")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 管理员端页面 ---
def render_admin_dashboard():
    with st.sidebar:
        st.markdown("### 👮‍♂️ 管理员控制台")
        menu = st.radio("导航", ["项目管理", "供应商库", "监控中心"], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🚪 退出系统", use_container_width=True):
            st.session_state.clear(); st.rerun()

    # ================= 项目管理 =================
    if menu == "项目管理":
        st.subheader("📁 项目管理")
        
        # 新建项目卡片
        with st.expander("➕ 创建新询价项目", expanded=False):
            with st.form("new_proj"):
                c1, c2, c3 = st.columns([2, 1, 1])
                p_name = c1.text_input("项目名称")
                p_date = c2.date_input("截止日期")
                p_time = c3.time_input("截止时间", value=datetime.strptime("17:00", "%H:%M").time())
                
                # 供应商多选
                all_sups = list(global_data["suppliers"].keys())
                sel_sups = st.multiselect("选择参与供应商", all_sups)
                
                if st.form_submit_button("立即创建", type="primary"):
                    if not p_name or not sel_sups:
                        st.error("信息不完整")
                    else:
                        pid = str(uuid.uuid4())[:8]
                        codes = {s: generate_random_code() for s in sel_sups}
                        global_data["projects"][pid] = {
                            "name": p_name,
                            "deadline": f"{p_date} {p_time.strftime('%H:%M')}",
                            "codes": codes,
                            "products": {}
                        }
                        st.success("创建成功"); st.rerun()

        # 项目列表（按时间排序）
        if not global_data["projects"]:
            st.info("暂无项目")
        else:
            # 排序：最近截止的在前
            sorted_projs = sorted(
                global_data["projects"].items(),
                key=lambda x: x[1]["deadline"],
                reverse=True
            )
            
            for pid, pdata in sorted_projs:
                with st.expander(f"📅 {pdata['deadline']} | {pdata['name']}", expanded=False):
                    
                    # 1. 供应商账号管理（修复：使用 st.code 实现复制，优化布局）
                    st.markdown("#### 🔑 供应商授权与密码")
                    st.info("💡 鼠标悬停在账号或密码上，点击右上角图标即可复制")
                    
                    codes = pdata.get("codes", {})
                    if codes:
                        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
                        # 表头
                        h1, h2, h3, h4 = st.columns([1.5, 2, 2, 1])
                        h1.markdown("**供应商**"); h2.markdown("**登录账号**"); h3.markdown("**登录密码**"); h4.markdown("**操作**")
                        st.markdown("<hr style='margin:5px 0'>", unsafe_allow_html=True)
                        
                        for s_name, s_code in codes.items():
                            r1, r2, r3, r4 = st.columns([1.5, 2, 2, 1])
                            with r1: st.markdown(f"<div style='margin-top:5px'>{s_name}</div>", unsafe_allow_html=True)
                            with r2: st.code(s_name, language=None) # 账号
                            with r3: st.code(s_code, language=None) # 密码
                            with r4: 
                                if st.button("移除", key=f"rm_{pid}_{s_name}"):
                                    del pdata["codes"][s_name]; st.rerun()
                        
                        # 追加供应商逻辑
                        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
                        ac1, ac2 = st.columns([3, 1])
                        new_sup_name = ac1.text_input("追加新供应商(输入名称)", key=f"add_sup_in_{pid}", label_visibility="collapsed", placeholder="输入名称自动生成账号")
                        if ac2.button("追加", key=f"btn_add_{pid}"):
                            if new_sup_name and new_sup_name not in codes:
                                pdata["codes"][new_sup_name] = generate_random_code()
                                # 同步到库
                                if new_sup_name not in global_data["suppliers"]:
                                    global_data["suppliers"][new_sup_name] = {}
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    # 2. 产品管理
                    st.markdown("#### 📦 询价产品列表")
                    prods = pdata.get("products", {})
                    # 添加产品
                    with st.form(f"add_p_{pid}", border=True):
                        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                        pn = c1.text_input("产品名")
                        pq = c2.number_input("数量", min_value=1, value=1)
                        pd_ = c3.text_input("描述")
                        pf = c4.form_submit_button("添加产品")
                        if pf and pn:
                            pdata["products"][pn] = {"quantity": pq, "desc": pd_, "bids": []}
                            st.rerun()
                    
                    # 显示产品
                    if prods:
                        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
                        for pdn, pdi in prods.items():
                            c1, c2 = st.columns([6, 1])
                            c1.markdown(f"• **{pdn}** (x{pdi['quantity']}) - {pdi.get('desc')}")
                            if c2.button("删除", key=f"del_p_{pid}_{pdn}"):
                                del pdata["products"][pdn]; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("🗑️ 删除整个项目", key=f"del_proj_{pid}"):
                        del global_data["projects"][pid]; st.rerun()

    # ================= 供应商库 =================
    elif menu == "供应商库":
        st.subheader("🏢 供应商数据库")
        
        # 使用 data_editor 实现 Excel 般的操作体验
        df = pd.DataFrame.from_dict(global_data["suppliers"], orient='index')
        if df.empty:
            df = pd.DataFrame(columns=["contact", "phone", "job", "type", "address"])
        
        # 列名美化
        df.columns = ["联系人", "电话", "职位", "产品类型", "地址"]
        
        with st.container():
            st.markdown('<div class="ui-card">', unsafe_allow_html=True)
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="sup_editor")
            
            if st.button("💾 保存更改", type="primary"):
                # 将DataFrame转回字典格式
                new_dict = {}
                for idx, row in edited_df.iterrows():
                    new_dict[idx] = {
                        "contact": row.get("联系人",""), "phone": row.get("电话",""),
                        "job": row.get("职位",""), "type": row.get("产品类型",""), "address": row.get("地址","")
                    }
                global_data["suppliers"] = new_dict
                st.success("已保存")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ================= 监控中心 =================
    elif menu == "监控中心":
        st.subheader("📊 报价分析看板")
        
        proj_opts = {pid: f"{d['deadline']} | {d['name']}" for pid, d in global_data["projects"].items()}
        sel_pid = st.selectbox("选择项目", options=list(proj_opts.keys()), format_func=lambda x: proj_opts[x])
        
        if sel_pid:
            pdata = global_data["projects"][sel_pid]
            products = pdata.get("products", {})
            
            # 汇总表逻辑
            summary = []
            for pn, pinfo in products.items():
                bids = [b for b in pinfo.get("bids", []) if b["price"] > 0]
                if bids:
                    prices = [b["price"] for b in bids]
                    min_p = min(prices)
                    best_sups = ",".join(set([b["supplier"] for b in bids if b["price"] == min_p]))
                    summary.append({
                        "产品": pn, "数量": pinfo["quantity"], "最低单价": min_p, 
                        "最低总价": min_p * pinfo["quantity"], "推荐供应商": best_sups, "报价数": len(bids)
                    })
                else:
                    summary.append({"产品": pn, "数量": pinfo["quantity"], "报价数": 0})
            
            st.markdown('<div class="ui-card">', unsafe_allow_html=True)
            st.markdown("#### 🏆 比价汇总")
            st.dataframe(pd.DataFrame(summary), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 详细对比图表
            st.markdown("#### 📈 报价明细")
            for pn, pinfo in products.items():
                bids = pinfo.get("bids", [])
                if bids:
                    st.markdown(f"**{pn}**")
                    chart_data = pd.DataFrame(bids)
                    # 图表：供应商 vs 价格
                    st.bar_chart(chart_data, x="supplier", y="price", color="#3b82f6")

# --- 主程序入口 ---
def main():
    if "user" not in st.session_state:
        render_login_page()
    else:
        u_type = st.session_state.get("user_type")
        if u_type == "admin": render_admin_dashboard()
        elif u_type == "supplier": render_supplier_dashboard()
        else: st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()

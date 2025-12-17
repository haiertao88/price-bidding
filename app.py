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

# --- 🎨 CSS 样式深度定制 ---
st.markdown("""
    <style>
        /* 基础布局优化 */
        .block-container {
            padding-top: 4rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
        
        /* 复制框样式修复 */
        .stCode { font-size: 0.9em !important; margin-bottom: 0px !important; }
        div[data-testid="stCodeBlock"] > pre { padding: 0.4rem !important; border-radius: 4px !important; }

        /* 文件上传框压缩 */
        section[data-testid="stFileUploader"] { padding: 0px !important; min-height: 0px !important; }
        section[data-testid="stFileUploader"] > div { padding-top: 5px !important; padding-bottom: 5px !important; }
        section[data-testid="stFileUploader"] small { display: none; }

        /* 上传组件汉化 */
        [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child { display: none; }
        [data-testid="stFileUploaderDropzoneInstructions"] > div:nth-child(2) small { display: none; }
        [data-testid="stFileUploader"] button { color: transparent !important; position: relative; min-width: 80px !important; }
        [data-testid="stFileUploader"] button::after {
            content: "📂 选择文件"; color: #31333F; position: absolute;
            left: 50%; top: 50%; transform: translate(-50%, -50%);
            font-size: 14px; white-space: nowrap;
        }
        section[data-testid="stFileUploader"] > div > div::before {
            content: "拖拽文件到此处 / 单个限制 200MB"; position: absolute;
            left: 10px; top: 50%; transform: translateY(-50%);
            font-size: 13px; color: #888; pointer-events: none; z-index: 1;
        }
        section[data-testid="stFileUploader"] > div { justify-content: flex-end; }

        /* 卡片与表格 */
        .compact-card { border: 1px solid #eee; background-color: #fcfcfc; padding: 8px 12px; border-radius: 6px; margin-bottom: 2px; }
        .stDataFrame { font-size: 0.85rem; }
        
        /* 产品描述文字 */
        .prod-desc { font-size: 0.85em; color: #666; margin-left: 5px; font-style: italic;}

        /* 附件下载胶囊 */
        .file-tag {
            display: inline-block; background-color: #f0f2f6; color: #31333F;
            padding: 4px 10px; border-radius: 15px; border: 1px solid #dce0e6;
            margin-right: 8px; margin-bottom: 8px; text-decoration: none;
            font-size: 0.85rem; transition: all 0.2s;
        }
        .file-tag:hover { background-color: #e0e4eb; border-color: #cdd3dd; color: #0068c9; }
        
        /* 供应商标签样式 */
        .sup-badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            background-color: #e6f3ff; color: #0068c9; border: 1px solid #cce5ff;
            font-size: 0.85rem; margin-right: 5px; margin-bottom: 5px;
        }
        .sup-info { font-size: 0.8em; color: #666; margin-left: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据 ---
@st.cache_resource
def get_global_data():
    return { 
        "projects": {},
        "suppliers": {
            "GYSA": {"contact": "张经理", "phone": "13800138000", "job": "销售总监", "type": "光纤光缆", "address": "江苏省南京市江宁区xxx号"},
            "GYSB": {"contact": "李工", "phone": "13900139000", "job": "技术支持", "type": "网络机柜", "address": "江苏省苏州市工业园区xxx号"},
            "GYSC": {"contact": "王总", "phone": "13700137000", "job": "总经理", "type": "综合布线", "address": "上海市浦东新区xxx号"}
        }
    }
shared_data = get_global_data()

# 数据结构清洗
if isinstance(shared_data.get("suppliers"), list):
    old_list = shared_data["suppliers"]
    shared_data["suppliers"] = {name: {"contact": "", "phone": "", "job": "", "type": "", "address": ""} for name in old_list}

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

def get_styled_download_tag(file_dict, supplier_name=""):
    if not file_dict: return ""
    b64 = file_dict["data"]
    label = f"📎 {supplier_name} - {file_dict['name']}" if supplier_name else f"📎 {file_dict['name']}"
    href = f"""<a href="data:{file_dict['type']};base64,{b64}" download="{file_dict['name']}" class="file-tag" target="_blank">{label}</a>"""
    return href

def get_simple_download_link(file_dict, label="📄"):
    if not file_dict: return ""
    b64 = file_dict["data"]
    display_text = f"{label} （华脉提供资料）: {file_dict['name']}"
    return f'<a href="data:{file_dict["type"]};base64,{b64}" download="{file_dict["name"]}" style="text-decoration:none; color:#0068c9; font-weight:bold; font-size:0.85em;">{display_text}</a>'

# --- 登录页面 ---
def login_page():
    st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>🔐 华脉招采平台</h3>", unsafe_allow_html=True)
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

# --- 供应商界面 ---
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

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1.2, 0.6, 0.6])
        c1.markdown(f"**👤 {user}**")
        c2.caption(f"项目: {proj['name']}")
        if closed: c3.error("🚫 已截止")
        else: c3.success(f"⏳ 剩余: {str(left).split('.')[0]}")
        if c4.button("🔄 刷新", help="获取最新数据"): st.rerun()
        if c5.button("退出"): st.session_state.clear(); st.rerun()

    products = proj["products"]
    if not products: st.info("暂无产品"); return
    if not closed and timedelta(minutes=0) < left < timedelta(minutes=15): st.warning("🔥 竞价最后阶段！")

    for pname, pinfo in products.items():
        with st.container():
            # 显示产品描述
            desc_text = pinfo.get('desc', '')
            desc_html = f"<span class='prod-desc'>({desc_text})</span>" if desc_text else ""
            
            st.markdown(f"""
            <div class="compact-card" style="display:flex; justify-content:space-between; align-items:center;">
                <span><b>📦 {pname}</b> {desc_html}</span>
                <small style='color:#666'>数量: {pinfo['quantity']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            link = get_simple_download_link(pinfo.get('admin_file'))
            if link: st.markdown(f"<div style='margin-top:-5px; margin-bottom:5px; font-size:0.8rem'>{link}</div>", unsafe_allow_html=True)

            with st.form(key=f"f_{pname}", border=False):
                fc1, fc2, fc3, fc4 = st.columns([1.5, 2, 2, 1])
                with fc1: price = st.number_input("单价", min_value=0.0, step=0.1, label_visibility="collapsed", placeholder="¥单价")
                with fc2: remark = st.text_input("备注", label_visibility="collapsed", placeholder="备注")
                with fc3: sup_file = st.file_uploader("附件", type=['pdf','jpg','xlsx'], label_visibility="collapsed", key=f"u_{pname}")
                with fc4: 
                    submitted = st.form_submit_button("提交", use_container_width=True)
                    if submitted:
                        if not closed:
                            if price > 0:
                                fdata = file_to_base64(sup_file)
                                my_history = [b for b in pinfo['bids'] if b['supplier'] == user]
                                is_duplicate = False
                                if my_history:
                                    last_bid = my_history[-1]
                                    last_fname = last_bid['file']['name'] if last_bid['file'] else None
                                    curr_fname = fdata['name'] if fdata else None
                                    if (last_bid['price'] == price and last_bid['remark'] == remark and last_fname == curr_fname):
                                        is_duplicate = True
                                
                                if is_duplicate:
                                    st.toast("⚠️ 报价未变更，已过滤重复提交", icon="🛡️")
                                else:
                                    pinfo['bids'].append({'supplier': user, 'price': price, 'remark': remark, 'file': fdata, 'time': now.strftime('%H:%M:%S'), 'datetime': now})
                                    st.toast("✅ 报价成功", icon="🎉")
                            else: st.toast("❌ 价格无效", icon="🚫")
                        else: st.error("已截止")
            st.markdown("<hr style='margin: 0.1rem 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

# --- 管理员界面 ---
def admin_dashboard():
    # 🔥🔥🔥 关键修复：申明使用全局变量，防止 UnboundLocalError 🔥🔥🔥
    global shared_data 
    
    st.sidebar.title("👮‍♂️ 总控")
    if st.sidebar.button("🔄 刷新数据", use_container_width=True): st.rerun()
    menu = st.sidebar.radio("菜单", ["项目管理", "供应商库", "监控中心"])
    if st.sidebar.button("退出系统"): st.session_state.clear(); st.rerun()

    if menu == "供应商库":
        st.subheader("🏢 供应商管理")
        with st.expander("➕ 登记新供应商", expanded=False):
            with st.form("add_sup_form"):
                st.caption("基本信息")
                c1, c2, c3 = st.columns(3)
                new_name = c1.text_input("供应商名称 (必填)", placeholder="企业全称")
                new_contact = c2.text_input("联系人", placeholder="姓名")
                new_job = c3.text_input("职位", placeholder="如: 销售经理")
                st.caption("详细信息")
                c4, c5, c6 = st.columns(3)
                new_phone = c4.text_input("电话", placeholder="手机/座机")
                new_type = c5.text_input("产品类型", placeholder="如: 光缆/机柜")
                new_addr = c6.text_input("地址", placeholder="办公地址")
                if st.form_submit_button("💾 保存录入", use_container_width=True):
                    if new_name:
                        if new_name not in shared_data["suppliers"]:
                            shared_data["suppliers"][new_name] = {"contact": new_contact, "phone": new_phone, "job": new_job, "type": new_type, "address": new_addr}
                            st.success(f"✅ 已添加: {new_name}"); st.rerun()
                        else: st.error("❌ 该供应商已存在")
                    else: st.error("⚠️ 供应商名称不能为空")

        st.markdown("---")
        st.subheader("📋 供应商名录")
        st.info("💡 提示：可直接修改下方表格内容，改完点击【保存所有修改】。")
        if shared_data["suppliers"]:
            df_source = pd.DataFrame.from_dict(shared_data["suppliers"], orient='index')
            required_cols = ["contact", "job", "phone", "type", "address"]
            for col in required_cols:
                if col not in df_source.columns: df_source[col] = ""
            edited_df = st.data_editor(df_source, column_config={"contact": "联系人", "job": "职位", "phone": "电话", "type": "产品类型", "address": "地址"}, use_container_width=True, key="sup_editor")
            
            if st.button("💾 保存所有修改", type="primary"):
                # 这里会写入 shared_data，有了 global 声明就不会报错了
                shared_data["suppliers"] = edited_df.to_dict(orient='index')
                st.toast("✅ 更新成功", icon="🎉"); st.rerun()
                
            st.divider()
            for name in list(shared_data["suppliers"].keys()):
                 with st.container():
                    col_info, col_del = st.columns([6, 1])
                    col_info.markdown(f"**{name}**")
                    if col_del.button("删除", key=f"del_sup_{name}"):
                        del shared_data["suppliers"][name]; st.rerun()
        else: st.info("暂无供应商数据")

    elif menu == "项目管理":
        st.subheader("📁 项目管理")
        with st.expander("➕ 新建项目", expanded=False):
            with st.form("new"):
                c1, c2, c3 = st.columns([1.5, 1, 1])
                n = c1.text_input("名称", placeholder="项目名", label_visibility="collapsed")
                d = c2.date_input("日期", datetime.now(), label_visibility="collapsed")
                t = c3.time_input("时间", datetime.strptime("17:00", "%H:%M").time(), label_visibility="collapsed")
                available_sups = list(shared_data.get("suppliers", {}).keys())
                if not available_sups:
                    st.error("⚠️ 请先在【供应商库】录入供应商！")
                    selected_sups = []
                else:
                    selected_sups = st.multiselect("选择供应商", available_sups, placeholder="请勾选参与报价的供应商")
                if st.form_submit_button("创建"):
                    if n and selected_sups:
                        pid = str(uuid.uuid4())[:8]
                        codes = {x: generate_random_code() for x in selected_sups}
                        shared_data["projects"][pid] = {"name": n, "deadline": f"{d} {t.strftime('%H:%M')}", "codes": codes, "products": {}}
                        st.rerun()
                    elif not n: st.error("请输入项目名称")
                    elif not selected_sups: st.error("请至少选择一个供应商")

        st.markdown("---")
        projs = sorted([p for p in shared_data["projects"].items() if 'deadline' in p[1]], key=lambda x: x[1]['deadline'], reverse=True)
        for pid, p in projs:
            with st.expander(f"📅 {p['deadline']} | {p['name']}", expanded=False):
                # 追加供应商
                with st.expander("➕ 追加供应商", expanded=False):
                    with st.form(f"append_sup_{pid}"):
                        all_global = list(shared_data["suppliers"].keys())
                        curr_sups = list(p['codes'].keys())
                        rem = [s for s in all_global if s not in curr_sups]
                        c_sel, c_new = st.columns(2)
                        sel_sup = c_sel.selectbox("从库中选", ["--请选择--"] + rem)
                        new_sup = c_new.text_input("或输入新供应商 (自动入库)", placeholder="临时新增名称")
                        if st.form_submit_button("立即添加"):
                            t_name = None
                            if new_sup:
                                t_name = new_sup.strip()
                                if t_name not in shared_data["suppliers"]:
                                    shared_data["suppliers"][t_name] = {"contact":"", "phone":"", "job":"", "type":"临时追加", "address":""}
                            elif sel_sup != "--请选择--": t_name = sel_sup
                            if t_name:
                                if t_name not in p['codes']:
                                    p['codes'][t_name] = generate_random_code()
                                    st.success(f"✅ 已添加 {t_name}"); st.rerun()
                                else: st.warning("已存在")
                            else: st.warning("无效操作")

                # 供应商授权列表 (支持删除)
                st.caption("🔑 供应商管理 (点击红色垃圾桶移除)")
                if p['codes']:
                    # 遍历并显示，增加删除按钮
                    for sup, code in list(p['codes'].items()):
                        c_code, c_del = st.columns([5, 1])
                        with c_code:
                            sub_c1, sub_c2 = st.columns([1, 2])
                            sub_c1.code(sup, language=None)
                            sub_c2.code(code, language=None)
                        if c_del.button("🗑️", key=f"rm_sup_{pid}_{sup}", help=f"移除 {sup}"):
                            del p['codes'][sup]
                            st.rerun()
                else: st.info("⚠️ 当前无供应商")
                
                st.markdown("<div style='margin-bottom: 10px'></div>", unsafe_allow_html=True)
                st.caption("📦 产品管理")
                for k, v in p['products'].items():
                    # 显示描述
                    desc_str = f"({v.get('desc')})" if v.get('desc') else ""
                    rc1, rc2 = st.columns([8, 1])
                    rc1.markdown(f"<div style='font-size:0.9em;'>• {k} {desc_str} (x{v['quantity']})</div>", unsafe_allow_html=True)
                    if rc2.button("✕", key=f"d{pid}{k}", help="删除"): 
                        del p['products'][k]; st.rerun()
                
                # 添加产品 (含描述字段)
                with st.form(f"add_{pid}", border=False):
                    ac1, ac2, ac3, ac4, ac5 = st.columns([2, 1, 2, 2, 1])
                    pn = ac1.text_input("产品", label_visibility="collapsed", placeholder="产品名")
                    pq = ac2.number_input("数量", min_value=1,

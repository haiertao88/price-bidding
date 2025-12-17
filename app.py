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
st.set_page_config(page_title="华脉招采平台", layout="wide")

# --- 🎨 CSS 样式深度定制 ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
        .stCode { font-size: 0.9em !important; margin-bottom: 0px !important; }
        div[data-testid="stCodeBlock"] > pre { padding: 0.4rem !important; border-radius: 4px !important; }
        section[data-testid="stFileUploader"] { padding: 0px !important; min-height: 0px !important; }
        section[data-testid="stFileUploader"] > div { padding-top: 5px !important; padding-bottom: 5px !important; }
        section[data-testid="stFileUploader"] small { display: none; }
        [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child { display: none; }
        [data-testid="stFileUploaderDropzoneInstructions"] > div:nth-child(2) small { display: none; }
        [data-testid="stFileUploader"] button { color: transparent !important; position: relative; min-width: 80px !important; }
        [data-testid="stFileUploader"] button::after {
            content: "📂 选择文件"; color: #31333F; position: absolute;
            left: 50%; top: 50%; transform: translate(-50%, -50%);
            font-size: 14px; white-space: nowrap;
        }
        section[data-testid="stFileUploader"] > div > div::before {
            content: "拖拽文件到此处 / 200MB内"; position: absolute;
            left: 10px; top: 50%; transform: translateY(-50%);
            font-size: 13px; color: #888; pointer-events: none; z-index: 1;
        }
        section[data-testid="stFileUploader"] > div { justify-content: flex-end; }
        .compact-card { border: 1px solid #eee; background-color: #fcfcfc; padding: 10px; border-radius: 6px; margin-bottom: 5px; }
        .stDataFrame { font-size: 0.85rem; }
        .prod-desc { font-size: 0.85em; color: #666; margin-left: 5px; font-style: italic;}
        .sup-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; background-color: #e6f3ff; color: #0068c9; border: 1px solid #cce5ff; font-size: 0.85rem; margin-right: 5px; margin-bottom: 5px; }
        .sup-info { font-size: 0.8em; color: #666; margin-left: 10px; }
        .file-tag {
            display: inline-block; background-color: #f0f2f6; color: #31333F;
            padding: 4px 10px; border-radius: 15px; border: 1px solid #dce0e6;
            margin-right: 8px; margin-bottom: 8px; text-decoration: none;
            font-size: 0.85rem; transition: all 0.2s;
        }
        .file-tag:hover { background-color: #e0e4eb; border-color: #cdd3dd; color: #0068c9; }
        .stButton>button:disabled { opacity: 0.6; cursor: not-allowed; }
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

# 数据结构自检 - 增强版
if isinstance(shared_data.get("suppliers"), list):
    old_list = shared_data["suppliers"]
    new_suppliers = {}
    for item in old_list:
        if isinstance(item, str) and item.strip():
            new_suppliers[item.strip()] = {"contact": "", "phone": "", "job": "", "type": "", "address": ""}
    shared_data["suppliers"] = new_suppliers

# 清理无效项目
invalid_pids = []
for pid, data in shared_data["projects"].items():
    if 'deadline' not in data or not isinstance(data.get('deadline'), str):
        invalid_pids.append(pid)
for pid in invalid_pids: 
    del shared_data["projects"][pid]

# --- 工具函数 ---
def generate_random_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def file_to_base64(uploaded_file, max_size=200*1024*1024):  # 200MB限制
    if uploaded_file is None: 
        return None
    # 检查文件大小
    file_size = uploaded_file.size
    if file_size > max_size:
        st.error(f"文件过大（{file_size/1024/1024:.1f}MB），最大支持200MB")
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        # 计算文件哈希（用于重复判断）
        file_hash = hashlib.md5(bytes_data).hexdigest()
        return {
            "name": uploaded_file.name, 
            "type": uploaded_file.type, 
            "data": b64,
            "size": file_size,
            "hash": file_hash
        }
    except Exception as e:
        st.error(f"文件处理失败: {str(e)}")
        return None

def get_file_hash(file_dict):
    """获取文件哈希（无文件返回空）"""
    return file_dict.get('hash', '') if file_dict else ''

def get_styled_download_tag(file_dict, supplier_name=""):
    if not file_dict: 
        return ""
    b64 = file_dict["data"]
    label = f"📎 {supplier_name} - {file_dict['name']}" if supplier_name else f"📎 {file_dict['name']}"
    href = f"""<a href="data:{file_dict['type']};base64,{b64}" download="{file_dict['name']}" class="file-tag" target="_blank">{label}</a>"""
    return href

def get_simple_download_link(file_dict, label="📄"):
    if not file_dict: 
        return ""
    b64 = file_dict["data"]
    display_text = f"{label} （华脉提供资料）: {file_dict['name']}"
    return f'<a href="data:{file_dict["type"]};base64,{b64}" download="{file_dict["name"]}" style="text-decoration:none; color:#0068c9; font-weight:bold; font-size:0.85em;">{display_text}</a>'

def parse_deadline(deadline_str):
    """安全解析截止时间"""
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(deadline_str, fmt)
        except:
            continue
    # 默认返回当前时间+1小时
    st.warning(f"截止时间格式错误: {deadline_str}，已重置为1小时后")
    return datetime.now() + timedelta(hours=1)

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
                    st.session_state.user_type = "admin"
                    st.session_state.user = u
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.experimental_rerun()
                else:
                    found = False
                    for pid, d in shared_data["projects"].items():
                        if u in d.get("codes", {}) and d["codes"][u] == p:
                            st.session_state.user_type = "supplier"
                            st.session_state.user = u
                            st.session_state.project_id = pid
                            if hasattr(st, 'rerun'):
                                st.rerun()
                            else:
                                st.experimental_rerun()
                            found = True
                            break
                    if not found: 
                        st.error("用户名或密码错误")

# --- 供应商界面 ---
def supplier_dashboard():
    user = st.session_state.get('user')
    pid = st.session_state.get('project_id')
    proj = shared_data["projects"].get(pid)
    
    if not user or not pid or not proj:
        st.error("会话失效，请重新登录")
        if st.button("返回登录页"):
            st.session_state.clear()
            if hasattr(st, 'rerun'):
                st.rerun()
            else:
                st.experimental_rerun()
        return
    
    # 安全解析截止时间
    deadline = parse_deadline(proj['deadline'])
    now = datetime.now()
    closed = now > deadline
    left = deadline - now if not closed else timedelta(0)

    # 页面头部
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1.2, 0.6, 0.6])
        c1.markdown(f"**👤 {user}**")
        c2.caption(f"项目: {proj['name']}")
        if closed: 
            c3.error("🚫 已截止")
        else: 
            c3.success(f"⏳ 剩余: {str(left).split('.')[0]}")
        if c4.button("🔄 刷新", help="获取最新数据"):
            if hasattr(st, 'rerun'):
                st.rerun()
            else:
                st.experimental_rerun()
        if c5.button("退出"):
            st.session_state.clear()
            if hasattr(st, 'rerun'):
                st.rerun()
            else:
                st.experimental_rerun()

    # 产品列表
    products = proj.get("products", {})
    if not products: 
        st.info("暂无产品")
        return
    
    # 最后15分钟提醒
    if not closed and timedelta(minutes=0) < left < timedelta(minutes=15): 
        st.warning("🔥 竞价最后阶段！")

    # 防止重复提交的锁
    if 'submit_lock' not in st.session_state:
        st.session_state.submit_lock = {}

    for pname, pinfo in products.items():
        with st.container():
            # 产品信息
            desc_text = pinfo.get('desc', '')
            desc_html = f"<span class='prod-desc'>({desc_text})</span>" if desc_text else ""
            st.markdown(f"""
            <div class="compact-card" style="display:flex; justify-content:space-between; align-items:center;">
                <span><b>📦 {pname}</b> {desc_html}</span>
                <small style='color:#666'>数量: {pinfo['quantity']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # 管理员提供的文件
            link = get_simple_download_link(pinfo.get('admin_file'))
            if link: 
                st.markdown(f"<div style='margin-top:-5px; margin-bottom:5px; font-size:0.8rem'>{link}</div>", unsafe_allow_html=True)

            # 报价表单
            with st.form(key=f"f_{pname}", border=False):
                fc1, fc2, fc3, fc4 = st.columns([1.5, 2, 2, 1])
                with fc1: 
                    price = st.number_input("单价", min_value=0.0, step=0.1, 
                                          label_visibility="collapsed", placeholder="¥单价")
                with fc2: 
                    remark = st.text_input("备注", label_visibility="collapsed", placeholder="备注")
                with fc3: 
                    sup_file = st.file_uploader("附件", type=['pdf','jpg','xlsx'], 
                                              label_visibility="collapsed", key=f"u_{pname}")
                with fc4: 
                    # 提交按钮状态控制
                    submit_disabled = closed or st.session_state.submit_lock.get(pname, False)
                    submitted = st.form_submit_button(
                        "提交" if not submit_disabled else "处理中...", 
                        use_container_width=True,
                        disabled=submit_disabled
                    )
                    
                    if submitted:
                        # 加锁防止重复提交
                        st.session_state.submit_lock[pname] = True
                        try:
                            if not closed:
                                if price > 0:
                                    fdata = file_to_base64(sup_file)
                                    # 增强版重复判断（包含文件哈希）
                                    my_history = [b for b in pinfo['bids'] if b['supplier'] == user]
                                    is_duplicate = False
                                    
                                    if my_history:
                                        last_bid = my_history[-1]
                                        last_price = last_bid.get('price', 0)
                                        last_remark = last_bid.get('remark', '')
                                        last_file_hash = get_file_hash(last_bid.get('file'))
                                        curr_file_hash = get_file_hash(fdata)
                                        
                                        if (last_price == price and 
                                            last_remark == remark and 
                                            last_file_hash == curr_file_hash):
                                            is_duplicate = True
                                    
                                    if is_duplicate:
                                        st.toast("⚠️ 报价未变更，系统已过滤重复提交", icon="🛡️")
                                    else:
                                        # 添加报价
                                        pinfo['bids'].append({
                                            'supplier': user, 
                                            'price': price, 
                                            'remark': remark, 
                                            'file': fdata, 
                                            'time': now.strftime('%H:%M:%S'), 
                                            'datetime': now
                                        })
                                        st.toast("✅ 报价成功", icon="🎉")
                                else: 
                                    st.toast("❌ 价格必须大于0", icon="🚫")
                            else: 
                                st.error("该项目报价已截止")
                        finally:
                            # 解锁
                            st.session_state.submit_lock[pname] = False
                            # 刷新页面
                            if hasattr(st, 'rerun'):
                                st.rerun()
                            else:
                                st.experimental_rerun()
            st.markdown("<hr style='margin: 0.1rem 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

# --- 管理员界面 ---
def admin_dashboard():
    global shared_data
    
    st.sidebar.title("👮‍♂️ 总控")
    if st.sidebar.button("🔄 刷新数据", use_container_width=True):
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()
    
    menu = st.sidebar.radio("菜单", ["项目管理", "供应商库", "监控中心"])
    if st.sidebar.button("退出系统"):
        st.session_state.clear()
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()

    # === 供应商库管理 ===
    if menu == "供应商库":
        st.subheader("🏢 供应商管理")
        
        # 添加新供应商
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
                
                submit_add = st.form_submit_button("💾 保存录入", use_container_width=True)
                if submit_add:
                    if new_name and new_name.strip():
                        new_name = new_name.strip()
                        if new_name not in shared_data["suppliers"]:
                            shared_data["suppliers"][new_name] = {
                                "contact": new_contact.strip() if new_contact else "",
                                "phone": new_phone.strip() if new_phone else "",
                                "job": new_job.strip() if new_job else "",
                                "type": new_type.strip() if new_type else "",
                                "address": new_addr.strip() if new_addr else ""
                            }
                            st.success(f"✅ 已添加: {new_name}")
                            if hasattr(st, 'rerun'):
                                st.rerun()
                            else:
                                st.experimental_rerun()
                        else: 
                            st.error("❌ 该供应商已存在")
                    else: 
                        st.error("⚠️ 供应商名称不能为空")

        st.markdown("---")
        st.subheader("📋 供应商名录")
        st.info("💡 提示：可直接修改下方表格内容，改完点击【保存所有修改】。")
        
        # 供应商列表编辑
        if shared_data["suppliers"]:
            df_source = pd.DataFrame.from_dict(shared_data["suppliers"], orient='index')
            required_cols = ["contact", "job", "phone", "type", "address"]
            for col in required_cols:
                if col not in df_source.columns: 
                    df_source[col] = ""
            
            edited_df = st.data_editor(
                df_source, 
                column_config={
                    "contact": "联系人", 
                    "job": "职位", 
                    "phone": "电话", 
                    "type": "产品类型", 
                    "address": "地址"
                },
                use_container_width=True, 
                key="sup_editor"
            )
            
            if st.button("💾 保存所有修改", type="primary"):
                shared_data["suppliers"] = edited_df.to_dict(orient='index')
                st.toast("✅ 更新成功", icon="🎉")
                if hasattr(st, 'rerun'):
                    st.rerun()
                else:
                    st.experimental_rerun()
            
            st.divider()
            st.caption("🗑️ 删除操作")
            # 分页显示删除按钮（避免过多按钮）
            sup_names = list(shared_data["suppliers"].keys())
            cols = st.columns(4)
            for idx, name in enumerate(sup_names):
                with cols[idx % 4]:
                    if st.button(f"删除 {name}", key=f"del_sup_{name}"):
                        del shared_data["suppliers"][name]
                        if hasattr(st, 'rerun'):
                            st.rerun()
                        else:
                            st.experimental_rerun()
        else: 
            st.info("暂无供应商数据")

    # === 项目管理 ===
    elif menu == "项目管理":
        st.subheader("📁 项目管理")
        
        # 新建项目
        with st.expander("➕ 新建项目", expanded=False):
            with st.form("new_project_form"):
                c1, c2, c3 = st.columns([1.5, 1, 1])
                proj_name = c1.text_input("项目名称", placeholder="请输入项目名称")
                proj_date = c2.date_input("截止日期", datetime.now())
                proj_time = c3.time_input("截止时间", datetime.strptime("17:00", "%H:%M").time())
                
                # 供应商选择
                available_sups = list(shared_data.get("suppliers", {}).keys())
                if not available_sups:
                    st.error("⚠️ 请先在【供应商库】录入供应商！")
                    selected_sups = []
                else:
                    selected_sups = st.multiselect(
                        "选择参与报价的供应商", 
                        available_sups, 
                        placeholder="请勾选供应商"
                    )
                
                submit_create = st.form_submit_button("🚀 创建项目", use_container_width=True)
                if submit_create:
                    if proj_name and selected_sups:
                        # 生成项目ID
                        pid = str(uuid.uuid4())[:8]
                        # 生成供应商密码
                        sup_codes = {x: generate_random_code() for x in selected_sups}
                        # 组合截止时间
                        deadline_str = f"{proj_date} {proj_time.strftime('%H:%M')}"
                        # 创建项目
                        shared_data["projects"][pid] = {
                            "name": proj_name,
                            "deadline": deadline_str,
                            "codes": sup_codes,
                            "products": {}
                        }
                        st.success(f"✅ 项目创建成功: {proj_name}")
                        if hasattr(st, 'rerun'):
                            st.rerun()
                        else:
                            st.experimental_rerun()
                    elif not proj_name:
                        st.error("⚠️ 请输入项目名称")
                    elif not selected_sups:
                        st.error("⚠️ 请至少选择一个供应商")

        st.markdown("---")
        
        # 现有项目管理
        projs = sorted(
            [p for p in shared_data["projects"].items() if 'deadline' in p[1]],
            key=lambda x: x[1]['deadline'], 
            reverse=True
        )
        
        if not projs:
            st.info("暂无项目数据")
            return
        
        for pid, p in projs:
            with st.expander(f"📅 {p['deadline']} | {p['name']}", expanded=False):
                # 1. 追加供应商
                with st.expander("➕ 追加供应商", expanded=False):
                    with st.form(f"append_sup_form_{pid}"):
                        all_global = list(shared_data["suppliers"].keys())
                        curr_sups = list(p['codes'].keys())
                        rem_sups = [s for s in all_global if s not in curr_sups]
                        
                        c_sel, c_new = st.columns(2)
                        sel_sup = c_sel.selectbox("从库中选择", ["--请选择--"] + rem_sups, key=f"sel_{pid}")
                        new_sup = c_new.text_input("或输入新供应商名称", placeholder="临时新增", key=f"new_{pid}")
                        
                        submit_append = st.form_submit_button("✅ 确认添加", use_container_width=True)
                        if submit_append:
                            t_name = None
                            if new_sup and new_sup.strip():
                                t_name = new_sup.strip()
                                # 自动入库
                                if t_name not in shared_data["suppliers"]:
                                    shared_data["suppliers"][t_name] = {
                                        "contact": "", "phone": "", "job": "", 
                                        "type": "临时追加", "address": ""
                                    }
                            elif sel_sup != "--请选择--":
                                t_name = sel_sup
                            
                            if t_name:
                                if t_name not in p['codes']:
                                    p['codes'][t_name] = generate_random_code()
                                    st.success(f"✅ 已添加供应商: {t_name}")
                                    if hasattr(st, 'rerun'):
                                        st.rerun()
                                    else:
                                        st.experimental_rerun()
                                else:
                                    st.warning("⚠️ 该供应商已在项目中")
                            else:
                                st.warning("⚠️ 请选择或输入供应商名称")

                # 2. 供应商管理（含移除）
                st.caption("🔑 供应商列表 (用户名/密码)")
                if p['codes']:
                    # 表头
                    st.markdown("""
                    <div style="display:flex; color:#666; font-size:0.8em; margin-bottom:5px; padding:5px; background:#f8f9fa; border-radius:4px;">
                        <div style="flex:1.5;">供应商名称</div>
                        <div style="flex:2;">登录用户名</div>
                        <div style="flex:2;">登录密码</div>
                        <div style="flex:0.8;">操作</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 供应商列表
                    for sup, code in list(p['codes'].items()):
                        c1, c2, c3, c4 = st.columns([1.5, 2, 2, 0.8])
                        with c1: 
                            st.markdown(f"**{sup}**")
                        with c2: 
                            st.code(sup, language=None)
                        with c3: 
                            st.code(code, language=None)
                        with c4:
                            if st.button("🗑️", key=f"rm_{pid}_{sup}", help="移除该供应商"):
                                del p['codes'][sup]
                                if hasattr(st, 'rerun'):
                                    st.rerun()
                                else:
                                    st.experimental_rerun()
                else:
                    st.info("⚠️ 该项目暂无供应商")
                
                st.markdown("<div style='margin:10px 0;'></div>", unsafe_allow_html=True)
                
                # 3. 产品管理
                st.caption("📦 产品列表")
                if p.get('products'):
                    for k, v in p['products'].items():
                        desc_str = f"({v.get('desc')})" if v.get('desc') else ""
                        rc1, rc2 = st.columns([8, 1])
                        rc1.markdown(f"""
                        <div style='font-size:0.9em; padding:5px; border-bottom:1px solid #eee;'>
                            • {k} {desc_str} (数量: {v['quantity']})
                        </div>
                        """, unsafe_allow_html=True)
                        if rc2.button("✕", key=f"d{pid}{k}", help="删除该产品"): 
                            del p['products'][k]
                            if hasattr(st, 'rerun'):
                                st.rerun()
                            else:
                                st.experimental_rerun()
                else:
                    st.info("暂无产品，请添加")
                
                # 添加产品表单
                st.caption("➕ 添加产品")
                with st.form(f"add_product_form_{pid}", border=False):
                    ac1, ac2, ac3, ac4, ac5 = st.columns([2, 1, 2, 2, 1])
                    pn = ac1.text_input("产品名称", label_visibility="collapsed", placeholder="如: 单模光缆")
                    pq = ac2.number_input("数量", min_value=1, value=1, label_visibility="collapsed")
                    pd = ac3.text_input("产品描述", label_visibility="collapsed", placeholder="规格/技术要求")
                    pf = ac4.file_uploader("上传规格文件", label_visibility="collapsed", key=f"file_{pid}")
                    submit_add_prod = ac5.form_submit_button("添加")
                    
                    if submit_add_prod:
                        if pn and pn.strip() and pn not in p['products']:
                            p['products'][pn.strip()] = {
                                "quantity": pq,
                                "desc": pd.strip() if pd else "",
                                "bids": [],
                                "admin_file": file_to_base64(pf)
                            }
                            if hasattr(st, 'rerun'):
                                st.rerun()
                            else:
                                st.experimental_rerun()
                        elif not pn.strip():
                            st.warning("⚠️ 产品名称不能为空")
                        else:
                            st.warning(f"⚠️ 产品 {pn} 已存在")
                
                # 删除项目按钮
                col_del, _ = st.columns([1, 9])
                if col_del.button(
                    "🗑️ 删除该项目", 
                    key=f"del_proj_{pid}",
                    type="secondary"
                ):
                    del shared_data["projects"][pid]
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.experimental_rerun()

    # === 监控中心 ===
    elif menu == "监控中心":
        st.subheader("📊 报价监控中心")
        
        # 项目选择
        proj_options = {
            k: f"{v['deadline']} - {v['name']}" 
            for k, v in shared_data["projects"].items() 
            if 'deadline' in v and 'products' in v
        }
        
        if not proj_options:
            st.warning("暂无可用项目数据")
            return
        
        selected_proj_id = st.selectbox(
            "选择要查看的项目",
            list(proj_options.keys()),
            format_func=lambda x: proj_options[x]
        )
        
        selected_proj = shared_data["projects"][selected_proj_id]
        
        # 比价总览
        st.markdown("### 🏆 报价汇总")
        summary_data = []
        
        for prod_name, prod_info in selected_proj['products'].items():
            bids = prod_info.get('bids', [])
            if bids:
                # 提取有效报价
                valid_bids = [b for b in bids if b.get('price', 0) > 0]
                if valid_bids:
                    prices = [b['price'] for b in valid_bids]
                    min_price = min(prices)
                    max_price = max(prices)
                    # 最优供应商
                    best_suppliers = [b['supplier'] for b in valid_bids if b['price'] == min_price]
                    best_suppliers_str = ", ".join(set(best_suppliers))
                    # 价差计算
                    price_diff = (max_price - min_price) / min_price * 100 if min_price > 0 else 0
                    # 总价计算
                    min_total = min_price * prod_info['quantity']
                    max_total = max_price * prod_info['quantity']
                    
                    summary_data.append({
                        "产品名称": prod_name,
                        "数量": prod_info['quantity'],
                        "最低单价": f"¥{min_price:.2f}",
                        "最低总价": f"¥{min_total:.2f}",
                        "最高单价": f"¥{max_price:.2f}",
                        "最高总价": f"¥{max_total:.2f}",
                        "最优供应商": best_suppliers_str,
                        "价差幅度": f"{price_diff:.1f}%",
                        "有效报价数": len(valid_bids)
                    })
                else:
                    summary_data.append({
                        "产品名称": prod_name,
                        "数量": prod_info['quantity'],
                        "最低单价": "-",
                        "最低总价": "-",
                        "最高单价": "-",
                        "最高总价": "-",
                        "最优供应商": "-",
                        "价差幅度": "-",
                        "有效报价数": 0
                    })
            else:
                summary_data.append({
                    "产品名称": prod_name,
                    "数量": prod_info['quantity'],
                    "最低单价": "-",
                    "最低总价": "-",
                    "最高单价": "-",
                    "最高总价": "-",
                    "最优供应商": "-",
                    "价差幅度": "-",
                    "有效报价数": 0
                })
        
        # 显示汇总表格
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            # 导出Excel
            all_detail_data = []
            for prod_name, prod_info in selected_proj['products'].items():
                for bid in prod_info.get('bids', []):
                    price = bid.get('price', 0)
                    total = price * prod_info['quantity']
                    all_detail_data.append({
                        "项目名称": selected_proj['name'],
                        "产品名称": prod_name,
                        "数量": prod_info['quantity'],
                        "供应商": bid.get('supplier', ''),
                        "单价": price,
                        "总价": total,
                        "备注": bid.get('remark', ''),
                        "报价时间": bid.get('time', ''),
                        "是否有附件": "是" if bid.get('file') else "否"
                    })
            
            if all_detail_data:
                # 创建Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 汇总表
                    summary_df.to_excel(writer, sheet_name='报价汇总', index=False)
                    # 明细表
                    detail_df = pd.DataFrame(all_detail_data)
                    detail_df.to_excel(writer, sheet_name='报价明细', index=False)
                
                # 下载按钮
                st.download_button(
                    label="📥 导出Excel报表",
                    data=output.getvalue(),
                    file_name=f"华脉招采-{selected_proj['name']}-报价明细.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
        
        # 详细报价分析
        st.markdown("### 📈 详细报价分析")
        
        for prod_name, prod_info in selected_proj['products'].items():
            st.markdown(f"#### 📦 {prod_name} (数量: {prod_info['quantity']})")
            
            bids = prod_info.get('bids', [])
            if bids:
                # 准备图表数据
                chart_data = []
                table_data = []
                
                for bid in bids:
                    bid_time = bid.get('datetime', datetime.now())
                    supplier = bid.get('supplier', '未知')
                    price = bid.get('price', 0)
                    total = price * prod_info['quantity']
                    remark = bid.get('remark', '')
                    bid_time_str = bid.get('time', '')
                    has_file = "✅" if bid.get('file') else "❌"
                    
                    chart_data.append({
                        "时间": bid_time,
                        "单价": price,
                        "供应商": supplier
                    })
                    
                    table_data.append({
                        "供应商": supplier,
                        "单价(¥)": f"{price:.2f}",
                        "总价(¥)": f"{total:.2f}",
                        "报价时间": bid_time_str,
                        "备注": remark,
                        "附件": has_file
                    })
                
                # 双列布局：图表 + 表格
                col1, col2 = st.columns(2)
                
                with col1:
                    # 报价趋势图
                    if chart_data:
                        chart_df = pd.DataFrame(chart_data)
                        st.line_chart(
                            chart_df,
                            x='时间',
                            y='单价',
                            color='供应商',
                            height=250,
                            use_container_width=True
                        )
                
                with col2:
                    # 报价明细表
                    st.dataframe(
                        table_data,
                        use_container_width=True,
                        hide_index=True,
                        height=250
                    )
                
                # 附件下载
                file_tags = []
                for bid in bids:
                    if bid.get('file'):
                        file_tag = get_styled_download_tag(bid['file'], bid['supplier'])
                        if file_tag:
                            file_tags.append(file_tag)
                
                if file_tags:
                    st.markdown("##### 📎 供应商附件")
                    st.markdown("".join(file_tags), unsafe_allow_html=True)
            else:
                st.info("该产品暂无报价数据")
            
            st.divider()

# --- 主程序入口 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

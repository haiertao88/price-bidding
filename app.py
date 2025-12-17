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

# --- 全局数据初始化（核心修复：确保数据结构绝对安全）---
@st.cache_resource
def init_global_data():
    """初始化全局数据，确保所有键都存在且类型正确"""
    return {
        "projects": {},  # 项目字典：{项目ID: {name, deadline, codes, products}}
        "suppliers": {   # 供应商字典：{供应商名称: {contact, phone, job, type, address}}
            "GYSA": {"contact": "张经理", "phone": "13800138000", "job": "销售总监", "type": "光纤光缆", "address": "江苏省南京市江宁区xxx号"},
            "GYSB": {"contact": "李工", "phone": "13900139000", "job": "技术支持", "type": "网络机柜", "address": "江苏省苏州市工业园区xxx号"},
            "GYSC": {"contact": "王总", "phone": "13700137000", "job": "总经理", "type": "综合布线", "address": "上海市浦东新区xxx号"}
        }
    }

# 全局数据实例（确保整个程序共用一份）
global_data = init_global_data()

# --- 工具函数 ---
def generate_random_code(length=6):
    """生成随机数字验证码"""
    return ''.join(random.choices(string.digits, k=length))

def file_to_base64(uploaded_file, max_size=200*1024*1024):
    """将上传文件转为base64，包含大小限制和哈希计算"""
    if uploaded_file is None:
        return None
    
    # 检查文件大小（200MB限制）
    file_size = uploaded_file.size
    if file_size > max_size:
        st.error(f"文件过大（{file_size/1024/1024:.1f}MB），最大支持200MB")
        return None
    
    try:
        bytes_data = uploaded_file.getvalue()
        b64_encoded = base64.b64encode(bytes_data).decode('utf-8')
        # 计算文件哈希（用于重复提交判断）
        file_hash = hashlib.md5(bytes_data).hexdigest()
        
        return {
            "name": uploaded_file.name,
            "type": uploaded_file.type,
            "data": b64_encoded,
            "size": file_size,
            "hash": file_hash
        }
    except Exception as e:
        st.error(f"文件处理失败：{str(e)}")
        return None

def get_file_hash(file_dict):
    """获取文件哈希（无文件返回空字符串）"""
    return file_dict.get('hash', '') if isinstance(file_dict, dict) else ''

def get_styled_download_tag(file_dict, supplier_name=""):
    """生成带样式的文件下载标签"""
    if not isinstance(file_dict, dict) or not file_dict.get('data'):
        return ""
    
    b64_data = file_dict["data"]
    display_label = f"📎 {supplier_name} - {file_dict['name']}" if supplier_name else f"📎 {file_dict['name']}"
    return f"""
    <a href="data:{file_dict['type']};base64,{b64_data}" download="{file_dict['name']}" class="file-tag" target="_blank">
        {display_label}
    </a>
    """

def get_simple_download_link(file_dict, label="📄"):
    """生成简单的下载链接"""
    if not isinstance(file_dict, dict) or not file_dict.get('data'):
        return ""
    
    b64_data = file_dict["data"]
    display_text = f"{label} （华脉提供资料）: {file_dict['name']}"
    return f"""
    <a href="data:{file_dict['type']};base64,{b64_data}" download="{file_dict['name']}" 
       style="text-decoration:none; color:#0068c9; font-weight:bold; font-size:0.85em;">
        {display_text}
    </a>
    """

def safe_parse_deadline(deadline_str):
    """安全解析截止时间，兼容多种格式"""
    if not isinstance(deadline_str, str):
        st.warning("截止时间格式错误，已重置为1小时后")
        return datetime.now() + timedelta(hours=1)
    
    # 支持的时间格式列表
    supported_formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    
    for fmt in supported_formats:
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue
    
    # 所有格式都不匹配时的兜底
    st.warning(f"截止时间 {deadline_str} 格式错误，已重置为1小时后")
    return datetime.now() + timedelta(hours=1)

# --- 登录页面 ---
def render_login_page():
    """渲染登录页面"""
    st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>🔐 华脉招采平台</h3>", unsafe_allow_html=True)
    
    # 居中登录框
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input(
                "用户名",
                label_visibility="collapsed",
                placeholder="请输入用户名"
            ).strip()
            
            password = st.text_input(
                "密码",
                type="password",
                label_visibility="collapsed",
                placeholder="请输入密码"
            ).strip()
            
            if st.button("登录", type="primary", use_container_width=True):
                # 管理员登录验证
                if username == "HUAMAI" and password == "HUAMAI888":
                    st.session_state["user_type"] = "admin"
                    st.session_state["user"] = username
                    st.rerun()
                
                # 供应商登录验证
                else:
                    login_success = False
                    for project_id, project_data in global_data["projects"].items():
                        supplier_codes = project_data.get("codes", {})
                        if username in supplier_codes and supplier_codes[username] == password:
                            st.session_state["user_type"] = "supplier"
                            st.session_state["user"] = username
                            st.session_state["project_id"] = project_id
                            login_success = True
                            st.rerun()
                            break
                    
                    if not login_success:
                        st.error("用户名或密码错误，请重试")

# --- 供应商端页面 ---
def render_supplier_dashboard():
    """渲染供应商报价页面"""
    # 验证会话有效性
    required_session_keys = ["user", "project_id", "user_type"]
    for key in required_session_keys:
        if key not in st.session_state:
            st.error("会话已失效，请重新登录")
            if st.button("返回登录页"):
                st.session_state.clear()
                st.rerun()
            return
    
    # 获取会话数据
    supplier_name = st.session_state["user"]
    project_id = st.session_state["project_id"]
    project_data = global_data["projects"].get(project_id)
    
    # 验证项目存在性
    if not project_data:
        st.error("当前项目不存在或已被删除")
        if st.button("返回登录页"):
            st.session_state.clear()
            st.rerun()
        return
    
    # 解析截止时间
    deadline = safe_parse_deadline(project_data.get("deadline", ""))
    now = datetime.now()
    is_closed = now > deadline
    time_remaining = deadline - now if not is_closed else timedelta(0)
    
    # 页面头部信息
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 1.2, 0.6, 0.6])
        col1.markdown(f"**👤 {supplier_name}**")
        col2.caption(f"项目：{project_data.get('name', '未知项目')}")
        
        if is_closed:
            col3.error("🚫 报价已截止")
        else:
            col3.success(f"⏳ 剩余：{str(time_remaining).split('.')[0]}")
        
        if col4.button("🔄 刷新", help="获取最新数据"):
            st.rerun()
        
        if col5.button("退出"):
            st.session_state.clear()
            st.rerun()
    
    # 最后15分钟提醒
    if not is_closed and timedelta(minutes=0) < time_remaining < timedelta(minutes=15):
        st.warning("🔥 报价即将截止，请尽快提交！")
    
    # 获取产品列表
    products = project_data.get("products", {})
    if not products:
        st.info("当前项目暂无可报价产品")
        return
    
    # 初始化提交锁（防止重复提交）
    if "submit_lock" not in st.session_state:
        st.session_state["submit_lock"] = {}
    
    # 渲染产品报价表单
    for product_name, product_info in products.items():
        with st.container():
            # 产品信息卡片
            product_desc = product_info.get("desc", "")
            desc_html = f"<span class='prod-desc'>({product_desc})</span>" if product_desc else ""
            st.markdown(f"""
                <div class="compact-card" style="display:flex; justify-content:space-between; align-items:center;">
                    <span><b>📦 {product_name}</b> {desc_html}</span>
                    <small style='color:#666'>数量：{product_info['quantity']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            # 管理员提供的文件链接
            admin_file = product_info.get("admin_file")
            if admin_file:
                download_link = get_simple_download_link(admin_file)
                st.markdown(f"""
                    <div style='margin-top:-5px; margin-bottom:5px; font-size:0.8rem'>
                        {download_link}
                    </div>
                """, unsafe_allow_html=True)
            
            # 报价表单
            with st.form(key=f"quote_form_{product_name}", border=False):
                fc1, fc2, fc3, fc4 = st.columns([1.5, 2, 2, 1])
                
                with fc1:
                    quote_price = st.number_input(
                        "单价",
                        min_value=0.0,
                        step=0.1,
                        label_visibility="collapsed",
                        placeholder="¥ 请输入单价"
                    )
                
                with fc2:
                    quote_remark = st.text_input(
                        "备注",
                        label_visibility="collapsed",
                        placeholder="输入报价备注（选填）"
                    ).strip()
                
                with fc3:
                    quote_file = st.file_uploader(
                        "附件",
                        type=["pdf", "jpg", "jpeg", "png", "xlsx", "xls"],
                        label_visibility="collapsed",
                        key=f"file_upload_{product_name}"
                    )
                
                with fc4:
                    # 控制提交按钮状态
                    submit_disabled = is_closed or st.session_state["submit_lock"].get(product_name, False)
                    submit_label = "提交" if not submit_disabled else "处理中..."
                    submit_clicked = st.form_submit_button(
                        submit_label,
                        use_container_width=True,
                        disabled=submit_disabled
                    )
                
                # 表单提交逻辑
                if submit_clicked:
                    # 加锁防止重复提交
                    st.session_state["submit_lock"][product_name] = True
                    
                    try:
                        if is_closed:
                            st.error("❌ 报价已截止，无法提交")
                        elif quote_price <= 0:
                            st.error("❌ 单价必须大于0，请重新输入")
                        else:
                            # 处理上传文件
                            file_data = file_to_base64(quote_file)
                            
                            # 检查是否为重复提交（价格+备注+文件哈希都相同）
                            bid_history = [b for b in product_info.get("bids", []) if b.get("supplier") == supplier_name]
                            is_duplicate = False
                            
                            if bid_history:
                                last_bid = bid_history[-1]
                                last_price = last_bid.get("price", 0)
                                last_remark = last_bid.get("remark", "")
                                last_file_hash = get_file_hash(last_bid.get("file"))
                                curr_file_hash = get_file_hash(file_data)
                                
                                if (last_price == quote_price and
                                    last_remark == quote_remark and
                                    last_file_hash == curr_file_hash):
                                    is_duplicate = True
                            
                            if is_duplicate:
                                st.warning("⚠️ 报价信息未变更，已过滤重复提交")
                            else:
                                # 添加新报价
                                new_bid = {
                                    "supplier": supplier_name,
                                    "price": quote_price,
                                    "remark": quote_remark,
                                    "file": file_data,
                                    "time": now.strftime("%H:%M:%S"),
                                    "datetime": now
                                }
                                
                                # 确保bids列表存在
                                if "bids" not in product_info:
                                    product_info["bids"] = []
                                
                                product_info["bids"].append(new_bid)
                                st.success("✅ 报价提交成功！")
                    
                    finally:
                        # 解锁
                        st.session_state["submit_lock"][product_name] = False
                        st.rerun()
        
        # 分隔线
        st.markdown("<hr style='margin: 0.1rem 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

# --- 管理员端页面 ---
def render_admin_dashboard():
    """渲染管理员控制台（核心修复：全局变量作用域+变量初始化）"""
    # 侧边栏菜单
    st.sidebar.title("👮‍♂️ 管理员控制台")
    
    if st.sidebar.button("🔄 刷新数据", use_container_width=True):
        st.rerun()
    
    menu_option = st.sidebar.radio(
        "功能菜单",
        ["项目管理", "供应商库", "监控中心"]
    )
    
    if st.sidebar.button("🚪 退出系统", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    # ========== 供应商库管理 ==========
    if menu_option == "供应商库":
        st.subheader("🏢 供应商库管理")
        
        # 添加新供应商
        with st.expander("➕ 新增供应商", expanded=False):
            with st.form("add_supplier_form", border=True):
                st.caption("基本信息")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_sup_name = st.text_input("供应商名称 *", placeholder="请输入企业全称").strip()
                
                with col2:
                    new_sup_contact = st.text_input("联系人", placeholder="请输入联系人姓名").strip()
                
                with col3:
                    new_sup_job = st.text_input("职位", placeholder="如：销售经理").strip()
                
                st.caption("详细信息")
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    new_sup_phone = st.text_input("联系电话", placeholder="手机/座机").strip()
                
                with col5:
                    new_sup_type = st.text_input("产品类型", placeholder="如：光纤光缆").strip()
                
                with col6:
                    new_sup_address = st.text_input("办公地址", placeholder="详细地址").strip()
                
                # 提交按钮
                if st.form_submit_button("💾 保存供应商", type="primary"):
                    if not new_sup_name:
                        st.error("⚠️ 供应商名称不能为空")
                    elif new_sup_name in global_data["suppliers"]:
                        st.error(f"⚠️ 供应商 {new_sup_name} 已存在")
                    else:
                        # 添加新供应商
                        global_data["suppliers"][new_sup_name] = {
                            "contact": new_sup_contact,
                            "phone": new_sup_phone,
                            "job": new_sup_job,
                            "type": new_sup_type,
                            "address": new_sup_address
                        }
                        st.success(f"✅ 供应商 {new_sup_name} 添加成功！")
                        st.rerun()
        
        st.markdown("---")
        
        # 供应商列表编辑
        st.subheader("📋 供应商名录")
        st.info("💡 可直接编辑表格内容，修改后点击【保存所有修改】按钮生效")
        
        # 确保suppliers始终是字典（核心修复）
        suppliers_dict = global_data.get("suppliers", {})
        if not isinstance(suppliers_dict, dict):
            global_data["suppliers"] = {}
            suppliers_dict = {}
        
        # 渲染供应商表格
        if suppliers_dict:
            # 转换为DataFrame（确保列完整）
            supplier_df = pd.DataFrame.from_dict(suppliers_dict, orient="index")
            
            # 补充缺失列（核心修复）
            required_columns = ["contact", "phone", "job", "type", "address"]
            for col in required_columns:
                if col not in supplier_df.columns:
                    supplier_df[col] = ""
            
            # 重命名列
            supplier_df.rename(
                columns={
                    "contact": "联系人",
                    "phone": "联系电话",
                    "job": "职位",
                    "type": "产品类型",
                    "address": "办公地址"
                },
                inplace=True
            )
            
            # 可编辑表格
            edited_df = st.data_editor(
                supplier_df,
                use_container_width=True,
                num_rows="dynamic",
                key="supplier_editor"
            )
            
            # 保存修改
            if st.button("💾 保存所有修改", type="primary"):
                # 转换回字典
                edited_dict = edited_df.rename(
                    columns={
                        "联系人": "contact",
                        "联系电话": "phone",
                        "职位": "job",
                        "产品类型": "type",
                        "办公地址": "address"
                    }
                ).to_dict(orient="index")
                
                # 更新全局数据
                global_data["suppliers"] = edited_dict
                st.success("✅ 供应商数据更新成功！")
                st.rerun()
            
            # 删除供应商
            st.markdown("---")
            st.subheader("🗑️ 供应商删除")
            col_del = st.columns(4)
            for idx, (sup_name, _) in enumerate(suppliers_dict.items()):
                with col_del[idx % 4]:
                    if st.button(f"删除 {sup_name}", key=f"del_sup_{sup_name}"):
                        del global_data["suppliers"][sup_name]
                        st.success(f"✅ 已删除供应商 {sup_name}")
                        st.rerun()
        else:
            st.info("📭 暂无供应商数据，请先添加")
    
    # ========== 项目管理 ==========
    elif menu_option == "项目管理":
        st.subheader("📁 项目管理")
        
        # 新建项目
        with st.expander("➕ 新建项目", expanded=False):
            with st.form("create_project_form", border=True):
                col1, col2, col3 = st.columns([1.5, 1, 1])
                
                with col1:
                    project_name = st.text_input("项目名称 *", placeholder="请输入项目名称").strip()
                
                with col2:
                    project_deadline_date = st.date_input("截止日期 *", value=datetime.now())
                
                with col3:
                    project_deadline_time = st.time_input("截止时间 *", value=datetime.strptime("17:00", "%H:%M").time())
                
                # 供应商选择
                available_suppliers = list(global_data["suppliers"].keys())
                if not available_suppliers:
                    st.error("⚠️ 请先在【供应商库】添加供应商！")
                    selected_suppliers = []
                else:
                    selected_suppliers = st.multiselect(
                        "参与报价的供应商 *",
                        options=available_suppliers,
                        placeholder="请选择至少一个供应商"
                    )
                
                # 提交创建
                if st.form_submit_button("🚀 创建项目", type="primary"):
                    if not project_name:
                        st.error("⚠️ 项目名称不能为空")
                    elif not selected_suppliers:
                        st.error("⚠️ 请至少选择一个供应商")
                    else:
                        # 生成项目ID和供应商验证码
                        project_id = str(uuid.uuid4())[:8]
                        supplier_codes = {sup: generate_random_code() for sup in selected_suppliers}
                        deadline_str = f"{project_deadline_date} {project_deadline_time.strftime('%H:%M')}"
                        
                        # 创建项目
                        global_data["projects"][project_id] = {
                            "name": project_name,
                            "deadline": deadline_str,
                            "codes": supplier_codes,
                            "products": {}
                        }
                        
                        st.success(f"✅ 项目 {project_name} 创建成功！")
                        st.rerun()
        
        st.markdown("---")
        
        # 现有项目管理
        projects = global_data.get("projects", {})
        if not projects:
            st.info("📭 暂无项目数据，请先创建")
            return
        
        # 按截止时间排序
        sorted_projects = sorted(
            projects.items(),
            key=lambda x: x[1]["deadline"],
            reverse=True
        )
        
        for project_id, project_data in sorted_projects:
            with st.expander(f"📅 {project_data['deadline']} | {project_data['name']}", expanded=False):
                # 追加供应商
                with st.expander("➕ 追加供应商", expanded=False):
                    with st.form(f"append_supplier_form_{project_id}", border=False):
                        current_suppliers = list(project_data.get("codes", {}).keys())
                        all_suppliers = list(global_data["suppliers"].keys())
                        remaining_suppliers = [s for s in all_suppliers if s not in current_suppliers]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            select_supplier = st.selectbox(
                                "从库中选择",
                                options=["--请选择--"] + remaining_suppliers,
                                key=f"select_sup_{project_id}"
                            )
                        
                        with col2:
                            new_supplier = st.text_input("或新增供应商", placeholder="临时添加供应商名称").strip()
                        
                        if st.form_submit_button("✅ 确认添加"):
                            target_supplier = None
                            
                            # 处理选择的供应商
                            if select_supplier != "--请选择--":
                                target_supplier = select_supplier
                            
                            # 处理新增供应商
                            elif new_supplier:
                                target_supplier = new_supplier
                                # 自动添加到供应商库
                                if target_supplier not in global_data["suppliers"]:
                                    global_data["suppliers"][target_supplier] = {
                                        "contact": "",
                                        "phone": "",
                                        "job": "",
                                        "type": "临时追加",
                                        "address": ""
                                    }
                            
                            # 验证并添加
                            if target_supplier:
                                if target_supplier in current_suppliers:
                                    st.warning(f"⚠️ 供应商 {target_supplier} 已在项目中")
                                else:
                                    project_data["codes"][target_supplier] = generate_random_code()
                                    st.success(f"✅ 已添加供应商 {target_supplier}")
                                    st.rerun()
                            else:
                                st.warning("⚠️ 请选择或输入供应商名称")
                
                # 供应商列表（含账号密码）
                st.caption("🔑 项目供应商账号信息")
                supplier_codes = project_data.get("codes", {})
                
                if supplier_codes:
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
                    for sup_name, sup_code in supplier_codes.items():
                        col1, col2, col3, col4 = st.columns([1.5, 2, 2, 0.8])
                        with col1:
                            st.markdown(f"**{sup_name}**")
                        with col2:
                            st.code(sup_name, language=None)
                        with col3:
                            st.code(sup_code, language=None)
                        with col4:
                            if st.button("🗑️", key=f"rm_sup_{project_id}_{sup_name}", help="移除供应商"):
                                del project_data["codes"][sup_name]
                                st.success(f"✅ 已移除供应商 {sup_name}")
                                st.rerun()
                else:
                    st.info("⚠️ 该项目暂无供应商")
                
                st.markdown("<div style='margin:10px 0;'></div>", unsafe_allow_html=True)
                
                # 产品管理
                st.caption("📦 产品列表")
                products = project_data.get("products", {})
                
                if products:
                    for prod_name, prod_info in products.items():
                        prod_desc = prod_info.get("desc", "")
                        desc_str = f"({prod_desc})" if prod_desc else ""
                        col1, col2 = st.columns([8, 1])
                        
                        with col1:
                            st.markdown(f"""
                                <div style='font-size:0.9em; padding:5px; border-bottom:1px solid #eee;'>
                                    • {prod_name} {desc_str} （数量：{prod_info['quantity']}）
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if st.button("✕", key=f"del_prod_{project_id}_{prod_name}", help="删除产品"):
                                del project_data["products"][prod_name]
                                st.success(f"✅ 已删除产品 {prod_name}")
                                st.rerun()
                else:
                    st.info("📭 暂无产品，请添加")
                
                # 添加产品表单
                st.caption("➕ 添加产品")
                with st.form(f"add_product_form_{project_id}", border=False):
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
                    
                    with col1:
                        prod_name = st.text_input("产品名称 *", label_visibility="collapsed", placeholder="如：单模光缆").strip()
                    
                    with col2:
                        prod_quantity = st.number_input("数量 *", min_value=1, value=1, label_visibility="collapsed")
                    
                    with col3:
                        prod_desc = st.text_input("产品描述", label_visibility="collapsed", placeholder="规格/技术要求").strip()
                    
                    with col4:
                        prod_file = st.file_uploader("规格文件", label_visibility="collapsed", key=f"prod_file_{project_id}")
                    
                    with col5:
                        add_prod_clicked = st.form_submit_button("添加")
                    
                    if add_prod_clicked:
                        if not prod_name:
                            st.warning("⚠️ 产品名称不能为空")
                        elif prod_name in products:
                            st.warning(f"⚠️ 产品 {prod_name} 已存在")
                        else:
                            # 添加产品
                            project_data["products"][prod_name] = {
                                "quantity": prod_quantity,
                                "desc": prod_desc,
                                "bids": [],
                                "admin_file": file_to_base64(prod_file)
                            }
                            st.success(f"✅ 已添加产品 {prod_name}")
                            st.rerun()
                
                # 删除项目按钮
                if st.button(f"🗑️ 删除项目：{project_data['name']}", key=f"del_proj_{project_id}", type="secondary"):
                    del global_data["projects"][project_id]
                    st.success(f"✅ 已删除项目 {project_data['name']}")
                    st.rerun()
    
    # ========== 监控中心 ==========
    elif menu_option == "监控中心":
        st.subheader("📊 报价监控中心")
        
        # 项目选择
        project_options = {
            pid: f"{pdata['deadline']} - {pdata['name']}"
            for pid, pdata in global_data["projects"].items()
            if "deadline" in pdata and "products" in pdata
        }
        
        if not project_options:
            st.info("📭 暂无可监控的项目")
            return
        
        selected_project_id = st.selectbox(
            "选择监控项目",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x]
        )
        
        selected_project = global_data["projects"][selected_project_id]
        products = selected_project.get("products", {})
        
        # 报价汇总（核心修复：确保summary_data始终初始化）
        st.markdown("### 🏆 报价汇总")
        summary_data = []  # 必须先初始化（关键修复）
        
        for prod_name, prod_info in products.items():
            bids = prod_info.get("bids", [])
            valid_bids = [b for b in bids if b.get("price", 0) > 0]
            
            # 初始化单行数据
            row_data = {
                "产品名称": prod_name,
                "数量": prod_info["quantity"],
                "最低单价": "-",
                "最低总价": "-",
                "最高单价": "-",
                "最高总价": "-",
                "最优供应商": "-",
                "价差幅度": "-",
                "有效报价数": len(valid_bids)
            }
            
            # 有有效报价时计算数据
            if valid_bids:
                prices = [b["price"] for b in valid_bids]
                min_price = min(prices)
                max_price = max(prices)
                min_total = min_price * prod_info["quantity"]
                max_total = max_price * prod_info["quantity"]
                
                # 最优供应商
                best_suppliers = [b["supplier"] for b in valid_bids if b["price"] == min_price]
                best_suppliers_str = ", ".join(set(best_suppliers))
                
                # 价差幅度
                price_diff = (max_price - min_price) / min_price * 100 if min_price > 0 else 0
                
                # 更新行数据
                row_data.update({
                    "最低单价": f"¥{min_price:.2f}",
                    "最低总价": f"¥{min_total:.2f}",
                    "最高单价": f"¥{max_price:.2f}",
                    "最高总价": f"¥{max_total:.2f}",
                    "最优供应商": best_suppliers_str,
                    "价差幅度": f"{price_diff:.1f}%"
                })
            
            # 添加到汇总数据
            summary_data.append(row_data)
        
        # 渲染汇总表格（核心修复：兜底空数据）
        if not summary_data:
            summary_df = pd.DataFrame(columns=[
                "产品名称", "数量", "最低单价", "最低总价", 
                "最高单价", "最高总价", "最优供应商", "价差幅度", "有效报价数"
            ])
        else:
            summary_df = pd.DataFrame(summary_data)
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # 导出Excel
        st.markdown("---")
        all_detail_data = []
        for prod_name, prod_info in products.items():
            for bid in prod_info.get("bids", []):
                price = bid.get("price", 0)
                all_detail_data.append({
                    "项目名称": selected_project["name"],
                    "产品名称": prod_name,
                    "数量": prod_info["quantity"],
                    "供应商": bid.get("supplier", ""),
                    "单价(¥)": f"{price:.2f}",
                    "总价(¥)": f"{price * prod_info['quantity']:.2f}",
                    "备注": bid.get("remark", ""),
                    "报价时间": bid.get("time", ""),
                    "附件状态": "有" if bid.get("file") else "无"
                })
        
        if all_detail_data:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                summary_df.to_excel(writer, sheet_name="报价汇总", index=False)
                pd.DataFrame(all_detail_data).to_excel(writer, sheet_name="报价明细", index=False)
            
            st.download_button(
                label="📥 导出Excel报表",
                data=output.getvalue(),
                file_name=f"华脉招采-{selected_project['name']}-报价报表.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        
        # 详细报价分析
        st.markdown("---")
        st.markdown("### 📈 产品报价详情")
        
        for prod_name, prod_info in products.items():
            st.markdown(f"#### 📦 {prod_name}（数量：{prod_info['quantity']}）")
            
            bids = prod_info.get("bids", [])
            if not bids:
                st.info("暂无报价数据")
                st.divider()
                continue
            
            # 准备图表和表格数据
            chart_data = []
            table_data = []
            
            for bid in bids:
                bid_time = bid.get("datetime", datetime.now())
                supplier = bid.get("supplier", "未知")
                price = bid.get("price", 0)
                total = price * prod_info["quantity"]
                
                chart_data.append({
                    "时间": bid_time,
                    "单价(¥)": price,
                    "供应商": supplier
                })
                
                table_data.append({
                    "供应商": supplier,
                    "单价(¥)": f"{price:.2f}",
                    "总价(¥)": f"{total:.2f}",
                    "报价时间": bid.get("time", ""),
                    "备注": bid.get("remark", ""),
                    "附件": "✅" if bid.get("file") else "❌"
                })
            
            # 双列布局：图表 + 表格
            col1, col2 = st.columns(2)
            
            with col1:
                st.line_chart(
                    pd.DataFrame(chart_data),
                    x="时间",
                    y="单价(¥)",
                    color="供应商",
                    height=250,
                    use_container_width=True
                )
            
            with col2:
                st.dataframe(
                    table_data,
                    use_container_width=True,
                    hide_index=True,
                    height=250
                )
            
            # 附件下载
            file_tags = []
            for bid in bids:
                if bid.get("file"):
                    file_tag = get_styled_download_tag(bid["file"], bid["supplier"])
                    if file_tag:
                        file_tags.append(file_tag)
            
            if file_tags:
                st.markdown("##### 📎 供应商附件")
                st.markdown("".join(file_tags), unsafe_allow_html=True)
            
            st.divider()

# --- 主程序入口 ---
def main():
    """主程序入口"""
    # 检查会话状态
    if "user" not in st.session_state:
        render_login_page()
    else:
        user_type = st.session_state.get("user_type")
        if user_type == "admin":
            render_admin_dashboard()
        elif user_type == "supplier":
            render_supplier_dashboard()
        else:
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()

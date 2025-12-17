import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 页面配置（响应式优化）---
st.set_page_config(
    page_title="华脉招采平台",
    layout="wide",
    initial_sidebar_state="collapsed",  # 移动端默认折叠侧边栏
)

# --- 🎨 全新CSS样式（响应式+主题化+动效）---
st.markdown("""
    <style>
        /* 基础响应式容器 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            padding-left: clamp(1rem, 3vw, 2rem) !important;
            padding-right: clamp(1rem, 3vw, 2rem) !important;
            max-width: 1920px !important;
        }
        
        /* 平滑滚动 */
        html {
            scroll-behavior: smooth;
        }
        
        /* 主题色定义 */
        :root {
            --huamai-blue: #0068c9;
            --huamai-light-blue: #e6f3ff;
            --huamai-gray: #f5f7fa;
            --huamai-dark-gray: #31333F;
            --huamai-border: #e5e7eb;
            --huamai-success: #00b42a;
            --huamai-warning: #ff7d00;
            --huamai-danger: #f53f3f;
            --shadow-sm: 0 2px 6px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
        }
        
        /* 通用卡片样式（响应式+hover动效） */
        .hm-card {
            border: 1px solid var(--huamai-border);
            background-color: white;
            padding: clamp(0.8rem, 2vw, 1.2rem);
            border-radius: 8px;
            margin-bottom: clamp(0.8rem, 2vw, 1.2rem);
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease;
            height: 100%;
        }
        .hm-card:hover {
            box-shadow: var(--shadow-md);
            border-color: var(--huamai-blue);
        }
        
        /* 数据指标卡片 */
        .metric-card {
            background: linear-gradient(135deg, var(--huamai-light-blue) 0%, #f0f7ff 100%);
            border: 1px solid #cce5ff;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            box-shadow: var(--shadow-sm);
            transition: transform 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .metric-value {
            font-size: clamp(1.5rem, 4vw, 2.5rem);
            font-weight: 700;
            color: var(--huamai-blue);
            margin: 0.5rem 0;
        }
        .metric-label {
            font-size: clamp(0.8rem, 1.5vw, 1rem);
            color: #666;
        }
        
        /* 响应式列间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: clamp(0.5rem, 1vw, 1rem) !important;
        }
        
        /* 表单元素样式优化 */
        .stTextInput > div > div,
        .stNumberInput > div > div,
        .stTextArea > div > div,
        .stSelectbox > div > div {
            border-radius: 6px !important;
            border: 1px solid var(--huamai-border) !important;
            padding: 0.5rem !important;
        }
        .stTextInput > div > div:focus-within,
        .stNumberInput > div > div:focus-within,
        .stTextArea > div > div:focus-within,
        .stSelectbox > div > div:focus-within {
            border-color: var(--huamai-blue) !important;
            box-shadow: 0 0 0 2px rgba(0, 104, 201, 0.1) !important;
        }
        
        /* 按钮样式升级 */
        .stButton > button {
            border-radius: 6px !important;
            padding: 0.5rem 1.2rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
            border: none !important;
        }
        .stButton > button:not(:disabled):hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-sm);
        }
        .stButton > button[data-baseweb="primary-button"] {
            background-color: var(--huamai-blue) !important;
        }
        .stButton > button[data-baseweb="primary-button"]:hover {
            background-color: #005bb5 !important;
        }
        
        /* 文件上传组件响应式优化 */
        section[data-testid="stFileUploader"] {
            padding: 0 !important;
            min-height: 0 !important;
        }
        section[data-testid="stFileUploader"] > div {
            border-radius: 6px !important;
            border: 1px dashed var(--huamai-border) !important;
            padding: clamp(1rem, 3vw, 2rem) !important;
            position: relative !important;
            background-color: var(--huamai-gray) !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child {
            display: none !important;
        }
        [data-testid="stFileUploader"] button {
            color: transparent !important;
            position: relative !important;
            min-width: clamp(80px, 10vw, 120px) !important;
        }
        [data-testid="stFileUploader"] button::after {
            content: "📂 选择文件";
            color: var(--huamai-dark-gray);
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            font-size: clamp(0.8rem, 1.5vw, 0.9rem);
            white-space: nowrap;
        }
        section[data-testid="stFileUploader"] > div > div::before {
            content: "拖拽文件到此处 / 200MB内";
            position: absolute;
            left: clamp(0.8rem, 2vw, 1rem);
            top: 50%;
            transform: translateY(-50%);
            font-size: clamp(0.7rem, 1.5vw, 0.8rem);
            color: #888;
            pointer-events: none;
            z-index: 1;
        }
        
        /* 表格响应式优化 */
        .stDataFrame {
            font-size: clamp(0.75rem, 1.5vw, 0.85rem) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        .dataframe th {
            background-color: var(--huamai-gray) !important;
            font-weight: 600 !important;
            padding: 0.8rem !important;
        }
        .dataframe td {
            padding: 0.8rem !important;
            border-bottom: 1px solid var(--huamai-border) !important;
        }
        
        /* 移动端适配 */
        @media (max-width: 768px) {
            /* 移动端单列显示 */
            .stColumns {
                flex-direction: column !important;
            }
            /* 侧边栏移动端优化 */
            [data-testid="stSidebar"] {
                width: 100% !important;
                max-width: 100% !important;
            }
            /* 移动端隐藏部分装饰元素 */
            .sup-badge {
                display: block !important;
                margin-bottom: 0.5rem !important;
            }
            /* 移动端卡片紧凑显示 */
            .hm-card {
                padding: 0.8rem !important;
            }
        }
        
        /* 加载动画 */
        .loading-spinner {
            border: 3px solid var(--huamai-light-blue);
            border-top: 3px solid var(--huamai-blue);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 8px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 空数据占位图 */
        .empty-state {
            text-align: center;
            padding: clamp(2rem, 5vw, 4rem) 1rem;
            color: #999;
        }
        .empty-state i {
            font-size: clamp(2rem, 8vw, 4rem);
            margin-bottom: 1rem;
            display: block;
            color: #ddd;
        }
        .empty-state p {
            font-size: clamp(0.9rem, 2vw, 1rem);
            margin: 0;
        }
        
        /* 供应商标签优化 */
        .sup-badge {
            display: inline-block;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            background-color: var(--huamai-light-blue);
            color: var(--huamai-blue);
            border: 1px solid #cce5ff;
            font-size: clamp(0.75rem, 1.5vw, 0.85rem);
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* 文件下载标签优化 */
        .file-tag {
            display: inline-block;
            background-color: white;
            color: var(--huamai-blue);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            border: 1px solid var(--huamai-light-blue);
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
            text-decoration: none;
            font-size: clamp(0.75rem, 1.5vw, 0.85rem);
            transition: all 0.2s;
        }
        .file-tag:hover {
            background-color: var(--huamai-light-blue);
            color: #005bb5;
            transform: translateY(-1px);
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据初始化 ---
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

# 全局数据实例
global_data = init_global_data()

# --- 工具函数（新增图表相关）---
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
       style="text-decoration:none; color:var(--huamai-blue); font-weight:bold; font-size:clamp(0.75rem, 1.5vw, 0.85rem);">
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

def create_price_comparison_chart(bids_data, product_name, quantity):
    """创建供应商报价对比柱状图"""
    if not bids_data:
        return None
    
    suppliers = [bid["supplier"] for bid in bids_data]
    prices = [bid["price"] for bid in bids_data]
    totals = [price * quantity for price in prices]
    
    # 创建双轴图表
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 添加单价柱
    fig.add_trace(
        go.Bar(x=suppliers, y=prices, name='单价 (¥)', 
               marker_color=var(--huamai-blue), opacity=0.8),
        secondary_y=False,
    )
    
    # 添加总价柱
    fig.add_trace(
        go.Bar(x=suppliers, y=totals, name='总价 (¥)', 
               marker_color='#00b42a', opacity=0.6),
        secondary_y=True,
    )
    
    # 样式配置
    fig.update_layout(
        title=f"{product_name} 报价对比",
        title_font=dict(size=clamp(14, 2vw, 16), color='#333'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    
    # 轴配置
    fig.update_xaxes(tickangle=-45, tickfont=dict(size=clamp(10, 1.5vw, 12)))
    fig.update_yaxes(title_text="单价 (¥)", secondary_y=False, tickfont=dict(size=clamp(10, 1.5vw, 12)))
    fig.update_yaxes(title_text="总价 (¥)", secondary_y=True, tickfont=dict(size=clamp(10, 1.5vw, 12)))
    
    return fig

def create_price_trend_chart(bids_data, product_name):
    """创建报价趋势面积图"""
    if not bids_data or len(bids_data) < 2:
        return None
    
    # 按时间排序
    sorted_bids = sorted(bids_data, key=lambda x: x["datetime"])
    
    times = [bid["datetime"] for bid in sorted_bids]
    prices = [bid["price"] for bid in sorted_bids]
    suppliers = [bid["supplier"] for bid in sorted_bids]
    
    fig = px.area(
        x=times,
        y=prices,
        color=suppliers,
        title=f"{product_name} 报价趋势",
        labels={"x": "报价时间", "y": "单价 (¥)"},
        height=300,
        template="plotly_white",
    )
    
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        title_font=dict(size=clamp(14, 2vw, 16), color='#333'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    fig.update_xaxes(tickfont=dict(size=clamp(10, 1.5vw, 12)))
    fig.update_yaxes(tickfont=dict(size=clamp(10, 1.5vw, 12)))
    
    return fig

def create_quote_pie_chart(summary_data):
    """创建报价占比饼图"""
    if not summary_data or sum([int(row["有效报价数"]) for row in summary_data]) == 0:
        return None
    
    product_names = [row["产品名称"] for row in summary_data if int(row["有效报价数"]) > 0]
    quote_counts = [int(row["有效报价数"]) for row in summary_data if int(row["有效报价数"]) > 0]
    
    fig = px.pie(
        values=quote_counts,
        names=product_names,
        title="各产品有效报价数占比",
        hole=0.3,
        height=350,
        template="plotly_white",
    )
    
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        title_font=dict(size=clamp(16, 2vw, 18), color='#333'),
        legend=dict(font=dict(size=clamp(10, 1.5vw, 12))),
    )
    
    return fig

def clamp(min_val, val, max_val):
    """辅助函数：限制值的范围（兼容不同Python版本）"""
    return max(min_val, min(val, max_val))

# --- 登录页面（响应式优化）---
def render_login_page():
    """渲染登录页面"""
    st.markdown("<h2 style='text-align: center; color: var(--huamai-blue); margin-bottom: clamp(1rem, 3vw, 2rem);'>🔐 华脉招采平台</h2>", unsafe_allow_html=True)
    
    # 响应式登录框
    col1, col2, col3 = st.columns([1, clamp(1.5, 50vw, 3), 1])
    with col2:
        with st.container(border=True, height=None):
            st.markdown('<div class="hm-card" style="border:none; box-shadow:none; padding:0;">', unsafe_allow_html=True)
            
            username = st.text_input(
                "用户名",
                label_visibility="collapsed",
                placeholder="请输入用户名",
                key="login_username"
            ).strip()
            
            password = st.text_input(
                "密码",
                type="password",
                label_visibility="collapsed",
                placeholder="请输入密码",
                key="login_password"
            ).strip()
            
            # 登录按钮（响应式）
            login_col1, login_col2 = st.columns([4, 1])
            with login_col1:
                if st.button("登录", type="primary", use_container_width=True, key="login_btn"):
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
            
            st.markdown('</div>', unsafe_allow_html=True)

# --- 供应商端页面（响应式+样式优化）---
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
    
    # 页面头部（响应式卡片）
    with st.container():
        st.markdown('<div class="hm-card">', unsafe_allow_html=True)
        
        # 响应式列布局
        col_layout = [1, 2, 1.5, 0.8, 0.8] if st.get_window_width() > 768 else [2, 3, 2, 1]
        cols = st.columns(col_layout)
        
        with cols[0]:
            st.markdown(f"**👤 {supplier_name}**", unsafe_allow_html=True)
        
        with cols[1]:
            st.caption(f"项目：{project_data.get('name', '未知项目')}")
        
        with cols[2]:
            if is_closed:
                st.error("🚫 报价已截止")
            else:
                st.success(f"⏳ 剩余：{str(time_remaining).split('.')[0]}")
        
        if len(cols) > 3:
            with cols[3]:
                if st.button("🔄 刷新", help="获取最新数据", use_container_width=True):
                    st.rerun()
            
            with cols[4]:
                if st.button("退出", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 最后15分钟提醒
    if not is_closed and timedelta(minutes=0) < time_remaining < timedelta(minutes=15):
        st.warning("🔥 报价即将截止，请尽快提交！")
    
    # 获取产品列表
    products = project_data.get("products", {})
    if not products:
        st.markdown("""
            <div class="empty-state">
                <i>📭</i>
                <p>当前项目暂无可报价产品</p>
            </div>
        """, unsafe_allow_html=True)
        return
    
    # 初始化提交锁
    if "submit_lock" not in st.session_state:
        st.session_state["submit_lock"] = {}
    
    # 渲染产品报价表单（响应式）
    for product_name, product_info in products.items():
        st.markdown('<div class="hm-card">', unsafe_allow_html=True)
        
        # 产品信息（响应式）
        product_desc = product_info.get("desc", "")
        desc_html = f"<span class='prod-desc'>({product_desc})</span>" if product_desc else ""
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem;">
                <span><b>📦 {product_name}</b> {desc_html}</span>
                <small style='color:#666'>数量：{product_info['quantity']}</small>
            </div>
        """, unsafe_allow_html=True)
        
        # 管理员提供的文件链接
        admin_file = product_info.get("admin_file")
        if admin_file:
            download_link = get_simple_download_link(admin_file)
            st.markdown(f"""
                <div style='margin-bottom:1rem; font-size:clamp(0.75rem, 1.5vw, 0.85rem)'>
                    {download_link}
                </div>
            """, unsafe_allow_html=True)
        
        # 报价表单（响应式列布局）
        with st.form(key=f"quote_form_{product_name}", border=False):
            # 根据屏幕宽度调整列布局
            if st.get_window_width() > 768:
                fc1, fc2, fc3, fc4 = st.columns([1.5, 2, 2, 1])
            else:
                fc1, fc2 = st.columns([1, 1])
                fc3 = st.columns(1)[0]
                fc4 = st.columns(1)[0]
            
            with fc1:
                quote_price = st.number_input(
                    "单价",
                    min_value=0.0,
                    step=0.1,
                    label_visibility="collapsed",
                    placeholder="¥ 请输入单价",
                    key=f"price_{product_name}"
                )
            
            with fc2:
                quote_remark = st.text_input(
                    "备注",
                    label_visibility="collapsed",
                    placeholder="输入报价备注（选填）",
                    key=f"remark_{product_name}"
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
                    disabled=submit_disabled,
                    type="primary"
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
                        
                        # 检查是否为重复提交
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr style='margin: clamp(0.5rem, 1vw, 1rem) 0; border-top: 1px solid var(--huamai-border);'>", unsafe_allow_html=True)

# --- 管理员端页面（新增图表+响应式+样式优化）---
def render_admin_dashboard():
    """渲染管理员控制台"""
    # 侧边栏菜单（响应式）
    with st.sidebar:
        st.markdown("<h3 style='color: var(--huamai-blue);'>👮‍♂️ 管理员控制台</h3>", unsafe_allow_html=True)
        
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
        
        menu_option = st.radio(
            "功能菜单",
            ["项目管理", "供应商库", "监控中心"],
            key="admin_menu"
        )
        
        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
        
        if st.button("🚪 退出系统", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
    
    # ========== 供应商库管理 ==========
    if menu_option == "供应商库":
        st.markdown("<h2 style='color: var(--huamai-blue); margin-bottom: 1rem;'>🏢 供应商库管理</h2>", unsafe_allow_html=True)
        
        # 添加新供应商（卡片样式）
        st.markdown('<div class="hm-card">', unsafe_allow_html=True)
        with st.expander("➕ 新增供应商", expanded=False):
            with st.form("add_supplier_form", border=False):
                # 响应式表单布局
                if st.get_window_width() > 768:
                    col1, col2, col3 = st.columns(3)
                    col4, col5, col6 = st.columns(3)
                else:
                    col1, col2 = st.columns(2)
                    col3 = st.columns(1)[0]
                    col4, col5 = st.columns(2)
                    col6 = st.columns(1)[0]
                
                with col1:
                    new_sup_name = st.text_input("供应商名称 *", placeholder="请输入企业全称").strip()
                
                with col2:
                    new_sup_contact = st.text_input("联系人", placeholder="请输入联系人姓名").strip()
                
                with col3:
                    new_sup_job = st.text_input("职位", placeholder="如：销售经理").strip()
                
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
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 供应商列表编辑（响应式表格）
        st.markdown("<h3 style='margin-bottom: 1rem;'>📋 供应商名录</h3>", unsafe_allow_html=True)
        st.info("💡 可直接编辑表格内容，修改后点击【保存所有修改】按钮生效")
        
        # 确保suppliers始终是字典
        suppliers_dict = global_data.get("suppliers", {})
        if not isinstance(suppliers_dict, dict):
            global_data["suppliers"] = {}
            suppliers_dict = {}
        
        # 渲染供应商表格
        if suppliers_dict:
            st.markdown('<div class="hm-card">', unsafe_allow_html=True)
            
            # 转换为DataFrame
            supplier_df = pd.DataFrame.from_dict(suppliers_dict, orient="index")
            
            # 补充缺失列
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
            
            # 可编辑表格（响应式）
            edited_df = st.data_editor(
                supplier_df,
                use_container_width=True,
                num_rows="dynamic",
                key="supplier_editor",
                column_config={
                    "联系人": st.column_config.TextColumn(width="medium"),
                    "联系电话": st.column_config.TextColumn(width="medium"),
                    "职位": st.column_config.TextColumn(width="small"),
                    "产品类型": st.column_config.TextColumn(width="medium"),
                    "办公地址": st.column_config.TextColumn(width="large"),
                }
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
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 删除供应商（响应式布局）
            st.markdown("---")
            st.markdown("<h3 style='margin-bottom: 1rem;'>🗑️ 供应商删除</h3>", unsafe_allow_html=True)
            
            # 根据屏幕宽度调整列数
            col_count = 4 if st.get_window_width() > 1200 else 3 if st.get_window_width() > 768 else 2
            del_cols = st.columns(col_count)
            
            for idx, (sup_name, _) in enumerate(suppliers_dict.items()):
                with del_cols[idx % col_count]:
                    if st.button(f"删除 {sup_name}", key=f"del_sup_{sup_name}", type="secondary"):
                        del global_data["suppliers"][sup_name]
                        st.success(f"✅ 已删除供应商 {sup_name}")
                        st.rerun()
        else:
            st.markdown("""
                <div class="empty-state">
                    <i>📭</i>
                    <p>暂无供应商数据，请先添加</p>
                </div>
            """, unsafe_allow_html=True)
    
    # ========== 项目管理 ==========
    elif menu_option == "项目管理":
        st.markdown("<h2 style='color: var(--huamai-blue); margin-bottom: 1rem;'>📁 项目管理</h2>", unsafe_allow_html=True)
        
        # 新建项目（卡片样式）
        st.markdown('<div class="hm-card">', unsafe_allow_html=True)
        with st.expander("➕ 新建项目", expanded=False):
            with st.form("create_project_form", border=False):
                # 响应式布局
                if st.get_window_width() > 768:
                    col1, col2, col3 = st.columns([1.5, 1, 1])
                else:
                    col1 = st.columns(1)[0]
                    col2, col3 = st.columns(2)
                
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
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 现有项目管理
        projects = global_data.get("projects", {})
        if not projects:
            st.markdown("""
                <div class="empty-state">
                    <i>📭</i>
                    <p>暂无项目数据，请先创建</p>
                </div>
            """, unsafe_allow_html=True)
            return
        
        # 按截止时间排序
        sorted_projects = sorted(
            projects.items(),
            key=lambda x: x[1]["deadline"],
            reverse=True
        )
        
        for project_id, project_data in sorted_projects:
            st.markdown('<div class="hm-card">', unsafe_allow_html=True)
            
            with st.expander(f"📅 {project_data['deadline']} | {project_data['name']}", expanded=False):
                # 追加供应商
                with st.expander("➕ 追加供应商", expanded=False):
                    with st.form(f"append_supplier_form_{project_id}", border=False):
                        current_suppliers = list(project_data.get("codes", {}).keys())
                        all_suppliers = list(global_data["suppliers"].keys())
                        remaining_suppliers = [s for s in all_suppliers if s not in current_suppliers]
                        
                        # 响应式布局
                        if st.get_window_width() > 768:
                            col1, col2 = st.columns(2)
                        else:
                            col1 = st.columns(1)[0]
                            col2 = st.columns(1)[0]
                        
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
                    # 响应式表格展示供应商账号
                    supplier_code_data = []
                    for sup_name, sup_code in supplier_codes.items():
                        supplier_code_data.append({
                            "供应商名称": sup_name,
                            "登录用户名": sup_name,
                            "登录密码": sup_code
                        })
                    
                    st.dataframe(
                        pd.DataFrame(supplier_code_data),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "供应商名称": st.column_config.TextColumn(width="medium"),
                            "登录用户名": st.column_config.TextColumn(width="medium"),
                            "登录密码": st.column_config.TextColumn(width="small"),
                        }
                    )
                else:
                    st.info("⚠️ 该项目暂无供应商")
                
                st.markdown("<div style='margin:10px 0;'></div>", unsafe_allow_html=True)
                
                # 产品管理
                st.caption("📦 产品列表")
                products = project_data.get("products", {})
                
                if products:
                    # 产品列表表格化展示
                    product_data = []
                    for prod_name, prod_info in products.items():
                        product_data.append({
                            "产品名称": prod_name,
                            "数量": prod_info["quantity"],
                            "描述": prod_info.get("desc", ""),
                            "附件": "✅" if prod_info.get("admin_file") else "❌",
                            "报价数": len(prod_info.get("bids", []))
                        })
                    
                    st.dataframe(
                        pd.DataFrame(product_data),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "产品名称": st.column_config.TextColumn(width="medium"),
                            "数量": st.column_config.NumberColumn(width="small"),
                            "描述": st.column_config.TextColumn(width="large"),
                            "附件": st.column_config.TextColumn(width="small"),
                            "报价数": st.column_config.NumberColumn(width="small"),
                        }
                    )
                    
                    # 删除产品按钮
                    if st.get_window_width() > 768:
                        del_prod_cols = st.columns(4)
                    else:
                        del_prod_cols = st.columns(2)
                    
                    for idx, (prod_name, _) in enumerate(products.items()):
                        with del_prod_cols[idx % len(del_prod_cols)]:
                            if st.button(f"删除 {prod_name}", key=f"del_prod_{project_id}_{prod_name}", type="secondary"):
                                del project_data["products"][prod_name]
                                st.success(f"✅ 已删除产品 {prod_name}")
                                st.rerun()
                else:
                    st.info("📭 暂无产品，请添加")
                
                # 添加产品表单（响应式）
                st.caption("➕ 添加产品")
                with st.form(f"add_product_form_{project_id}", border=False):
                    if st.get_window_width() > 768:
                        col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
                    else:
                        col1, col2 = st.columns(2)
                        col3 = st.columns(1)[0]
                        col4 = st.columns(1)[0]
                        col5 = st.columns(1)[0]
                    
                    with col1:
                        prod_name = st.text_input("产品名称 *", label_visibility="collapsed", placeholder="如：单模光缆").strip()
                    
                    with col2:
                        prod_quantity = st.number_input("数量 *", min_value=1, value=1, label_visibility="collapsed")
                    
                    with col3:
                        prod_desc = st.text_input("产品描述", label_visibility="collapsed", placeholder="规格/技术要求").strip()
                    
                    with col4:
                        prod_file = st.file_uploader("规格文件", label_visibility="collapsed", key=f"prod_file_{project_id}")
                    
                    with col5:
                        add_prod_clicked = st.form_submit_button("添加", type="primary")
                    
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
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== 监控中心（新增图表+数据可视化）==========
    elif menu_option == "监控中心":
        st.markdown("<h2 style='color: var(--huamai-blue); margin-bottom: 1rem;'>📊 报价监控中心</h2>", unsafe_allow_html=True)
        
        # 项目选择
        project_options = {
            pid: f"{pdata['deadline']} - {pdata['name']}"
            for pid, pdata in global_data["projects"].items()
            if "deadline" in pdata and "products" in pdata
        }
        
        if not project_options:
            st.markdown("""
                <div class="empty-state">
                    <i>📭</i>
                    <p>暂无可监控的项目</p>
                </div>
            """, unsafe_allow_html=True)
            return
        
        selected_project_id = st.selectbox(
            "选择监控项目",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            key="monitor_project"
        )
        
        selected_project = global_data["projects"][selected_project_id]
        products = selected_project.get("products", {})
        
        # ========== 数据指标卡片（新增）==========
        st.markdown("<h3 style='margin: 1.5rem 0 1rem;'>📈 核心数据指标</h3>", unsafe_allow_html=True)
        
        # 计算核心指标
        total_products = len(products)
        total_quotes = sum(len(prod_info.get("bids", [])) for prod_info in products.values())
        total_suppliers = len(set(bid.get("supplier") for prod_info in products.values() for bid in prod_info.get("bids", [])))
        
        # 响应式指标卡片布局
        if st.get_window_width() > 768:
            metric_cols = st.columns(3)
        else:
            metric_cols = st.columns(1)
        
        with metric_cols[0]:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">产品总数</div>
                    <div class="metric-value">{total_products}</div>
                    <div style="font-size: 0.8rem; color: #999;">个</div>
                </div>
            """, unsafe_allow_html=True)
        
        if len(metric_cols) > 1:
            with metric_cols[1]:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">总报价数</div>
                        <div class="metric-value">{total_quotes}</div>
                        <div style="font-size: 0.8rem; color: #999;">条</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[2]:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">参与供应商数</div>
                        <div class="metric-value">{total_suppliers}</div>
                        <div style="font-size: 0.8rem; color: #999;">家</div>
                    </div>
                """, unsafe_allow_html=True)
        
        # ========== 报价汇总（优化+新增饼图）==========
        st.markdown("<h3 style='margin: 1.5rem 0 1rem;'>🏆 报价汇总</h3>", unsafe_allow_html=True)
        
        summary_data = []
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
        
        # 渲染汇总表格 + 饼图（响应式布局）
        if st.get_window_width() > 1000:
            sum_col1, sum_col2 = st.columns([2, 1])
        else:
            sum_col1 = st.columns(1)[0]
            sum_col2 = st.columns(1)[0]
        
        with sum_col1:
            st.markdown('<div class="hm-card">', unsafe_allow_html=True)
            
            # 渲染汇总表格
            if not summary_data:
                summary_df = pd.DataFrame(columns=[
                    "产品名称", "数量", "最低单价", "最低总价", 
                    "最高单价", "最高总价", "最优供应商", "价差幅度", "有效报价数"
                ])
            else:
                summary_df = pd.DataFrame(summary_data)
            
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "产品名称": st.column_config.TextColumn(width="medium"),
                    "数量": st.column_config.NumberColumn(width="small"),
                    "最低单价": st.column_config.TextColumn(width="small"),
                    "最低总价": st.column_config.TextColumn(width="small"),
                    "最高单价": st.column_config.TextColumn(width="small"),
                    "最高总价": st.column_config.TextColumn(width="small"),
                    "最优供应商": st.column_config.TextColumn(width="medium"),
                    "价差幅度": st.column_config.TextColumn(width="small"),
                    "有效报价数": st.column_config.NumberColumn(width="small"),
                }
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with sum_col2:
            # 新增报价占比饼图
            pie_fig = create_quote_pie_chart(summary_data)
            if pie_fig:
                st.markdown('<div class="hm-card">', unsafe_allow_html=True)
                st.plotly_chart(pie_fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class="empty-state">
                        <i>📊</i>
                        <p>暂无报价数据可展示</p>
                    </div>
                """, unsafe_allow_html=True)
        
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
                type="primary",
                use_container_width=True
            )
        
        # ========== 详细报价分析（新增多类型图表）==========
        st.markdown("---")
        st.markdown("<h3 style='margin: 1.5rem 0 1rem;'>📈 产品报价详情</h3>", unsafe_allow_html=True)
        
        for prod_name, prod_info in products.items():
            st.markdown(f"<h4 style='color: var(--huamai-blue);'>📦 {prod_name}（数量：{prod_info['quantity']}）</h4>", unsafe_allow_html=True)
            
            bids = prod_info.get("bids", [])
            if not bids:
                st.markdown("""
                    <div class="empty-state" style="padding: 2rem 1rem;">
                        <i>📭</i>
                        <p>暂无报价数据</p>
                    </div>
                """, unsafe_allow_html=True)
                st.divider()
                continue
            
            # 准备数据
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
            
            # 响应式图表布局
            if st.get_window_width() > 1000:
                chart_col1, chart_col2 = st.columns(2)
            else:
                chart_col1 = st.columns(1)[0]
                chart_col2 = st.columns(1)[0]
            
            with chart_col1:
                st.markdown('<div class="hm-card">', unsafe_allow_html=True)
                # 新增报价对比柱状图
                bar_fig = create_price_comparison_chart(bids, prod_name, prod_info["quantity"])
                if bar_fig:
                    st.plotly_chart(bar_fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with chart_col2:
                st.markdown('<div class="hm-card">', unsafe_allow_html=True)
                # 新增报价趋势面积图
                trend_fig = create_price_trend_chart(bids, prod_name)
                if trend_fig:
                    st.plotly_chart(trend_fig, use_container_width=True)
                else:
                    st.markdown("""
                        <div class="empty-state">
                            <i>📉</i>
                            <p>数据不足，无法展示趋势</p>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 报价详情表格
            st.markdown('<div class="hm-card">', unsafe_allow_html=True)
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "供应商": st.column_config.TextColumn(width="medium"),
                    "单价(¥)": st.column_config.TextColumn(width="small"),
                    "总价(¥)": st.column_config.TextColumn(width="small"),
                    "报价时间": st.column_config.TextColumn(width="small"),
                    "备注": st.column_config.TextColumn(width="large"),
                    "附件": st.column_config.TextColumn(width="small"),
                }
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
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

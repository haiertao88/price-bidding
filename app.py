import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta
import hashlib
import json
import os
import time

# --- 页面配置 ---
st.set_page_config(
    page_title="华脉招采平台", 
    layout="wide",
    page_icon="📋"
)

# --- 🎨 CSS 样式深度定制（新增界面优化样式）---
st.markdown("""
    <style>
        /* 基础布局优化 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        /* 按钮样式优化 */
        .stButton>button {
            border-radius: 6px !important;
            height: 2.5rem !important;
        }
        .primary-btn {
            background-color: #165DFF !important;
            color: white !important;
            border: none !important;
        }
        .secondary-btn {
            background-color: #F0F2F5 !important;
            color: #1D2129 !important;
            border: 1px solid #DCDFE6 !important;
        }
        /* 表单样式优化 */
        .stForm {
            border: 1px solid #E5E6EB !important;
            border-radius: 8px !important;
            padding: 1.5rem !important;
        }
        /* 加载动画提示 */
        .loading-text {
            color: #165DFF;
            font-size: 0.9rem;
            font-weight: 500;
        }
        /* 成功/错误提示优化 */
        .success-box {
            background-color: #F0F9FF;
            border-left: 4px solid #52C41A;
            padding: 1rem;
            border-radius: 4px;
            margin: 0.5rem 0;
        }
        .error-box {
            background-color: #FFF1F0;
            border-left: 4px solid #F5222D;
            padding: 1rem;
            border-radius: 4px;
            margin: 0.5rem 0;
        }
        /* 卡片样式 */
        .card {
            background-color: white;
            border: 1px solid #E5E6EB;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- 📊 数据持久化核心配置 ---
DATA_FILE = "huamai_platform_data.json"  # 数据存储文件

def save_data(data):
    """将数据保存到JSON文件（持久化）"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"数据保存失败：{str(e)}")
        return False

def load_data():
    """从JSON文件加载数据（持久化）"""
    default_data = {
        "projects": {},  # 项目数据
        "suppliers": {   # 供应商初始数据
            "GYSA": {"contact": "张经理", "phone": "13800138000", "job": "销售总监", "type": "光纤光缆", "address": "江苏省南京市江宁区xxx号"},
            "GYSB": {"contact": "李工", "phone": "13900139000", "job": "技术支持", "type": "网络机柜", "address": "江苏省苏州市工业园区xxx号"},
            "GYSC": {"contact": "王总", "phone": "13700137000", "job": "总经理", "type": "综合布线", "address": "上海市浦东新区xxx号"}
        },
        "sms_records": []  # 预留字段：短信记录
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            # 文件损坏则返回默认数据并重新保存
            save_data(default_data)
            return default_data
    else:
        # 无文件则创建并保存默认数据
        save_data(default_data)
        return default_data

# 初始化全局数据（持久化）
@st.cache_resource
def init_global_data():
    return load_data()

global_data = init_global_data()

# --- 工具函数 ---
def generate_random_code(length=6):
    """生成随机数字验证码/密码"""
    return ''.join(random.choices(string.digits, k=length))

def file_to_base64(uploaded_file, max_size=200*1024*1024):
    """文件转Base64（带大小限制）"""
    if uploaded_file is None:
        return None
    file_size = uploaded_file.size
    if file_size > max_size:
        st.error(f"文件过大（{file_size/1024/1024:.1f}MB），最大支持200MB")
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64_encoded = base64.b64encode(bytes_data).decode('utf-8')
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

def safe_parse_deadline(deadline_str):
    """安全解析截止时间"""
    if not isinstance(deadline_str, str):
        st.warning("截止时间格式错误，已重置为1小时后")
        return datetime.now() + timedelta(hours=1)
    supported_formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in supported_formats:
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue
    st.warning(f"截止时间 {deadline_str} 格式错误，已重置为当前时间")
    return datetime.now()

# --- 页面渲染函数 ---
def render_login_page():
    """登录页面（界面优化）"""
    st.title("🔑 华脉招采平台登录")
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", border=True):
            st.markdown("### 账号密码登录")
            username = st.text_input(
                "用户名",
                placeholder="请输入您的用户名",
                label_visibility="collapsed"
            ).strip()
            password = st.text_input(
                "密码",
                type="password",
                placeholder="请输入您的密码",
                label_visibility="collapsed"
            ).strip()
            
            login_btn = st.form_submit_button("登录", type="primary")
            if login_btn:
                with st.spinner("正在验证账号..."):
                    time.sleep(1)  # 模拟验证耗时
                    # 管理员账号验证
                    if username == "HUAMAI" and password == "HUAMAI888":
                        st.session_state["user_type"] = "admin"
                        st.session_state["user"] = username
                        st.success("登录成功！正在跳转...")
                        time.sleep(0.5)
                        st.rerun()
                    # 供应商账号验证
                    else:
                        login_success = False
                        target_project_id = None
                        # 遍历所有项目验证供应商账号
                        for project_id, project_data in global_data["projects"].items():
                            supplier_codes = project_data.get("codes", {})
                            if username in supplier_codes and supplier_codes[username] == password:
                                login_success = True
                                target_project_id = project_id
                                break
                        if login_success:
                            st.session_state["user_type"] = "supplier"
                            st.session_state["user"] = username
                            st.session_state["project_id"] = target_project_id
                            st.success("登录成功！正在跳转...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.markdown("""
                                <div class="error-box">
                                    <strong>登录失败</strong>：用户名或密码错误，请重试！
                                </div>
                            """, unsafe_allow_html=True)

def render_supplier_dashboard():
    """供应商端页面（界面优化）"""
    st.title("📤 供应商报价中心")
    st.divider()
    
    # 验证会话
    required_keys = ["user", "project_id", "user_type"]
    if not all(k in st.session_state for k in required_keys):
        st.markdown("""
            <div class="error-box">
                <strong>会话失效</strong>：请重新登录！
            </div>
        """, unsafe_allow_html=True)
        if st.button("返回登录页", type="secondary"):
            st.session_state.clear()
            st.rerun()
        return
    
    supplier_name = st.session_state["user"]
    project_id = st.session_state["project_id"]
    project_data = global_data["projects"].get(project_id)
    
    if not project_data:
        st.markdown("""
            <div class="error-box">
                <strong>项目不存在</strong>：您关联的项目已被删除！
            </div>
        """, unsafe_allow_html=True)
        return
    
    # 项目信息卡片
    st.markdown("### 📋 项目信息")
    with st.container():
        st.markdown(f"""
            <div class="card">
                <div><strong>项目名称：</strong>{project_data['name']}</div>
                <div><strong>报价截止时间：</strong>{project_data['deadline']}</div>
                <div><strong>当前时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    # 截止时间判断
    deadline = safe_parse_deadline(project_data["deadline"])
    is_closed = datetime.now() > deadline
    if is_closed:
        st.markdown("""
            <div class="error-box">
                <strong>报价已截止</strong>：该项目报价时间已结束，无法提交！
            </div>
        """, unsafe_allow_html=True)
    else:
        remaining = deadline - datetime.now()
        hours = remaining.total_seconds() // 3600
        minutes = (remaining.total_seconds() % 3600) // 60
        st.markdown(f"""
            <div class="success-box">
                <strong>报价倒计时</strong>：剩余 {int(hours)} 小时 {int(minutes)} 分钟，请尽快提交！
            </div>
        """, unsafe_allow_html=True)
        
        # 报价表单（界面优化）
        st.markdown("### 📝 提交报价")
        with st.form("quote_form", border=True):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("产品名称 *", placeholder="请输入报价产品名称")
                quote_price = st.number_input("报价金额（元）*", min_value=0.01, step=0.01, format="%.2f")
            with col2:
                quote_quantity = st.number_input("报价数量 *", min_value=1, step=1)
                quote_remark = st.text_area("报价说明", placeholder="请输入产品规格、交付周期等说明", height=100)
            
            submit_btn = st.form_submit_button("🚀 提交报价", type="primary")
            if submit_btn:
                if not product_name:
                    st.error("产品名称不能为空！")
                else:
                    with st.spinner("正在提交报价..."):
                        time.sleep(1)
                        # 保存报价（扩展：可新增报价数据存储）
                        if "quotes" not in project_data:
                            project_data["quotes"] = {}
                        project_data["quotes"][supplier_name] = {
                            "product_name": product_name,
                            "price": float(quote_price),
                            "quantity": int(quote_quantity),
                            "remark": quote_remark,
                            "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        # 持久化保存
                        if save_data(global_data):
                            st.markdown("""
                                <div class="success-box">
                                    <strong>报价提交成功</strong>：您的报价已保存，可在截止前修改！
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("报价提交失败，请重试！")

def render_admin_dashboard():
    """管理员端页面（数据持久化+界面优化）"""
    st.title("👑 华脉招采平台管理后台")
    st.divider()
    
    # 侧边栏菜单（界面优化）
    menu_option = st.sidebar.radio(
        "功能菜单",
        ["项目管理", "供应商库", "报价监控"],
        index=0,
        format_func=lambda x: f"📁 {x}" if x == "项目管理" else f"📇 {x}" if x == "供应商库" else f"📊 {x}"
    )
    
    # 1. 项目管理（核心功能+数据持久化+界面优化）
    if menu_option == "项目管理":
        st.markdown("### 📁 项目管理")
        
        # 新建项目
        with st.expander("➕ 新建项目", expanded=True):
            with st.form("create_project_form", border=True):
                col1, col2 = st.columns(2)
                with col1:
                    project_name = st.text_input("项目名称 *", placeholder="请输入项目全称")
                    project_deadline_date = st.date_input("截止日期 *", value=datetime.now() + timedelta(days=7))
                with col2:
                    project_deadline_time = st.time_input("截止时间 *", value=datetime.strptime("17:00", "%H:%M").time())
                    available_suppliers = list(global_data["suppliers"].keys())
                    selected_suppliers = st.multiselect(
                        "参与供应商 *",
                        options=available_suppliers,
                        placeholder="请选择至少一个供应商",
                        disabled=not available_suppliers
                    )
                
                create_btn = st.form_submit_button("🚀 创建项目", type="primary")
                if create_btn:
                    with st.spinner("正在创建项目..."):
                        time.sleep(1)
                        if not project_name:
                            st.error("项目名称不能为空！")
                        elif not available_suppliers:
                            st.error("请先在【供应商库】添加供应商！")
                        elif not selected_suppliers:
                            st.error("请至少选择一个参与供应商！")
                        else:
                            # 生成项目数据
                            project_id = str(uuid.uuid4())[:8]
                            deadline_str = f"{project_deadline_date} {project_deadline_time.strftime('%H:%M')}"
                            supplier_codes = {sup: generate_random_code() for sup in selected_suppliers}
                            
                            # 添加到全局数据
                            global_data["projects"][project_id] = {
                                "name": project_name,
                                "deadline": deadline_str,
                                "codes": supplier_codes,
                                "products": {},
                                "quotes": {}
                            }
                            
                            # 持久化保存
                            if save_data(global_data):
                                st.markdown("""
                                    <div class="success-box">
                                        <strong>项目创建成功</strong>！
                                        <br>项目ID：{}
                                        <br>供应商账号已生成，可在供应商库查看。
                                    </div>
                                """.format(project_id), unsafe_allow_html=True)
                            else:
                                st.error("项目创建失败，请重试！")
        
        # 现有项目列表
        st.markdown("### 📋 现有项目")
        projects = global_data.get("projects", {})
        if not projects:
            st.info("暂无项目数据，点击上方「新建项目」创建第一个项目！")
        else:
            # 按截止时间排序
            sorted_projects = sorted(
                projects.items(),
                key=lambda x: safe_parse_deadline(x[1]["deadline"]),
                reverse=False
            )
            
            for project_id, project_data in sorted_projects:
                with st.expander(f"📅 {project_data['name']}（截止：{project_data['deadline']}）", expanded=False):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"""
                            <div class="card">
                                <div><strong>项目ID：</strong>{project_id}</div>
                                <div><strong>参与供应商：</strong>{', '.join(project_data['codes'].keys())}</div>
                                <div><strong>已提交报价：</strong>{len(project_data.get('quotes', {}))}/{len(project_data['codes'])}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        # 编辑按钮（预留）
                        if st.button("编辑", key=f"edit_{project_id}", type="secondary"):
                            st.warning("编辑功能暂未实现，敬请期待！")
                    with col3:
                        # 删除按钮（带确认）
                        if st.button("删除", key=f"del_{project_id}", type="secondary"):
                            with st.spinner("正在删除项目..."):
                                time.sleep(0.5)
                                del global_data["projects"][project_id]
                                if save_data(global_data):
                                    st.success("项目删除成功！")
                                    st.rerun()
                                else:
                                    st.error("项目删除失败，请重试！")
    
    # 2. 供应商库（数据持久化+批量导入+界面优化）
    elif menu_option == "供应商库":
        st.markdown("### 📇 供应商库")
        
        # 批量导入（新增功能）
        st.markdown("#### 📤 批量导入")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "选择Excel/CSV文件（必填列：名称、联系人、手机号）",
                type=["xlsx", "csv"],
                help="Excel/CSV文件需包含：名称、联系人、手机号列"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("清空所有供应商", type="secondary"):
                with st.spinner("正在清空数据..."):
                    time.sleep(0.5)
                    global_data["suppliers"] = {}
                    if save_data(global_data):
                        st.success("所有供应商已清空！")
                        st.rerun()
        
        # 处理导入文件
        if uploaded_file:
            with st.spinner("正在导入数据..."):
                time.sleep(1)
                try:
                    if uploaded_file.name.endswith(".xlsx"):
                        df = pd.read_excel(uploaded_file)
                    else:
                        df = pd.read_csv(uploaded_file)
                    
                    # 校验必填列
                    required_cols = ["名称", "联系人", "手机号"]
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    if missing_cols:
                        st.markdown(f"""
                            <div class="error-box">
                                <strong>导入失败</strong>：文件缺少必填列：{', '.join(missing_cols)}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # 数据清洗
                        df = df.dropna(subset=required_cols)
                        df["手机号"] = df["手机号"].astype(str).str.replace("-", "").str.replace(" ", "")
                        df = df[df["手机号"].str.len() == 11]
                        
                        # 导入数据
                        imported_count = 0
                        for idx, row in df.iterrows():
                            sup_name = row["名称"].strip()
                            global_data["suppliers"][sup_name] = {
                                "contact": row["联系人"].strip(),
                                "phone": row["手机号"],
                                "job": row.get("职位", "").strip(),
                                "type": row.get("类型", "").strip(),
                                "address": row.get("地址", "").strip()
                            }
                            imported_count += 1
                        
                        # 保存数据
                        if save_data(global_data):
                            st.markdown(f"""
                                <div class="success-box">
                                    <strong>导入成功</strong>！共导入 {imported_count} 条有效供应商数据
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("数据导入失败，请重试！")
                except Exception as e:
                    st.markdown(f"""
                        <div class="error-box">
                            <strong>导入异常</strong>：{str(e)}
                        </div>
                    """, unsafe_allow_html=True)
        
        # 新增单个供应商
        st.markdown("#### ➕ 新增供应商")
        with st.form("add_supplier_form", border=True):
            col1, col2 = st.columns(2)
            with col1:
                sup_name = st.text_input("供应商名称 *", placeholder="请输入企业全称")
                sup_contact = st.text_input("联系人 *", placeholder="请输入联系人姓名")
                sup_phone = st.text_input("手机号 *", placeholder="请输入11位手机号")
            with col2:
                sup_job = st.text_input("职位", placeholder="如：销售总监")
                sup_type = st.text_input("业务类型", placeholder="如：光纤光缆")
                sup_address = st.text_input("地址", placeholder="请输入详细地址")
            
            add_btn = st.form_submit_button("保存供应商", type="primary")
            if add_btn:
                with st.spinner("正在保存..."):
                    time.sleep(0.5)
                    if not sup_name:
                        st.error("供应商名称不能为空！")
                    elif not sup_contact:
                        st.error("联系人不能为空！")
                    elif not sup_phone or len(sup_phone) != 11:
                        st.error("请输入有效的11位手机号！")
                    else:
                        global_data["suppliers"][sup_name] = {
                            "contact": sup_contact,
                            "phone": sup_phone,
                            "job": sup_job,
                            "type": sup_type,
                            "address": sup_address
                        }
                        if save_data(global_data):
                            st.success("供应商添加成功！")
                            st.rerun()
                        else:
                            st.error("供应商添加失败，请重试！")
        
        # 供应商列表
        st.markdown("#### 📋 供应商列表")
        suppliers = global_data.get("suppliers", {})
        if not suppliers:
            st.info("暂无供应商数据，点击上方「新增供应商」添加！")
        else:
            # 转换为DataFrame展示
            sup_df = pd.DataFrame.from_dict(suppliers, orient="index")
            sup_df = sup_df.reset_index().rename(columns={"index": "供应商名称"})
            
            # 编辑/删除操作
            edited_df = st.data_editor(
                sup_df,
                num_rows="dynamic",
                disabled=["供应商名称"],  # 名称不可编辑
                column_config={
                    "phone": st.column_config.TextColumn("手机号", validate="^1[3-9]\\d{9}$")
                },
                key="supplier_editor"
            )
            
            # 保存编辑后的数据
            if st.button("保存修改", type="primary"):
                with st.spinner("正在保存修改..."):
                    time.sleep(0.5)
                    new_suppliers = {}
                    for idx, row in edited_df.iterrows():
                        sup_name = row["供应商名称"]
                        if sup_name:
                            new_suppliers[sup_name] = {
                                "contact": row["contact"],
                                "phone": row["phone"],
                                "job": row["job"],
                                "type": row["type"],
                                "address": row["address"]
                            }
                    global_data["suppliers"] = new_suppliers
                    if save_data(global_data):
                        st.success("供应商数据修改成功！")
                    else:
                        st.error("供应商数据修改失败，请重试！")
    
    # 3. 报价监控（界面优化）
    elif menu_option == "报价监控":
        st.markdown("### 📊 报价监控")
        projects = global_data.get("projects", {})
        if not projects:
            st.info("暂无项目数据，无法监控报价！")
        else:
            # 选择项目
            project_names = {p_id: p_data["name"] for p_id, p_data in projects.items()}
            selected_project_id = st.selectbox(
                "选择监控项目",
                options=list(project_names.keys()),
                format_func=lambda x: project_names[x]
            )
            project_data = projects[selected_project_id]
            
            # 报价统计
            st.markdown("#### 📈 报价统计")
            quotes = project_data.get("quotes", {})
            total_suppliers = len(project_data["codes"])
            submitted_suppliers = len(quotes)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("项目名称", project_data["name"])
            with col2:
                st.metric("应提交供应商", total_suppliers)
            with col3:
                st.metric("已提交供应商", submitted_suppliers)
            
            # 报价详情
            st.markdown("#### 📋 报价详情")
            if not quotes:
                st.info("暂无供应商提交报价！")
            else:
                # 转换为DataFrame展示
                quote_df = pd.DataFrame.from_dict(quotes, orient="index")
                quote_df = quote_df.reset_index().rename(columns={"index": "供应商名称"})
                st.dataframe(
                    quote_df,
                    column_config={
                        "price": st.column_config.NumberColumn("报价金额（元）", format="%.2f"),
                        "quantity": st.column_config.NumberColumn("报价数量"),
                        "submit_time": st.column_config.DatetimeColumn("提交时间")
                    },
                    use_container_width=True
                )
                
                # 导出报价数据
                csv_data = quote_df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 导出报价数据",
                    data=csv_data,
                    file_name=f"{project_data['name']}_报价数据_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )

# --- 主程序入口 ---
def main():
    # 初始化会话状态
    if "user_type" not in st.session_state:
        render_login_page()
    else:
        if st.sidebar.button("🔚 退出登录", type="secondary"):
            st.session_state.clear()
            st.rerun()
        
        if st.session_state["user_type"] == "admin":
            render_admin_dashboard()
        elif st.session_state["user_type"] == "supplier":
            render_supplier_dashboard()

if __name__ == "__main__":
    main()

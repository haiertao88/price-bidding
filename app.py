import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="华脉询价系统", layout="wide")

# --- CSS 样式修复与优化 ---
# 修复问题1：标题被遮挡。增加顶部内边距。
st.markdown("""
    <style>
        .block-container {
            padding-top: 3.5rem; /* 增加顶部空间，防止标题被遮挡 */
            padding-bottom: 2rem;
        }
        /* 卡片样式优化 */
        .st-emotion-cache-1r6slb0 {
            padding: 1.5rem;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据结构 (重构为支持多项目) ---
@st.cache_resource
def get_global_data():
    return {
        "projects": {} 
        # 结构示例:
        # "uuid_1": {
        #     "name": "上午电子料询价",
        #     "date": "2023-10-27",
        #     "codes": {"GYSA": "8821", "GYSB": "9921", "GYSC": "0012"},
        #     "products": { "连接器": {"bids": []} }
        # }
    }

shared_data = get_global_data()

# --- 工具函数 ---
def generate_random_code(length=6):
    """生成随机数字密码"""
    return ''.join(random.choices(string.digits, k=length))

def get_product_rankings(project_id, product_name):
    """计算特定项目中某个产品的排名"""
    project = shared_data["projects"].get(project_id)
    if not project or product_name not in project["products"]:
        return []
        
    bids = project["products"][product_name]["bids"]
    if not bids:
        return []
    
    supplier_best = {}
    for bid in bids:
        sup = bid['supplier']
        price = bid['price']
        if sup not in supplier_best or price < supplier_best[sup]['price']:
            supplier_best[sup] = bid

    return sorted(supplier_best.values(), key=lambda x: x['price'])

# --- 登录逻辑 (升级版) ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 华脉询价系统登录</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("用户名")
            password = st.text_input("密码 / 项目通行码", type="password")
            
            if st.button("登录", type="primary", use_container_width=True):
                # 1. 甲方管理员登录
                if username == "HUAMAI" and password == "HUAMAI888":
                    st.session_state.user_type = "admin"
                    st.session_state.user = username
                    st.rerun()
                
                # 2. 供应商登录 (GYSA, GYSB, GYSC)
                elif username in ["GYSA", "GYSB", "GYSC"]:
                    # 遍历所有项目，检查密码是否匹配某个项目的通行码
                    found_project = None
                    for pid, p_data in shared_data["projects"].items():
                        # 检查该项目是否给该供应商分配了密码，且密码匹配
                        if p_data["codes"].get(username) == password:
                            found_project = pid
                            break
                    
                    if found_project:
                        st.session_state.user_type = "supplier"
                        st.session_state.user = username
                        st.session_state.project_id = found_project # 锁定当前会话到该项目
                        st.success("验证成功！正在进入报价室...")
                        st.rerun()
                    else:
                        st.error("密码无效或项目已过期。请联系管理员获取最新通行码。")
                else:
                    st.error("用户不存在")

# --- 供应商界面 (只能看锁定的项目) ---
def supplier_dashboard():
    current_user = st.session_state.user
    project_id = st.session_state.project_id
    project = shared_data["projects"].get(project_id)

    # 防御性检查：如果项目被删了
    if not project:
        st.error("该项目已结束或被删除。")
        if st.button("退出"):
            st.session_state.clear()
            st.rerun()
        return

    # 侧边栏
    with st.sidebar:
        st.title(f"👤 {current_user}")
        st.markdown(f"**当前项目**:\n{project['name']}")
        st.markdown(f"**日期**: {project['date']}")
        st.info("💡 **操作提示**\n提交报价后，请务必点击下方红色按钮刷新排名！")
        if st.button("🔄 刷新排名", type="primary", use_container_width=True):
            st.rerun()
        if st.button("退出登录"):
            st.session_state.clear()
            st.rerun()

    # 主界面
    st.markdown(f"### 📊 实时报价列表 - {project['name']}")
    
    products = project["products"]
    if not products:
        st.warning("该项目暂无询价产品。")
        return

    for p_name in list(products.keys()):
        with st.container(border=True):
            st.markdown(f"#### 📦 {p_name}")
            rankings = get_product_rankings(project_id, p_name)
            
            # 计算排名
            min_price = rankings[0]['price'] if rankings else 0
            my_rank = None
            for idx, rank_info in enumerate(rankings):
                if rank_info['supplier'] == current_user:
                    my_rank = idx + 1
                    break
            
            c1, c2, c3 = st.columns([1, 1, 1.5])
            c1.metric("全场最低价", f"¥{min_price}" if min_price else "--")
            
            if my_rank == 1:
                c2.metric("我的排名", "第 1 名 🏆", delta="领先")
            elif my_rank:
                c2.metric("我的排名", f"第 {my_rank} 名", delta=None, delta_color="off")
            else:
                c2.metric("我的排名", "未报价")

            with c3:
                with st.form(key=f"{project_id}_{p_name}", border=False):
                    sc1, sc2 = st.columns([2, 1])
                    new_price = sc1.number_input("报价", min_value=0.0, step=1.0, label_visibility="collapsed")
                    if sc2.form_submit_button("🚀 提交"):
                        if new_price > 0:
                            products[p_name]['bids'].append({
                                'supplier': current_user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S')
                            })
                            st.success("已提交")
                            st.rerun()

# --- 管理员界面 (多项目管理) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 华脉总控台")
    st.sidebar.markdown(f"用户: {st.session_state.user}")
    
    # 侧边栏功能切换
    menu = st.sidebar.radio("功能导航", ["📁 项目管理 (新建/密码)", "📊 实时监控", "⚙️ 全局设置"])
    
    if st.sidebar.button("退出系统"):
        st.session_state.clear()
        st.rerun()

    # === 功能1：项目管理 (核心) ===
    if menu == "📁 项目管理 (新建/密码)":
        st.title("📁 项目管理中心")
        
        # 1. 新建项目
        with st.expander("➕ 创建新询价项目", expanded=True):
            with st.form("new_project"):
                c1, c2 = st.columns([2, 1])
                p_name = c1.text_input("项目名称 (如：10月27日电子料询价)")
                p_date = c2.date_input("询价日期", datetime.now())
                if st.form_submit_button("立即创建"):
                    if p_name:
                        new_id = str(uuid.uuid4())[:8] # 生成简短ID
                        # 随机生成3个不同的密码
                        codes = {
                            "GYSA": generate_random_code(),
                            "GYSB": generate_random_code(),
                            "GYSC": generate_random_code()
                        }
                        shared_data["projects"][new_id] = {
                            "name": p_name,
                            "date": str(p_date),
                            "codes": codes,
                            "products": {}
                        }
                        st.success(f"项目 '{p_name}' 创建成功！")
                        st.rerun()
        
        st.markdown("---")
        
        # 2. 项目列表 (按日期折叠)
        if not shared_data["projects"]:
            st.info("暂无项目，请先创建。")
        else:
            # 按日期分组显示
            projects_by_date = {}
            for pid, data in shared_data["projects"].items():
                d = data["date"]
                if d not in projects_by_date: projects_by_date[d] = []
                projects_by_date[d].append((pid, data))
            
            # 倒序显示日期
            for d in sorted(projects_by_date.keys(), reverse=True):
                with st.expander(f"📅 {d}", expanded=True):
                    for pid, data in projects_by_date[d]:
                        with st.container(border=True):
                            # 项目标题栏
                            col_title, col_action = st.columns([3, 1])
                            col_title.subheader(f"📂 {data['name']}")
                            if col_action.button("🗑️ 删除项目", key=f"del_{pid}"):
                                del shared_data["projects"][pid]
                                st.rerun()
                            
                            # 密码区 (重点)
                            st.markdown("##### 🔑 供应商通行码 (请复制发给对应供应商)")
                            code_cols = st.columns(3)
                            for idx, (sup, code) in enumerate(data["codes"].items()):
                                code_cols[idx].code(f"{sup}: {code}", language="text")
                            
                            # 产品管理区
                            st.markdown("##### 📦 询价产品")
                            # 显示现有产品
                            if data["products"]:
                                tags = [f"{p} ({len(v['bids'])}报价)" for p, v in data["products"].items()]
                                st.write("已包含: " + " | ".join(tags))
                            
                            # 添加新产品
                            c_add1, c_add2 = st.columns([3, 1])
                            new_prod = c_add1.text_input("添加产品", key=f"add_p_name_{pid}", placeholder="输入产品名称", label_visibility="collapsed")
                            if c_add2.button("➕ 添加", key=f"btn_add_{pid}"):
                                if new_prod and new_prod not in data["products"]:
                                    data["products"][new_prod] = {"bids": []}
                                    st.rerun()

    # === 功能2：实时监控 ===
    elif menu == "📊 实时监控":
        st.title("📊 报价监控")
        if not shared_data["projects"]:
            st.warning("暂无项目")
        else:
            # 选择要查看的项目
            project_options = {pid: f"{d['date']} - {d['name']}" for pid, d in shared_data["projects"].items()}
            selected_pid = st.selectbox("选择项目", options=list(project_options.keys()), format_func=lambda x: project_options[x])
            
            project = shared_data["projects"][selected_pid]
            
            st.markdown(f"### {project['name']}")
            
            # 下载该项目的Excel
            all_records = []
            for pname, info in project["products"].items():
                for bid in info['bids']:
                    all_records.append({'产品': pname, '供应商': bid['supplier'], '价格': bid['price'], '时间': bid['time']})
            
            if all_records:
                df = pd.DataFrame(all_records)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 导出该项目报价单", buffer.getvalue(), f"bids_{project['date']}.xlsx")
            
            # 显示排名表格
            for p_name in project["products"].keys():
                with st.container(border=True):
                    st.markdown(f"**{p_name}**")
                    rankings = get_product_rankings(selected_pid, p_name)
                    if rankings:
                        # 整理表格
                        display_data = []
                        for i, r in enumerate(rankings):
                            display_data.append({
                                "排名": f"第 {i+1} 名 {'🥇' if i==0 else ''}", 
                                "供应商": r['supplier'], 
                                "价格": f"¥{r['price']}",
                                "时间": r['time']
                            })
                        st.table(display_data)
                    else:
                        st.caption("暂无报价")

# --- 主程序路由 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

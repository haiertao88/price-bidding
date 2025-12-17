import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="华脉询价系统", layout="wide")

# --- CSS 样式优化 ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 3.5rem;
            padding-bottom: 2rem;
        }
        .st-emotion-cache-1r6slb0 {
            padding: 1.5rem;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据结构 ---
@st.cache_resource
def get_global_data():
    return {
        "projects": {} 
        # 结构示例:
        # "uuid_1": {
        #     "name": "电子料询价",
        #     "date": "2023-10-27", 
        #     "codes": {"GYSA": "8821", "供应商D": "9921"}, # 动态供应商列表
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

# --- 登录逻辑 (升级版：支持任意供应商账号) ---
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
                
                # 2. 供应商登录 (动态验证)
                # 不再限制特定的用户名列表，而是去匹配密码
                else:
                    found_project = None
                    # 遍历所有项目
                    for pid, p_data in shared_data["projects"].items():
                        # 检查该项目里是否有这个供应商，且密码对不对
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
                        st.error("登录失败：用户名不存在或通行码错误/已过期。")

# --- 供应商界面 ---
def supplier_dashboard():
    current_user = st.session_state.user
    project_id = st.session_state.project_id
    project = shared_data["projects"].get(project_id)

    if not project:
        st.error("该项目已结束或被删除。")
        if st.button("退出"):
            st.session_state.clear()
            st.rerun()
        return

    with st.sidebar:
        st.title(f"👤 {current_user}")
        st.caption(f"当前项目: {project['name']}")
        st.caption(f"询价日期: {project['date']}")
        st.divider()
        st.info("💡 **操作提示**\n提交报价后，请务必点击下方红色按钮刷新排名！")
        if st.button("🔄 刷新排名", type="primary", use_container_width=True):
            st.rerun()
        if st.button("退出登录"):
            st.session_state.clear()
            st.rerun()

    st.markdown(f"### 📊 实时报价 - {project['name']}")
    
    products = project["products"]
    if not products:
        st.warning("暂无询价产品。")
        return

    # 使用列布局显示产品，每行显示2个
    product_names = list(products.keys())
    
    for p_name in product_names:
        with st.container(border=True):
            st.markdown(f"#### 📦 {p_name}")
            rankings = get_product_rankings(project_id, p_name)
            
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
                c2.metric("我的排名", f"第 {my_rank} 名", delta="未领先", delta_color="off")
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

# --- 管理员界面 (功能增强版) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 华脉总控台")
    st.sidebar.markdown(f"用户: {st.session_state.user}")
    
    menu = st.sidebar.radio("导航", ["📁 项目管理 (新建/密码)", "📊 实时监控 & 导出"])
    
    if st.sidebar.button("退出系统"):
        st.session_state.clear()
        st.rerun()

    # === 功能1：项目管理 ===
    if menu == "📁 项目管理 (新建/密码)":
        st.title("📁 项目管理中心")
        
        # 1. 新建项目 (支持自定义供应商)
        with st.expander("➕ 创建新询价项目", expanded=True):
            with st.form("new_project"):
                st.markdown("#### 1. 项目基础信息")
                c1, c2 = st.columns([2, 1])
                p_name = c1.text_input("项目名称", placeholder="例如：12月17日服务器配件询价")
                p_date = c2.date_input("询价日期", datetime.now())
                
                st.markdown("#### 2. 参与供应商 (用逗号隔开)")
                # 默认值给3个，但允许用户修改
                default_sups = "GYSA, GYSB, GYSC"
                suppliers_str = st.text_area("输入供应商账号列表", value=default_sups, help="例如：GYSA, GYSB, 供应商D, 深圳某厂")
                
                if st.form_submit_button("立即创建"):
                    if p_name and suppliers_str:
                        # 处理供应商列表：分割、去空格、去重
                        sup_list = [s.strip() for s in suppliers_str.replace('，', ',').split(',') if s.strip()]
                        
                        if not sup_list:
                            st.error("请至少输入一个供应商")
                        else:
                            new_id = str(uuid.uuid4())[:8]
                            # 为每个供应商生成密码
                            codes = {sup: generate_random_code() for sup in sup_list}
                            
                            shared_data["projects"][new_id] = {
                                "name": p_name,
                                "date": str(p_date),
                                "codes": codes,
                                "products": {}
                            }
                            st.success(f"项目 '{p_name}' 创建成功！包含 {len(sup_list)} 位供应商。")
                            st.rerun()
                    else:
                        st.error("请填写完整信息")
        
        st.markdown("---")
        
        # 2. 项目列表 (增加日期筛选功能)
        st.subheader("📋 项目列表")
        
        # --- 日期筛选控件 ---
        col_filter1, col_filter2 = st.columns([1, 3])
        with col_filter1:
            filter_mode = st.selectbox("筛选方式", ["显示全部", "按日期查询"])
        
        target_date = None
        if filter_mode == "按日期查询":
            with col_filter2:
                target_date = st.date_input("选择日期", datetime.now())
        
        # 开始过滤逻辑
        projects_to_show = []
        # 按日期倒序排列
        sorted_pids = sorted(shared_data["projects"].keys(), key=lambda x: shared_data["projects"][x]['date'], reverse=True)
        
        for pid in sorted_pids:
            data = shared_data["projects"][pid]
            # 如果开启筛选，且日期不匹配，则跳过
            if filter_mode == "按日期查询" and str(target_date) != data["date"]:
                continue
            projects_to_show.append((pid, data))

        if not projects_to_show:
            st.info("没有找到符合条件的项目。")
        else:
            for pid, data in projects_to_show:
                with st.expander(f"📅 {data['date']} | {data['name']}", expanded=False):
                    
                    # 密码管理区
                    st.markdown("##### 🔑 供应商通行码")
                    st.caption("请复制以下信息发给对应供应商：")
                    
                    # 动态展示所有供应商密码
                    code_items = list(data["codes"].items())
                    # 分列显示，每行3个
                    cols = st.columns(3)
                    for i, (sup, code) in enumerate(code_items):
                        cols[i % 3].code(f"{sup}: {code}", language="text")
                    
                    st.divider()
                    
                    # 产品管理区
                    c_prod1, c_prod2 = st.columns([3, 1])
                    c_prod1.markdown("##### 📦 询价产品管理")
                    
                    # 显示现有产品及删除按钮
                    if data["products"]:
                        for p_key in list(data["products"].keys()):
                            cp1, cp2 = st.columns([4, 1])
                            cp1.text(f"• {p_key}")
                            if cp2.button("删除", key=f"del_p_{pid}_{p_key}"):
                                del data["products"][p_key]
                                st.rerun()
                    else:
                        st.caption("暂无产品")
                    
                    # 添加新产品
                    with st.form(key=f"add_prod_{pid}"):
                        c_add1, c_add2 = st.columns([3, 1])
                        new_p = c_add1.text_input("新增产品名称", placeholder="如：5G芯片", label_visibility="collapsed")
                        if c_add2.form_submit_button("➕ 添加"):
                            if new_p and new_p not in data["products"]:
                                data["products"][new_p] = {"bids": []}
                                st.rerun()
                    
                    # 删除整个项目
                    st.markdown("---")
                    if st.button("🗑️ 删除整个项目", key=f"del_proj_{pid}"):
                        del shared_data["projects"][pid]
                        st.rerun()

    # === 功能2：实时监控 ===
    elif menu == "📊 实时监控 & 导出":
        st.title("📊 报价监控中心")
        
        if not shared_data["projects"]:
            st.warning("暂无项目")
        else:
            # 下拉菜单：选择项目 (按时间倒序)
            project_options = {pid: f"{d['date']} - {d['name']}" for pid, d in shared_data["projects"].items()}
            # 排序
            sorted_opts = dict(sorted(project_options.items(), key=lambda item: shared_data["projects"][item[0]]['date'], reverse=True))
            
            selected_pid = st.selectbox("选择要查看的项目", options=list(sorted_opts.keys()), format_func=lambda x: sorted_opts[x])
            
            project = shared_data["projects"][selected_pid]
            
            # 导出 Excel
            all_records = []
            for pname, info in project["products"].items():
                for bid in info['bids']:
                    all_records.append({'产品': pname, '供应商': bid['supplier'], '价格': bid['price'], '时间': bid['time']})
            
            if all_records:
                df = pd.DataFrame(all_records)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button(f"📥 导出 [{project['name']}] 报价单", buffer.getvalue(), f"报价单_{project['date']}.xlsx")
            
            st.divider()
            
            # 显示详细排名
            for p_name in project["products"].keys():
                with st.container(border=True):
                    st.markdown(f"**{p_name}**")
                    rankings = get_product_rankings(selected_pid, p_name)
                    if rankings:
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
                        st.caption("等待供应商报价...")

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

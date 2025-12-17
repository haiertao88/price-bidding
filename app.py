import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="华脉询价系统 Pro", layout="wide")

# --- CSS 样式优化 ---
st.markdown("""
    <style>
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        .st-emotion-cache-1r6slb0 { padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; }
        .stCode { margin-bottom: -1rem !important; }
        /* 优化图表容器 */
        .chart-container { margin-top: 1rem; margin-bottom: 1rem; }
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

def get_product_rankings(project_id, product_name):
    """计算排名"""
    project = shared_data["projects"].get(project_id)
    if not project or product_name not in project["products"]:
        return []
    
    bids = project["products"][product_name]["bids"]
    if not bids:
        return []
    
    # 取每个供应商的最低价
    supplier_best = {}
    for bid in bids:
        sup = bid['supplier']
        price = bid['price']
        if sup not in supplier_best or price < supplier_best[sup]['price']:
            supplier_best[sup] = bid

    return sorted(supplier_best.values(), key=lambda x: x['price'])

# --- 登录逻辑 ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 华脉询价系统登录</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("用户名")
            password = st.text_input("密码 / 项目通行码", type="password")
            
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
                        st.error("登录失败：用户名不存在或通行码错误。")

# --- 供应商界面 ---
def supplier_dashboard():
    current_user = st.session_state.user
    project_id = st.session_state.project_id
    project = shared_data["projects"].get(project_id)

    if not project:
        st.error("该项目已结束。")
        if st.button("退出"):
            st.session_state.clear()
            st.rerun()
        return

    with st.sidebar:
        st.title(f"👤 {current_user}")
        st.caption(f"项目: {project['name']}")
        st.divider()
        st.info("💡 提交后请刷新排名！")
        if st.button("🔄 刷新排名", type="primary", use_container_width=True): st.rerun()
        if st.button("退出登录"):
            st.session_state.clear()
            st.rerun()

    st.markdown(f"### 📊 实时报价 - {project['name']}")
    
    products = project["products"]
    if not products:
        st.warning("暂无询价产品。")
        return

    for p_name, p_info in products.items():
        with st.container(border=True):
            # 显示产品名称和数量
            qty = p_info.get('quantity', '未填')
            st.markdown(f"#### 📦 {p_name} <span style='font-size:0.8em; color:gray'>(采购量: {qty})</span>", unsafe_allow_html=True)
            
            rankings = get_product_rankings(project_id, p_name)
            my_rank = None
            for idx, rank_info in enumerate(rankings):
                if rank_info['supplier'] == current_user:
                    my_rank = idx + 1
                    break
            
            c1, c2 = st.columns([1, 2])
            with c1:
                if my_rank == 1:
                    st.metric("我的排名", "第 1 名 🏆", delta="当前领先")
                elif my_rank:
                    st.metric("我的排名", f"第 {my_rank} 名", delta="未领先", delta_color="off")
                else:
                    st.metric("我的排名", "未报价")

            with c2:
                with st.form(key=f"{project_id}_{p_name}", border=False):
                    sc1, sc2 = st.columns([3, 1])
                    new_price = sc1.number_input("含税单价 (¥)", min_value=0.0, step=0.1, label_visibility="collapsed", placeholder="输入价格")
                    if sc2.form_submit_button("🚀 提交"):
                        if new_price > 0:
                            p_info['bids'].append({
                                'supplier': current_user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S'),
                                'datetime': pd.Timestamp.now() # 用于画图的时间戳
                            })
                            st.success("已提交")
                            st.rerun()

# --- 管理员界面 (核心升级) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 华脉总控台")
    st.sidebar.markdown(f"用户: {st.session_state.user}")
    
    menu = st.sidebar.radio("导航", ["📁 项目管理 (新建/密码)", "📊 实时监控 & 竞价分析"])
    
    if st.sidebar.button("退出系统"):
        st.session_state.clear()
        st.rerun()

    # === 功能1：项目管理 ===
    if menu == "📁 项目管理 (新建/密码)":
        st.title("📁 项目管理中心")
        
        with st.expander("➕ 创建新询价项目", expanded=True):
            with st.form("new_project"):
                st.markdown("#### 1. 项目基础信息")
                c1, c2 = st.columns([2, 1])
                p_name = c1.text_input("项目名称", placeholder="例如：12月17日服务器配件询价")
                p_date = c2.date_input("询价日期", datetime.now())
                
                st.markdown("#### 2. 参与供应商")
                suppliers_str = st.text_area("输入供应商账号列表 (逗号隔开)", value="GYSA, GYSB, GYSC")
                
                if st.form_submit_button("立即创建"):
                    if p_name and suppliers_str:
                        sup_list = [s.strip() for s in suppliers_str.replace('，', ',').split(',') if s.strip()]
                        if not sup_list:
                            st.error("请至少输入一个供应商")
                        else:
                            new_id = str(uuid.uuid4())[:8]
                            codes = {sup: generate_random_code() for sup in sup_list}
                            shared_data["projects"][new_id] = {
                                "name": p_name, "date": str(p_date), "codes": codes, "products": {}
                            }
                            st.success(f"项目 '{p_name}' 创建成功！")
                            st.rerun()
                    else:
                        st.error("请填写完整信息")
        
        st.markdown("---")
        
        # 项目列表
        projects_to_show = sorted(shared_data["projects"].items(), key=lambda x: x[1]['date'], reverse=True)
        
        if not projects_to_show:
            st.info("暂无项目")
        else:
            for pid, data in projects_to_show:
                with st.expander(f"📅 {data['date']} | {data['name']}", expanded=False):
                    # 密码区
                    st.markdown("##### 🔑 供应商账号与密码 (点击复制)")
                    h1, h2 = st.columns([1, 1])
                    h1.markdown("**账号**"); h2.markdown("**密码**")
                    for sup, code in data["codes"].items():
                        r1, r2 = st.columns([1, 1])
                        r1.code(sup, language=None); r2.code(code, language=None)
                    
                    st.divider()
                    
                    # 产品管理 (升级：增加数量)
                    c_prod1, c_prod2 = st.columns([3, 1])
                    c_prod1.markdown("##### 📦 询价产品管理")
                    
                    if data["products"]:
                        for p_key, p_val in data["products"].items():
                            cp1, cp2 = st.columns([4, 1])
                            qty_display = p_val.get('quantity', 'N/A')
                            cp1.text(f"• {p_key} (数量: {qty_display})")
                            if cp2.button("删除", key=f"del_{pid}_{p_key}"):
                                del data["products"][p_key]
                                st.rerun()
                    else:
                        st.caption("暂无产品")
                    
                    with st.form(key=f"add_prod_{pid}"):
                        c_add1, c_add2, c_add3 = st.columns([3, 2, 1])
                        new_p = c_add1.text_input("产品名称", placeholder="如：5G芯片")
                        new_q = c_add2.number_input("采购数量", min_value=1, value=100)
                        if c_add3.form_submit_button("➕ 添加"):
                            if new_p and new_p not in data["products"]:
                                # 数据结构升级：包含 quantity
                                data["products"][new_p] = {"quantity": new_q, "bids": []}
                                st.rerun()
                    
                    st.markdown("---")
                    if st.button("🗑️ 删除整个项目", key=f"del_proj_{pid}"):
                        del shared_data["projects"][pid]
                        st.rerun()

    # === 功能2：实时监控 & 竞价分析 (核心升级) ===
    elif menu == "📊 实时监控 & 竞价分析":
        st.title("📊 报价监控中心")
        
        if not shared_data["projects"]:
            st.warning("暂无项目")
        else:
            # 选择项目
            project_options = {pid: f"{d['date']} - {d['name']}" for pid, d in shared_data["projects"].items()}
            sorted_opts = dict(sorted(project_options.items(), key=lambda item: shared_data["projects"][item[0]]['date'], reverse=True))
            selected_pid = st.selectbox("选择要查看的项目", options=list(sorted_opts.keys()), format_func=lambda x: sorted_opts[x])
            project = shared_data["projects"][selected_pid]
            
            # 导出 Excel
            all_records = []
            for pname, info in project["products"].items():
                qty = info.get('quantity', 0)
                for bid in info['bids']:
                    all_records.append({
                        '产品': pname, '采购数量': qty, '供应商': bid['supplier'], 
                        '单价': bid['price'], '总价': bid['price'] * qty, '时间': bid['time']
                    })
            
            if all_records:
                df_export = pd.DataFrame(all_records)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_export.to_excel(writer, index=False)
                st.download_button(f"📥 导出 [{project['name']}] 报价单", buffer.getvalue(), f"报价单_{project['date']}.xlsx")
            
            st.divider()
            
            # --- 产品维度详细分析 ---
            for p_name, p_info in project["products"].items():
                qty = p_info.get('quantity', 0)
                bids = p_info['bids']
                
                with st.container(border=True):
                    st.subheader(f"📦 {p_name}")
                    st.caption(f"采购数量: {qty}")

                    if not bids:
                        st.info("⏳ 暂无供应商报价")
                    else:
                        # 数据处理
                        df = pd.DataFrame(bids)
                        
                        # 1. 计算核心指标
                        # 按供应商分组取最小值
                        supplier_best = df.loc[df.groupby("supplier")["price"].idxmin()]
                        min_price = supplier_best['price'].min()
                        max_price = supplier_best['price'].max()
                        best_supplier = supplier_best.loc[supplier_best['price'] == min_price, 'supplier'].iloc[0]
                        avg_price = supplier_best['price'].mean()

                        # 指标卡片
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("最优供应商", best_supplier, border=True)
                        m1.caption("🏆 中标候选人")
                        
                        m2.metric("最低单价", f"¥{min_price:,.2f}", border=True)
                        if qty > 0: m2.caption(f"预估总价: ¥{min_price * qty:,.2f}")
                        
                        m3.metric("最高单价", f"¥{max_price:,.2f}", border=True)
                        m3.caption(f"价差: {(max_price-min_price)/min_price:.1%}")
                        
                        m4.metric("平均报价", f"¥{avg_price:,.2f}", border=True)

                        st.markdown("---")
                        
                        # 2. 图表区
                        t1, t2 = st.tabs(["📈 价格走势图 (Trend)", "📊 供应商比价 (Compare)"])
                        
                        with t1:
                            # 走势图: x轴时间, y轴价格, 颜色区分供应商
                            st.caption("不同供应商的报价随时间变化趋势")
                            chart_df = df[['datetime', 'price', 'supplier']].copy()
                            # 转换时间戳为更易读的格式
                            st.line_chart(
                                chart_df,
                                x='datetime',
                                y='price',
                                color='supplier',
                                use_container_width=True
                            )
                        
                        with t2:
                            # 比价图: 柱状图显示各家最终报价
                            st.caption("各供应商最终报价对比")
                            compare_df = supplier_best[['supplier', 'price']].set_index('supplier')
                            st.bar_chart(
                                compare_df,
                                color="#ffaa00", # 统一颜色或自动颜色
                                use_container_width=True
                            )

                        # 3. 详细排名表 (可折叠)
                        with st.expander("查看详细排名表格"):
                            rankings = get_product_rankings(selected_pid, p_name)
                            display_data = []
                            for i, r in enumerate(rankings):
                                total = r['price'] * qty if qty else 0
                                display_data.append({
                                    "排名": f"第 {i+1} 名", 
                                    "供应商": r['supplier'], 
                                    "最终单价": f"¥{r['price']}",
                                    "总价": f"¥{total:,.2f}",
                                    "报价时间": r['time']
                                })
                            st.table(display_data)

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()

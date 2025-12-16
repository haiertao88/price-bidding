import streamlit as st
import pandas as pd
import io

# --- 页面配置 ---
st.set_page_config(page_title="供应商比价系统", layout="wide") # 改为 wide 模式，利用屏幕宽度

# --- CSS 样式优化 (解决间距太大的问题) ---
st.markdown("""
    <style>
        /* 缩小组件上下的空白 */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        /* 调整卡片内部的紧凑度 */
        .st-emotion-cache-1r6slb0 {
            padding: 1rem;
        }
        /* 调整标题大小 */
        h4 {
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- 全局数据缓存 ---
@st.cache_resource
def get_global_data():
    return {
        '光纤连接器 Type-A': {'bids': []},
        '路由器外壳 CNC': {'bids': []}
    }

shared_data = get_global_data()

# --- 排名计算逻辑 ---
def get_product_rankings(product_name):
    if product_name not in shared_data:
        return []
    bids = shared_data[product_name]['bids']
    if not bids:
        return []
    
    supplier_best = {}
    for bid in bids:
        sup = bid['supplier']
        price = bid['price']
        if sup not in supplier_best or price < supplier_best[sup]['price']:
            supplier_best[sup] = bid

    return sorted(supplier_best.values(), key=lambda x: x['price'])

# --- 登录界面 ---
def login_page():
    st.markdown("## 🔐 供应商竞价系统")
    with st.container(border=True):
        username = st.text_input("账号")
        password = st.text_input("密码", type="password")
        if st.button("登录", use_container_width=True, type="primary"):
            if username == "admin" and password == "admin888":
                st.session_state.user_type = "admin"
                st.session_state.user = username
                st.rerun()
            elif username in ["supA", "supB", "supC"] and password == "123":
                st.session_state.user_type = "supplier"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("账号或密码错误")

# --- 供应商界面 (UI 紧凑化 + 隐藏价差) ---
def supplier_dashboard():
    current_user = st.session_state.user
    
    # --- 侧边栏：操作指南 ---
    with st.sidebar:
        st.title(f"👤 {current_user}")
        
        st.info("📖 **操作必读**\n\n1. 在右侧输入价格并提交。\n2. **提交后，必须点击下方的【刷新排名】按钮**，才能看到你的最新名次！")
        
        # 使用 type="primary" 让按钮变红/显眼
        if st.button("🔄 点我刷新排名", type="primary", use_container_width=True):
            st.rerun()
            
        st.markdown("---")
        if st.button("退出登录"):
            st.session_state.clear()
            st.rerun()

    st.markdown("### 📊 实时报价列表")

    if not shared_data:
        st.warning("暂无询价产品")
        return

    # 使用 columns 布局，每行显示 1-2 个产品（取决于屏幕宽度），也可以一行一个但更紧凑
    for product_name in list(shared_data.keys()):
        # 给每个产品一个带边框的容器，视觉上更紧凑
        with st.container(border=True):
            # 第一行：标题
            st.markdown(f"#### 📦 {product_name}")
            
            rankings = get_product_rankings(product_name)
            min_price = rankings[0]['price'] if rankings else 0
            
            my_rank = None
            for idx, rank_info in enumerate(rankings):
                if rank_info['supplier'] == current_user:
                    my_rank = idx + 1
                    break
            
            # 第二行：数据和操作 (分为3列)
            c1, c2, c3 = st.columns([1, 1, 1.5])
            
            # 列1：最低价
            c1.metric("全场最低价", f"¥{min_price}" if min_price else "--")
            
            # 列2：我的排名 (修改点：隐藏具体落后价格)
            if my_rank == 1:
                c2.metric("我的排名", "第 1 名 🏆", delta="当前领先")
            elif my_rank:
                # 只显示第几名，delta 设为 None 或 "未领先"，不显示具体差价
                c2.metric("我的排名", f"第 {my_rank} 名", delta=None, delta_color="off")
            else:
                c2.metric("我的排名", "未报价")

            # 列3：报价输入框 (高度对齐优化)
            with c3:
                with st.form(key=f"f_{product_name}", border=False):
                    # 把输入框和按钮放在一行
                    sub_c1, sub_c2 = st.columns([2, 1])
                    new_price = sub_c1.number_input("报价", min_value=0.0, step=1.0, label_visibility="collapsed", placeholder="输入价格")
                    if sub_c2.form_submit_button("🚀 提交"):
                        if new_price > 0:
                            shared_data[product_name]['bids'].append({
                                'supplier': current_user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S')
                            })
                            st.success("已提交")
                            st.rerun()

# --- 管理员界面 (保持紧凑) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 管理员")
    if st.sidebar.button("🔄 刷新数据", type="primary"): st.rerun()
    if st.sidebar.button("退出"): 
        st.session_state.clear()
        st.rerun()

    st.title("📋 甲方总控台")
    
    tab1, tab2, tab3 = st.tabs(["🏆 实时排名", "⚙️ 产品管理", "📝 历史记录"])

    with tab1:
        for p_name in shared_data.keys():
            with st.container(border=True):
                st.markdown(f"#### {p_name}")
                rankings = get_product_rankings(p_name)
                if rankings:
                    # 简化表格显示
                    st.dataframe(
                        pd.DataFrame(rankings)[['supplier', 'price', 'time']].rename(columns={'supplier':'供应商', 'price':'报价', 'time':'时间'}),
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.caption("暂无报价")

    with tab2:
        with st.form("add"):
            c1, c2 = st.columns([3, 1])
            new_name = c1.text_input("产品名称", label_visibility="collapsed", placeholder="输入新产品名称")
            if c2.form_submit_button("➕ 发布产品"):
                if new_name and new_name not in shared_data:
                    shared_data[new_name] = {'bids': []}
                    st.rerun()
        
        st.markdown("---")
        for p_name in list(shared_data.keys()):
            c1, c2 = st.columns([4, 1])
            c1.text(p_name)
            if c2.button("删除", key=f"d_{p_name}"):
                del shared_data[p_name]
                st.rerun()

    with tab3:
        all_records = []
        for pname, info in shared_data.items():
            for bid in info['bids']:
                all_records.append({'产品': pname, '供应商': bid['supplier'], '价格': bid['price'], '时间': bid['time']})
        
        if all_records:
            df = pd.DataFrame(all_records)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无数据")

# --- 主程序 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()
